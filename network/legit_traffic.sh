#!/bin/bash
echo "Starting legitimate traffic from h1 to h3 (Server: 10.0.0.3)"
echo "Press Ctrl+C to stop."
while true; do
    iperf -c 10.0.0.3 -u -b 1m -t 5 2>/dev/null
    sleep 0.5
done
