#!/usr/bin/env python3
"""
Multi-Host Botnet Topology for Distributed DDoS Emulation & Mixed-Traffic Verification
======================================================================================
Spins up a 10-host Mininet topology connecting to OpenFlow 1.3 switch s1:
  - Target Server:
      • h3  (10.0.0.3): Protected Server running multi-threaded HTTP (port 80/8080),
                        UDP responder (port 5001, 5002, and 53)
  - Pure Legitimate Users (distinct IPs):
      • h1  (10.0.0.1) : Legitimate streaming client (UDP :5001 @ ~820 pkts/s)
      • h11 (10.0.0.11): Legitimate HTTP web client (:80 @ ~310 pkts/s)
      • h12 (10.0.0.12): Legitimate DNS client (:53 @ ~185 pkts/s)
  - Attacker / Mixed Nodes (distinct IPs):
      • h2  (10.0.0.2) : Volumetric UDP flood (:80 @ ~9,500 PPS) + concurrent legit stream (:5001 @ ~440 PPS)
      • h4  (10.0.0.4) : TCP SYN flood (:80 @ ~6,800 PPS) + concurrent legit stream (:53 @ ~230 PPS)
      • h5  (10.0.0.5) : Slowloris HTTP starvation (:80 TCP @ ~45 PPS)
      • h6  (10.0.0.6) : High-rate ICMP Echo flood (@ ~5,200 PPS)
      • h7  (10.0.0.7) : High-Port UDP flood (:8080 @ ~11,400 PPS)
      • h8  (10.0.0.8) : True Pulsing / Wave DDoS (10s ON / 5s OFF on :53 UDP @ ~7,600 PPS)

Usage:
    sudo python3 network/topo_botnet.py
"""

import os
import sys
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(SCRIPT_DIR, 'server_h3.py')
SLOWLORIS_SCRIPT = os.path.join(SCRIPT_DIR, 'slowloris.py')
LEGIT_WEB_SCRIPT = os.path.join(SCRIPT_DIR, 'legit_web_client.py')
FLOODER_SCRIPT = os.path.join(SCRIPT_DIR, 'traffic_flooder.py')

def cleanup_stale():
    """Removes stale veth interfaces, switch bridges, and traffic generation processes."""
    info('*** Auto-cleaning stale virtual interfaces, bridges, and background processes...\n')
    os.system("ovs-vsctl --if-exists del-br s1 2>/dev/null")
    os.system("ip link show | grep -oE '(s1-eth[0-9]+|h[0-9]+-eth[0-9]+)' | xargs -r -n 1 ip link delete 2>/dev/null")
    os.system("pkill -9 -f 'traffic_flooder' 2>/dev/null")
    os.system("pkill -9 -f 'hping3' 2>/dev/null")
    os.system("pkill -9 -f 'iperf' 2>/dev/null")
    os.system("pkill -9 -f 'server_h3.py' 2>/dev/null")
    os.system("pkill -9 -f 'slowloris' 2>/dev/null")
    os.system("pkill -9 -f 'legit_web_client' 2>/dev/null")
    os.system("pkill -9 -f 'pulse_h8' 2>/dev/null")

