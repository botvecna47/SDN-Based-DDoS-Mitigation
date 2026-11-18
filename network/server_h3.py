#!/usr/bin/env python3
"""
Multi-Threaded Protected Target Server (h3: 10.0.0.3)
=====================================================
Runs multi-threaded HTTP servers on port 80 and 8080 plus a lightweight UDP responder
on port 53 (DNS / Microservices) and port 5002.

Because this uses ThreadingHTTPServer, each incoming connection is handled on an
independent worker thread. Slowloris holding 100+ lingering sockets will NOT starve
or freeze legitimate web clients (e.g., h11) connecting on port 80.
"""

import sys
import time
import socket
import signal
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class RobustRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        body = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 28\r\nConnection: close\r\n\r\nOK from Protected Server h3\n"
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_HEAD(self):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except Exception:
            pass

    def do_POST(self):
        self.do_GET()

    def log_message(self, format, *args):
        # Suppress noisy access log output during high-rate attack simulation
        pass

def run_http_server(port):
    server_address = ('', port)
    try:
        httpd = ThreadingHTTPServer(server_address, RobustRequestHandler)
        httpd.daemon_threads = True
        print(f"[h3 Server] Multi-threaded HTTP server listening on port {port} (TCP)")
        httpd.serve_forever()
    except Exception as e:
        print(f"[h3 Server] HTTP server on port {port} stopped: {e}")

def run_udp_responder(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))
        print(f"[h3 Server] Lightweight UDP responder listening on port {port} (UDP)")
        while True:
            data, addr = sock.recvfrom(2048)
            if not data:
                continue
            # If standard DNS query or test packet, reply with a compact acknowledgement
            if len(data) >= 12:
                # Echo basic header with QR=1 (response)
                try:
                    resp = data[:2] + b'\x81\x80' + data[4:6] + data[4:6] + b'\x00\x00\x00\x00'
                    sock.sendto(resp, addr)
                except Exception:
                    pass
    except Exception as e:
        print(f"[h3 Server] UDP responder on port {port} stopped: {e}")

def main():
    def shutdown(signum=None, frame=None):
        print("\n[h3 Server] Shutting down target server...")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Launch threaded HTTP server on port 80
    t_http80 = threading.Thread(target=run_http_server, args=(80,), daemon=True)
    t_http80.start()

    # Launch threaded HTTP server on port 8080 (optional secondary target port)
    t_http8080 = threading.Thread(target=run_http_server, args=(8080,), daemon=True)
    t_http8080.start()

    # Launch UDP responder on port 53 (DNS)
    t_udp53 = threading.Thread(target=run_udp_responder, args=(53,), daemon=True)
    t_udp53.start()

    # Launch UDP responder on port 5001 (Primary streaming port for h1 & h2)
    t_udp5001 = threading.Thread(target=run_udp_responder, args=(5001,), daemon=True)
    t_udp5001.start()

    # Launch UDP responder on port 5002 (Secondary stream)
    t_udp5002 = threading.Thread(target=run_udp_responder, args=(5002,), daemon=True)
    t_udp5002.start()

    print("[h3 Server] Protected Server daemon active. All listener threads operational.")
    while True:
        time.sleep(1.0)

if __name__ == "__main__":
    main()
