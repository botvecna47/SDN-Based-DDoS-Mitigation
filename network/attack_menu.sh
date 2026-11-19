#!/bin/bash
# ==============================================================================
# SDN DDoS Attack Emulation Suite & Interactive Launchpad
# ==============================================================================
# Provides unified emulation commands for:
#   1. Volumetric UDP Flood (h2: 10.0.0.2 :80 @ ~9,500 PPS)
#   2. TCP SYN Flood (h4: 10.0.0.4 :80 @ ~6,800 PPS)
#   3. Slowloris HTTP Starvation (h5: 10.0.0.5 :80 @ ~45 PPS)
#   4. High-Rate ICMP Ping Flood (h6: 10.0.0.6 @ ~5,200 PPS)
#   5. Dynamic Pulsing / Wave Attack (h8: 10.0.0.8 10s ON ~7,600 PPS / 5s OFF)
#   6. Coordinated Multi-IP Botnet with Same-IP Mixed Traffic (h2, h4-h8)
#   7. Same-IP Mixed Traffic Demo (h2 and h4 simultaneous legit + attack)
#   8. High-Port UDP Flood (h7: 10.0.0.7 :8080 @ ~11,400 PPS)
#   9. Start Pure Legitimate Streams (h1, h11, h12 baseline ~1,315 PPS)
#  10. Stop Attack Traffic (Halts attacks; retains legitimate streams)
#  11. Stop All Traffic (Halts attacks AND legitimate traffic)
# ==============================================================================

TARGET_IP="10.0.0.3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLOODER="$SCRIPT_DIR/traffic_flooder.py"
SLOWLORIS="$SCRIPT_DIR/slowloris.py"
LEGIT_WEB="$SCRIPT_DIR/legit_web_client.py"

BOTNET_PID_FILE="/tmp/sdn_botnet_pids"
PULSE_PID_FILE="/tmp/sdn_pulse_pids"

if [ "$EUID" -eq 0 ]; then
    SUDO=""
elif sudo -n true 2>/dev/null; then
    SUDO="sudo"
else
    SUDO=""
fi

print_header() {
    clear
    echo "======================================================================"
    echo "       SDN DDOS MITIGATION — ATTACK EMULATION LAUNCHPAD               "
    echo "======================================================================"
    echo " Target Server : $TARGET_IP (Host h3)"
    echo " Detection     : Tier-1 CIC-DDoS2019 Decision Tree (Ryu Controller)"
    echo " Granularity   : Flow-Tuple Mitigation (Same-IP Mixed Allowed + Dropped)"
    echo " Environment   : $([ "$EUID" -eq 0 ] && echo "Mininet Host / Root (Optimal)" || ([ -n "$SUDO" ] && echo "Host VM (sudo enabled)" || echo "Host VM (non-root / no passwordless sudo)"))"
    echo "======================================================================"
    echo ""
}

show_menu() {
    echo "Select an emulation vector to launch:"
    echo "  [1]  Volumetric UDP Flood       (h2: 10.0.0.2 :80 @ ~9,500 PPS)"
    echo "  [2]  TCP SYN Handshake Flood    (h4: 10.0.0.4 :80 @ ~6,800 PPS)"
    echo "  [3]  Slowloris HTTP Starvation  (h5: 10.0.0.5 :80 @ ~45 PPS)"
    echo "  [4]  High-Rate ICMP Ping Flood  (h6: 10.0.0.6 @ ~5,200 PPS)"
    echo "  [5]  Dynamic Pulsing Wave DDoS  (h8: 10.0.0.8 10s ON ~7,600 PPS / 5s OFF)"
    echo "  [6]  Coordinated Botnet Assault (Launches h2, h4-h8 with distinct rates)"
    echo "  [7]  Same-IP Mixed Traffic Demo (h2 and h4 simultaneous legit + attack)"
    echo "  [8]  High-Port UDP Flood        (h7: 10.0.0.7 :8080 @ ~11,400 PPS)"
    echo "  [9]  Start Legitimate Streams   (h1, h11, h12 baseline ~1,315 PPS)"
    echo "  [10] Stop Attack Traffic        (Halts attacks; retains legitimate streams)"
    echo "  [11] Stop All Traffic           (Halts attacks AND legitimate traffic)"
    echo "  [0]  Exit"
    echo ""
    read -p "Enter choice [0-11]: " choice
}

