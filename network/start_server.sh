#!/bin/bash
# Note: network/topo.py already starts this iperf UDP server automatically on h3 at boot.
# Use this script only if you need to manually restart the server inside Mininet:
# Usage: mininet> h3 bash network/start_server.sh
echo "Starting iperf UDP server on h3 (port 5001)..."
iperf -s -u
