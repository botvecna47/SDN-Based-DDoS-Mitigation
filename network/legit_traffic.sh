#!/bin/bash
echo "Starting steady legitimate traffic from h1 to h3 (Server: 10.0.0.3)..."
echo "Press Ctrl+C to stop."
trap "echo 'Stopping traffic generator...'; exit 0" SIGINT SIGTERM

# Continuous UDP stream at 10 Mbps (~850 pkts/s baseline) for 1 hour.
# Eliminates periodic drop-to-zero dips caused by short iperf burst intervals.
iperf -c 10.0.0.3 -u -b 10m -t 3600
