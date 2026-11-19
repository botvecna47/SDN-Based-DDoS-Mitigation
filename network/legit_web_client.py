#!/usr/bin/env python3
"""
Lightweight High-Efficiency Legitimate HTTP Web Client
======================================================
Generates steady, calibrated legitimate HTTP GET requests to target server (10.0.0.3:80)
using persistent keep-alive connections. Consumes < 1% CPU unlike bash while-curl loops.
"""

import sys
import time
import http.client
import signal

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else '10.0.0.3'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    rate_pps = float(sys.argv[3]) if len(sys.argv) > 3 else 310.0
    interval = 1.0 / rate_pps if rate_pps > 0 else 0.003

    def shutdown(signum=None, frame=None):
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        try:
            conn = http.client.HTTPConnection(target, port, timeout=2.0)
            conn.connect()
            while True:
                t0 = time.perf_counter()
                conn.request("GET", "/", headers={"Connection": "keep-alive"})
                resp = conn.getresponse()
                resp.read()
                elapsed = time.perf_counter() - t0
                sleep_sec = interval - elapsed
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
        except Exception:
            time.sleep(0.1)

if __name__ == '__main__':
    main()