class BotnetCLI(CLI):
    prompt = 'mininet-botnet> '

    def __init__(self, mininet, *args, **kwargs):
        self.net = mininet
        super().__init__(mininet, *args, **kwargs)

    def do_legit(self, _line):
        """Start or restart continuous legitimate background traffic (h1, h11, h12 -> h3)."""
        # h1: UDP streaming to port 5001 (~820 PPS)
        h1 = self.mn.get('h1')
        h1.cmd('pkill -9 -f traffic_flooder 2>/dev/null')
        h1.cmd('pkill -9 -f hping3 2>/dev/null')
        h1.cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 5001 --rate 820 --src-ip 10.0.0.1 >/dev/null 2>&1 &')

        # h11: Legitimate HTTP web traffic to port 80 (~310 PPS)
        h11 = self.mn.get('h11')
        h11.cmd('pkill -9 -f legit_web_client 2>/dev/null')
        h11.cmd('pkill -9 -f curl 2>/dev/null')
        h11.cmd('pkill -9 -f traffic_flooder 2>/dev/null')
        h11.cmd(f'python3 {LEGIT_WEB_SCRIPT} 10.0.0.3 80 310 >/dev/null 2>&1 &')

        # h12: Legitimate DNS query traffic to port 53 (~185 PPS)
        h12 = self.mn.get('h12')
        h12.cmd('pkill -9 -f traffic_flooder 2>/dev/null')
        h12.cmd('pkill -9 -f hping3 2>/dev/null')
        h12.cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 53 --rate 185 --src-ip 10.0.0.12 >/dev/null 2>&1 &')

        info('*** Continuous legitimate user traffic active:\n')
        info('    • h1  (10.0.0.1)  -> 10.0.0.3:5001 [UDP Video Stream] (~820 PPS) [ALLOWED]\n')
        info('    • h11 (10.0.0.11) -> 10.0.0.3:80   [HTTP Web Client]  (~310 PPS) [ALLOWED]\n')
        info('    • h12 (10.0.0.12) -> 10.0.0.3:53   [DNS Queries]      (~185 PPS) [ALLOWED]\n')

    def do_udp(self, _line):
        """Launch volumetric UDP flood from h2 targeting h3:80 (~9,500 PPS)."""
        info('    -> h2 (10.0.0.2): Volumetric UDP Flood (:80 @ ~9,500 PPS)\n')
        self.mn.get('h2').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 80 --rate 9500 --src-ip 10.0.0.2 >/dev/null 2>&1 &')

    def do_syn(self, _line):
        """Launch TCP SYN handshake flood from h4 targeting h3:80 (~6,800 PPS)."""
        info('    -> h4 (10.0.0.4): TCP SYN Flood (:80 @ ~6,800 PPS)\n')
        self.mn.get('h4').cmd(f'python3 {FLOODER_SCRIPT} --proto tcp_syn --target 10.0.0.3 --port 80 --rate 6800 --src-ip 10.0.0.4 >/dev/null 2>&1 &')

    def do_slowloris(self, _line):
        """Launch Slowloris HTTP header starvation from h5 targeting h3:80 (~45 PPS)."""
        info('    -> h5 (10.0.0.5): Slowloris HTTP Starvation (:80 @ ~45 PPS)\n')
        self.mn.get('h5').cmd(f'python3 {SLOWLORIS_SCRIPT} 10.0.0.3 80 90 --src-ip 10.0.0.5 >/dev/null 2>&1 &')

    def do_icmp(self, _line):
        """Launch high-rate ICMP ping flood from h6 targeting h3 (~5,200 PPS)."""
        info('    -> h6 (10.0.0.6): High-Rate ICMP Echo Flood (@ ~5,200 PPS)\n')
        self.mn.get('h6').cmd(f'python3 {FLOODER_SCRIPT} --proto icmp --target 10.0.0.3 --rate 5200 --src-ip 10.0.0.6 >/dev/null 2>&1 &')

    def do_highport(self, _line):
        """Launch high-port UDP flood from h7 targeting h3:8080 (~11,400 PPS)."""
        info('    -> h7 (10.0.0.7): High-Port UDP Flood (:8080 @ ~11,400 PPS)\n')
        self.mn.get('h7').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 8080 --rate 11400 --src-ip 10.0.0.7 >/dev/null 2>&1 &')

    def do_pulse(self, _line):
        """Launch dynamic pulsing wave DDoS from h8 targeting h3:53 (10s ON ~7,600 PPS / 5s OFF)."""
        info('    -> h8 (10.0.0.8): True Pulsing Wave DDoS (10s ON @ ~7,600 PPS / 5s OFF on :53 UDP)\n')
        self.mn.get('h8').cmd(f'python3 {FLOODER_SCRIPT} --proto pulse --target 10.0.0.3 --port 53 --rate 7600 --on 10 --off 5 --src-ip 10.0.0.8 >/dev/null 2>&1 &')

    def do_mixed(self, _line):
        """Launch Same-IP Mixed Traffic Demo (h2 and h4 carry concurrent legit + attack streams)."""
        info('*** [MIXED TRAFFIC] Launching concurrent benign and hostile streams on same IPs:\n')
        info('    -> h2 (10.0.0.2): Attack (:80 UDP @ ~9,500 PPS) [DROPPED] + Legit (:5001 UDP @ ~440 PPS) [PASSED]\n')
        self.mn.get('h2').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 80 --rate 9500 --src-ip 10.0.0.2 >/dev/null 2>&1 &')
        self.mn.get('h2').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 5001 --rate 440 --src-ip 10.0.0.2 >/dev/null 2>&1 &')

        info('    -> h4 (10.0.0.4): Attack (:80 SYN @ ~6,800 PPS) [DROPPED] + Legit (:53 UDP @ ~230 PPS) [PASSED]\n')
        self.mn.get('h4').cmd(f'python3 {FLOODER_SCRIPT} --proto tcp_syn --target 10.0.0.3 --port 80 --rate 6800 --src-ip 10.0.0.4 >/dev/null 2>&1 &')
        self.mn.get('h4').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 53 --rate 230 --src-ip 10.0.0.4 >/dev/null 2>&1 &')

    def do_botnet(self, _line):
        """Launch distributed botnet attack across hosts h2, h4, h5, h6, h7, h8 targeting h3."""
        info('*** [ATTACK] Dispatched multi-vector botnet assault against 10.0.0.3:\n')

        # 1. Ensure legitimate background streams are actively running
        self.do_legit('')

        # 2. h2: Volumetric UDP Flood (port 80) + concurrent legitimate stream (port 5001)
        info('    -> h2 (10.0.0.2): Volumetric UDP Flood (:80 @ ~9,500 PPS) + Legit Stream (:5001 @ ~440 PPS)\n')
        self.mn.get('h2').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 80 --rate 9500 --src-ip 10.0.0.2 >/dev/null 2>&1 &')
        self.mn.get('h2').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 5001 --rate 440 --src-ip 10.0.0.2 >/dev/null 2>&1 &')

        # 3. h4: TCP SYN Handshake Flood (port 80) + concurrent legitimate stream (port 53)
        info('    -> h4 (10.0.0.4): TCP SYN Flood (:80 @ ~6,800 PPS) + Legit Stream (:53 @ ~230 PPS)\n')
        self.mn.get('h4').cmd(f'python3 {FLOODER_SCRIPT} --proto tcp_syn --target 10.0.0.3 --port 80 --rate 6800 --src-ip 10.0.0.4 >/dev/null 2>&1 &')
        self.mn.get('h4').cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 53 --rate 230 --src-ip 10.0.0.4 >/dev/null 2>&1 &')

        # 4. h5: Slowloris HTTP Starvation
        self.do_slowloris('')

        # 5. h6: ICMP Echo Flood
        self.do_icmp('')

        # 6. h7: High-Port UDP Flood (port 8080)
        self.do_highport('')

        # 7. h8: True Pulsing / Wave DDoS (10s ON / 5s OFF on port 53 UDP)
        self.do_pulse('')

        info('*** Distributed multi-vector botnet assault is running (~40,500 Attack PPS + ~1,985 Clean PPS)!\n')
        info('*** Type "stop_attack" to halt attacks while retaining legitimate traffic.\n')

    def do_stop_attack(self, _line):
        """Stop all attacks across botnet nodes while retaining legitimate user traffic."""
        info('*** Halting all botnet attack processes...\n')
        for h in ['h5', 'h6', 'h7', 'h8']:
            node = self.mn.get(h)
            if node:
                node.cmd('pkill -9 -f traffic_flooder 2>/dev/null')
                node.cmd('pkill -9 -f slowloris 2>/dev/null')
                node.cmd('pkill -9 -f hping3 2>/dev/null')

        # On mixed nodes h2 and h4, stop attack streams (:80) while preserving benign streams (:5001, :53)
        self.mn.get('h2').cmd('pkill -9 -f "traffic_flooder.*--port 80" 2>/dev/null')
        self.mn.get('h2').cmd('pkill -9 -f "hping3.*-p 80" 2>/dev/null')
        self.mn.get('h4').cmd('pkill -9 -f "traffic_flooder.*tcp_syn" 2>/dev/null')
        self.mn.get('h4').cmd('pkill -9 -f "traffic_flooder.*--port 80" 2>/dev/null')
        self.mn.get('h4').cmd('pkill -9 -f "hping3.*-p 80" 2>/dev/null')

        info('*** All botnet attacks stopped. Legitimate traffic from h1, h11, h12, h2, h4 continues.\n')

    def do_stop_all(self, _line):
        """Stop all traffic (both attacks and legitimate user traffic)."""
        self.do_stop_attack(_line)
        for h in ['h1', 'h11', 'h12', 'h2', 'h4']:
            node = self.mn.get(h)
            if node:
                node.cmd('pkill -9 -f traffic_flooder 2>/dev/null')
                node.cmd('pkill -9 -f legit_web_client 2>/dev/null')
                node.cmd('pkill -9 -f hping3 2>/dev/null')
                node.cmd('pkill -9 -f iperf 2>/dev/null')
        info('*** All traffic (legitimate + attack) halted.\n')

    def do_menu(self, line):
        """Interactive Attack & Traffic Launchpad."""
        choice = line.strip()
        if not choice:
            print("\n======================================================================")
            print("       SDN DDOS MITIGATION — ATTACK EMULATION LAUNCHPAD               ")
            print("======================================================================")
            print(" Target Server : 10.0.0.3 (Host h3)")
            print(" Detection     : Tier-1 CIC-DDoS2019 Decision Tree (Ryu Controller)")
            print(" Granularity   : Flow-Tuple Mitigation (Same-IP Mixed Allowed + Dropped)")
            print("======================================================================")
            print("Select an emulation vector to launch:")
            print("  [1]  Volumetric UDP Flood       (h2: 10.0.0.2 :80 @ ~9,500 PPS)")
            print("  [2]  TCP SYN Handshake Flood    (h4: 10.0.0.4 :80 @ ~6,800 PPS)")
            print("  [3]  Slowloris HTTP Starvation  (h5: 10.0.0.5 :80 @ ~45 PPS)")
            print("  [4]  High-Rate ICMP Ping Flood  (h6: 10.0.0.6 @ ~5,200 PPS)")
            print("  [5]  Dynamic Pulsing Wave DDoS  (h8: 10.0.0.8 10s ON ~7,600 PPS / 5s OFF)")
            print("  [6]  Coordinated Botnet Assault (Launches h2, h4-h8 with distinct rates)")
            print("  [7]  Same-IP Mixed Traffic Demo (h2 and h4 simultaneous legit + attack)")
            print("  [8]  High-Port UDP Flood        (h7: 10.0.0.7 :8080 @ ~11,400 PPS)")
            print("  [9]  Start Legitimate Streams   (h1, h11, h12 baseline ~1,315 PPS)")
            print("  [10] Stop Attack Traffic        (Halts attacks; retains legitimate streams)")
            print("  [11] Stop All Traffic           (Halts attacks AND legitimate traffic)")
            print("  [0]  Return to CLI")
            print("======================================================================")
            try:
                choice = input("Enter choice [0-11]: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("")
                return

        actions = {
            '1': self.do_udp,
            'udp': self.do_udp,
            '2': self.do_syn,
            'syn': self.do_syn,
            '3': self.do_slowloris,
            'slowloris': self.do_slowloris,
            '4': self.do_icmp,
            'icmp': self.do_icmp,
            '5': self.do_pulse,
            'pulse': self.do_pulse,
            '6': self.do_botnet,
            'botnet': self.do_botnet,
            '7': self.do_mixed,
            'mixed': self.do_mixed,
            '8': self.do_highport,
            'highport': self.do_highport,
            '9': self.do_legit,
            'legit': self.do_legit,
            '10': self.do_stop_attack,
            'stop_attack': self.do_stop_attack,
            'stop': self.do_stop_attack,
            '11': self.do_stop_all,
            'stop_all': self.do_stop_all,
            '0': lambda _: None
        }

        func = actions.get(choice)
        if func:
            func('')
        else:
            print(f"Unknown option '{choice}'. Available: 0-11 or command names.\n")

    def do_status(self, _line):
        """Show running traffic processes on all hosts."""
        info('*** Network Traffic Status:\n')
        info('h3  (Server)     : ' + self.mn.get('h3').cmd('pgrep -a -f server_h3 || echo "Idle"').strip() + '\n')
        info('h1  (Legit Stream): ' + self.mn.get('h1').cmd('pgrep -a -f traffic_flooder || echo "Idle"').strip() + '\n')
        info('h11 (Legit Web)   : ' + self.mn.get('h11').cmd('pgrep -a -f legit_web_client || echo "Idle"').strip() + '\n')
        info('h12 (Legit DNS)   : ' + self.mn.get('h12').cmd('pgrep -a -f traffic_flooder || echo "Idle"').strip() + '\n')
        for h in ['h2', 'h4', 'h5', 'h6', 'h7', 'h8']:
            p = self.mn.get(h).cmd('pgrep -a -f traffic_flooder; pgrep -a -f slowloris').strip()
            info(f'{h:<3} (Mixed/Attack): ' + (p if p else "Idle") + '\n')

def create_botnet_network():
    setLogLevel('info')
    cleanup_stale()

    CONTROLLER_IP = os.environ.get('CONTROLLER_IP', '127.0.0.1')

    info(f'*** Creating botnet network, connecting to controller at {CONTROLLER_IP}\n')
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch)

    info('*** Adding controller\n')
    c0 = net.addController('c0', controller=RemoteController, ip=CONTROLLER_IP, port=6653)

    info('*** Adding OpenFlow 1.3 switch\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    info('*** Adding protected server (h3: 10.0.0.3)\n')
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')

    info('*** Adding pure legitimate users (h1, h11, h12)\n')
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01') # Streaming client
    h11 = net.addHost('h11', ip='10.0.0.11', mac='00:00:00:00:00:11') # Web client
    h12 = net.addHost('h12', ip='10.0.0.12', mac='00:00:00:00:00:12') # DNS client

    info('*** Adding attacker / mixed nodes (h2, h4, h5, h6, h7, h8)\n')
    botnet = {}
    for i in [2, 4, 5, 6, 7, 8]:
        name = f'h{i}'
        ip = f'10.0.0.{i}'
        mac = f'00:00:00:00:00:0{i}'
        botnet[name] = net.addHost(name, ip=ip, mac=mac)

    info('*** Creating switch links\n')
    net.addLink(h1, s1)
    net.addLink(botnet['h2'], s1)
    net.addLink(h3, s1)
    net.addLink(botnet['h4'], s1)
    net.addLink(botnet['h5'], s1)
    net.addLink(botnet['h6'], s1)
    net.addLink(botnet['h7'], s1)
    net.addLink(botnet['h8'], s1)
    net.addLink(h11, s1)
    net.addLink(h12, s1)

    info('*** Starting network\n')
    net.start()

    info('*** Starting target services on h3 (multi-threaded HTTP/UDP server)\n')
    h3.cmd(f'python3 {SERVER_SCRIPT} >/dev/null 2>&1 &')

    # Fast ARP learning: ping each host to h3 directly (< 0.5s)
    info('*** Quick ARP/MAC learning (all hosts -> target server h3)...\n')
    for h in [h1, h11, h12] + list(botnet.values()):
        net.ping([h, h3])
    info('*** Botnet network is fully initialized and ready.\n')
    info('*** Hosts active: Server (h3), Pure Legit (h1, h11, h12), Mixed/Attackers (h2, h4, h5, h6, h7, h8)\n')

    # Start pure legitimate user streams by default
    info('*** Bootstrapping baseline legitimate user streams...\n')
    h1.cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 5001 --rate 820 --src-ip 10.0.0.1 >/dev/null 2>&1 &')
    h11.cmd(f'python3 {LEGIT_WEB_SCRIPT} 10.0.0.3 80 310 >/dev/null 2>&1 &')
    h12.cmd(f'python3 {FLOODER_SCRIPT} --proto udp --target 10.0.0.3 --port 53 --rate 185 --src-ip 10.0.0.12 >/dev/null 2>&1 &')
    info('    • h1  (10.0.0.1)  -> 10.0.0.3:5001 [UDP Video Stream] (~820 PPS) [ALLOWED]\n')
    info('    • h11 (10.0.0.11) -> 10.0.0.3:80   [HTTP Web Client]  (~310 PPS) [ALLOWED]\n')
    info('    • h12 (10.0.0.12) -> 10.0.0.3:53   [DNS Queries]      (~185 PPS) [ALLOWED]\n')

    info('\n========================================================================\n')
    info('*** BOTNET TOPOLOGY READY — INTERACTIVE CLI COMMANDS:\n')
    info('  • botnet      : Launch distributed multi-vector attack (h2, h4-h8)\n')
    info('  • legit       : Restart legitimate user streams (h1, h11, h12)\n')
    info('  • udp         : Volumetric UDP flood (h2: 10.0.0.2 :80 @ ~9,500 PPS)\n')
    info('  • syn         : TCP SYN flood (h4: 10.0.0.4 :80 @ ~6,800 PPS)\n')
    info('  • slowloris   : Slowloris HTTP starvation (h5: 10.0.0.5 :80 @ ~45 PPS)\n')
    info('  • icmp        : High-rate ICMP ping flood (h6: 10.0.0.6 @ ~5,200 PPS)\n')
    info('  • pulse       : Dynamic pulsing wave DDoS (h8: 10.0.0.8 :53 @ ~7,600 PPS)\n')
    info('  • highport    : High-port UDP flood (h7: 10.0.0.7 :8080 @ ~11,400 PPS)\n')
    info('  • mixed       : Same-IP mixed traffic demo (h2 and h4)\n')
    info('  • stop_attack : Stop all botnet attacks (keeps legitimate traffic on)\n')
    info('  • stop_all    : Stop all traffic (attacks + legitimate)\n')
    info('  • menu        : Open interactive attack menu (or type: menu <0-11>)\n')
    info('  • status      : Inspect running traffic processes across all nodes\n')
    info('  • pingall     : Test ping connectivity across all 10 nodes\n')
    info('========================================================================\n\n')

    auto_attack = ('--attack' in sys.argv or '--botnet' in sys.argv or '-a' in sys.argv)
    try:
        cli = BotnetCLI(net)
        if auto_attack:
            info('\n*** [--attack flag detected] Auto-launching coordinated multi-vector botnet assault...\n')
            cli.do_botnet('')
            info('*** Multi-vector botnet assault is ACTIVE! Press Ctrl+C anytime to stop.\n')
            while True:
                time.sleep(1.0)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        info('*** Stopping network and cleaning up...\n')
        for h in [h1, h11, h12]:
            h.cmd('pkill -9 -f "traffic_flooder" 2>/dev/null')
            h.cmd('pkill -9 -f "legit_web_client" 2>/dev/null')
            h.cmd('pkill -9 -f "hping3" 2>/dev/null')
            h.cmd('pkill -9 -f "iperf" 2>/dev/null')
        h3.cmd('pkill -9 -f "server_h3" 2>/dev/null')
        for b in botnet.values():
            b.cmd('pkill -9 -f "traffic_flooder" 2>/dev/null')
            b.cmd('pkill -9 -f "slowloris" 2>/dev/null')
            b.cmd('pkill -9 -f "hping3" 2>/dev/null')
            b.cmd('pkill -9 -f "bash" 2>/dev/null')
        net.stop()
        cleanup_stale()

if __name__ == '__main__':
    create_botnet_network()