ensure_legit_traffic() {
    if ! pgrep -f "traffic_flooder.*5001" >/dev/null 2>&1 && ! pgrep -f "legit_web_client" >/dev/null 2>&1; then
        echo "[*] [AUTO-START] Bootstrapping background legitimate user streams..."
        $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 5001 --rate 820 --src-ip 10.0.0.1 >/dev/null 2>&1 &
        $SUDO python3 "$LEGIT_WEB" "$TARGET_IP" 80 310 >/dev/null 2>&1 &
        $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 53 --rate 185 --src-ip 10.0.0.12 >/dev/null 2>&1 &
        sleep 0.5
    fi
}

stop_attacks() {
    echo "[*] Terminating all active attack processes..."
    if [ -f "$PULSE_PID_FILE" ]; then
        kill -9 $(cat "$PULSE_PID_FILE" 2>/dev/null) 2>/dev/null
        rm -f "$PULSE_PID_FILE"
    fi
    if [ -f "$BOTNET_PID_FILE" ]; then
        while read -r pid; do
            [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null
        done < "$BOTNET_PID_FILE"
        rm -f "$BOTNET_PID_FILE"
    fi
    # Stop attack streams (port 80 floods, icmp, port 8080)
    $SUDO pkill -9 -f "traffic_flooder.*--port 80" 2>/dev/null
    $SUDO pkill -9 -f "traffic_flooder.*--port 8080" 2>/dev/null
    $SUDO pkill -9 -f "traffic_flooder.*--proto icmp" 2>/dev/null
    $SUDO pkill -9 -f "traffic_flooder.*--proto tcp_syn" 2>/dev/null
    $SUDO pkill -9 -f "traffic_flooder.*--proto pulse" 2>/dev/null
    $SUDO pkill -9 -f "slowloris.py" 2>/dev/null
    $SUDO pkill -9 -f "hping3" 2>/dev/null
    echo "[+] Attack traffic halted. Legitimate user streams remain active."
}

stop_all() {
    stop_attacks
    echo "[*] Terminating all legitimate traffic streams..."
    $SUDO pkill -9 -f "traffic_flooder" 2>/dev/null
    $SUDO pkill -9 -f "legit_web_client" 2>/dev/null
    $SUDO pkill -9 -f "hping3" 2>/dev/null
    echo "[+] All traffic halted."
}

pause_prompt() {
    if [ -t 0 ]; then
        echo ""
        read -n 1 -s -r -p "Press any key to return to menu..."
        echo ""
    fi
}

case_launch() {
    case $1 in
        1|volumetric)
            ensure_legit_traffic
            echo "[!] Launching Volumetric UDP Flood from 10.0.0.2 against $TARGET_IP:80 (~9,500 PPS)..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 80 --rate 9500 --src-ip 10.0.0.2
            trap - INT
            ;;
        2|syn_flood)
            ensure_legit_traffic
            echo "[!] Launching TCP SYN Flood from 10.0.0.4 against $TARGET_IP:80 (~6,800 PPS)..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            $SUDO python3 "$FLOODER" --proto tcp_syn --target "$TARGET_IP" --port 80 --rate 6800 --src-ip 10.0.0.4
            trap - INT
            ;;
        3|slowloris)
            ensure_legit_traffic
            echo "[!] Launching Slowloris Low-and-Slow Attack from 10.0.0.5 against $TARGET_IP:80..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            python3 "$SLOWLORIS" "$TARGET_IP" 80 90 --src-ip 10.0.0.5
            trap - INT
            ;;
        4|icmp_flood)
            ensure_legit_traffic
            echo "[!] Launching ICMP Ping Flood from 10.0.0.6 against $TARGET_IP (~5,200 PPS)..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            $SUDO python3 "$FLOODER" --proto icmp --target "$TARGET_IP" --rate 5200 --src-ip 10.0.0.6
            trap - INT
            ;;
        5|pulsing)
            ensure_legit_traffic
            echo "[!] Launching Dynamic Pulsing Wave DDoS from 10.0.0.8 against $TARGET_IP:53 (10s ON ~7,600 PPS / 5s OFF)..."
            echo "Press Ctrl+C to stop."
            trap 'echo ""; echo "[*] Pulsing attack stopped by user."; return 0' INT
            $SUDO python3 "$FLOODER" --proto pulse --target "$TARGET_IP" --port 53 --rate 7600 --on 10 --off 5 --src-ip 10.0.0.8
            trap - INT
            ;;
        6|botnet)
            ensure_legit_traffic
            echo "[!] Launching Coordinated Multi-IP Botnet Assault with Distinct Rates & Mixed Traffic:"
            echo "    -> Node h2 (10.0.0.2): Volumetric UDP Flood (:80 @ ~9,500 PPS) [BLOCKED]"
            echo "    -> Node h2 (10.0.0.2): Concurrent Legit Stream (:5001 @ ~440 PPS) [ALLOWED]"
            echo "    -> Node h4 (10.0.0.4): TCP SYN Handshake Flood (:80 @ ~6,800 PPS) [BLOCKED]"
            echo "    -> Node h4 (10.0.0.4): Concurrent Legit Stream (:53 @ ~230 PPS) [ALLOWED]"
            echo "    -> Node h5 (10.0.0.5): Slowloris HTTP Starvation (:80 @ ~45 PPS) [BLOCKED]"
            echo "    -> Node h6 (10.0.0.6): High-Rate ICMP Echo Flood (@ ~5,200 PPS) [BLOCKED]"
            echo "    -> Node h7 (10.0.0.7): High-Port UDP Flood (:8080 @ ~11,400 PPS) [BLOCKED]"
            echo "    -> Node h8 (10.0.0.8): Pulsing Wave Attack (10s ON ~7,600 PPS / 5s OFF) [BLOCKED]"

            rm -f "$BOTNET_PID_FILE" "$PULSE_PID_FILE"

            # Concurrent legitimate streams on mixed nodes h2 and h4
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 5001 --rate 440 --src-ip 10.0.0.2 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 53 --rate 230 --src-ip 10.0.0.4 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            # Attack streams with distinct non-identical rates
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 80 --rate 9500 --src-ip 10.0.0.2 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO python3 "$FLOODER" --proto tcp_syn --target "$TARGET_IP" --port 80 --rate 6800 --src-ip 10.0.0.4 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO python3 "$FLOODER" --proto icmp --target "$TARGET_IP" --rate 5200 --src-ip 10.0.0.6 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 8080 --rate 11400 --src-ip 10.0.0.7 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            python3 "$SLOWLORIS" "$TARGET_IP" 80 90 --src-ip 10.0.0.5 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            $SUDO python3 "$FLOODER" --proto pulse --target "$TARGET_IP" --port 53 --rate 7600 --on 10 --off 5 --src-ip 10.0.0.8 >/dev/null 2>&1 &
            echo $! >> "$BOTNET_PID_FILE"

            echo ""
            echo "[+] Distributed Botnet active in background (~40,500 Attack PPS + ~1,985 Clean PPS)!"
            echo "Observe the React Dashboard Table: Mixed nodes show both Passed (Green) and Blocked (Red) rates!"
            echo "To halt botnet: Select Option [10] (Stop Attack Traffic)."
            pause_prompt
            ;;
        7|mixed_same_ip)
            ensure_legit_traffic
            echo "[!] Launching Same-IP Mixed Traffic Demo (h2 and h4 carry both legit and attack streams)..."
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 80 --rate 9500 --src-ip 10.0.0.2 >/dev/null 2>&1 &
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 5001 --rate 440 --src-ip 10.0.0.2 >/dev/null 2>&1 &
            $SUDO python3 "$FLOODER" --proto tcp_syn --target "$TARGET_IP" --port 80 --rate 6800 --src-ip 10.0.0.4 >/dev/null 2>&1 &
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 53 --rate 230 --src-ip 10.0.0.4 >/dev/null 2>&1 &
            echo "[+] Same-IP mixed traffic is running on h2 and h4."
            pause_prompt
            ;;
        8|high_port_udp)
            ensure_legit_traffic
            echo "[!] Launching High-Port UDP Flood from 10.0.0.7 against $TARGET_IP:8080 (~11,400 PPS)..."
            echo "Press Ctrl+C to abort attack."
            trap 'echo ""; echo "[*] Attack stopped by user."; return 0' INT
            $SUDO python3 "$FLOODER" --proto udp --target "$TARGET_IP" --port 8080 --rate 11400 --src-ip 10.0.0.7
            trap - INT
            ;;
        9|legit)
            echo "[*] Launching pure legitimate user streams from h1, h11, h12 to h3 ($TARGET_IP)..."
            ensure_legit_traffic
            echo "[+] Pure legitimate user streams (~1,315 pkts/s baseline) active in background!"
            echo "Inspect the React Dashboard to observe Clean Forwarded traffic green line passing through."
            pause_prompt
            ;;
        10)
            stop_attacks
            pause_prompt
            ;;
        11)
            stop_all
            pause_prompt
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

# If arguments were provided directly on the command line, dispatch without menu
if [ -n "$1" ]; then
    case_launch "$1"
    exit 0
fi

# Interactive menu loop
while true; do
    print_header
    show_menu
    case_launch "$choice"
done
