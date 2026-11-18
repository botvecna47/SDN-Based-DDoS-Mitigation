#!/usr/bin/env python3
"""
Multi-Host Botnet Topology for Distributed DDoS Emulation & Mixed-Traffic Verification
======================================================================================
Spins up a 10-host Mininet topology connecting to OpenFlow 1.3 switch s1:
  - Target Server:
      • h3  (10.0.0.3): Protected Server running multi-threaded HTTP (port 80/8080),
                        iperf UDP server (5001), and UDP/DNS responder (port 53)
  - Pure Legitimate Users (distinct IPs):
      • h1  (10.0.0.1) : Legitimate streaming client (iperf / UDP :5001 @ ~820 pkts/s)
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

def cleanup_stale():
    """Removes stale veth interfaces and switch bridges to prevent RTNETLINK File exists errors."""
    info('*** Auto-cleaning stale virtual interfaces and switch bridges...\n')
    os.system("ovs-vsctl --if-exists del-br s1 2>/dev/null")
    os.system("ip link show | grep -oE '(s1-eth[0-9]+|h[0-9]+-eth[0-9]+)' | xargs -r -n 1 ip link delete 2>/dev/null")
    os.system("pkill -9 -f 'iperf' 2>/dev/null")
    os.system("pkill -9 -f 'server_h3.py' 2>/dev/null")
    os.system("pkill -9 -f 'http.server' 2>/dev/null")
    os.system("pkill -9 -f 'hping3' 2>/dev/null")
    os.system("pkill -9 -f 'slowloris' 2>/dev/null")
    os.system("pkill -9 -f 'pulse_h8' 2>/dev/null")

class BotnetCLI(CLI):
    prompt = 'mininet-botnet> '

    def __init__(self, mininet, *args, **kwargs):
        self.net = mininet
        super().__init__(mininet, *args, **kwargs)

    def do_botnet(self, _line):
        """Launch distributed botnet attack across hosts h2, h4, h5, h6, h7, h8 targeting h3."""
        info('*** [ATTACK] Dispatched multi-vector botnet assault against 10.0.0.3:\n')
        
        # h2: Volumetric UDP Flood (port 80) + concurrent legitimate stream (port 5001)
        info('    -> h2 (10.0.0.2): Volumetric UDP Flood (:80 @ ~9,500 PPS) + Legit Stream (:5001 @ ~440 PPS)\n')
        self.mn.get('h2').cmd('hping3 -i u105 --udp -p 80 10.0.0.3 >/dev/null 2>&1 &')
        self.mn.get('h2').cmd('hping3 -i u2270 --udp -p 5001 10.0.0.3 >/dev/null 2>&1 &')
        
        # h4: TCP SYN Handshake Flood (port 80) + concurrent legitimate stream (port 53)
        info('    -> h4 (10.0.0.4): TCP SYN Flood (:80 @ ~6,800 PPS) + Legit Stream (:53 @ ~230 PPS)\n')
        self.mn.get('h4').cmd('hping3 -i u147 -S -p 80 10.0.0.3 >/dev/null 2>&1 &')
        self.mn.get('h4').cmd('hping3 -i u4350 --udp -p 53 10.0.0.3 >/dev/null 2>&1 &')
        
        # h5: Slowloris HTTP Starvation
        info('    -> h5 (10.0.0.5): Slowloris HTTP Starvation (:80 @ ~45 PPS)\n')
        self.mn.get('h5').cmd(f'python3 {SLOWLORIS_SCRIPT} 10.0.0.3 80 90 --src-ip 10.0.0.5 >/dev/null 2>&1 &')
        
        # h6: ICMP Echo Flood
        info('    -> h6 (10.0.0.6): High-Rate ICMP Echo Flood (@ ~5,200 PPS)\n')
        self.mn.get('h6').cmd('hping3 -i u192 --icmp 10.0.0.3 >/dev/null 2>&1 &')
        
        # h7: High-Port UDP Flood (port 8080)
        info('    -> h7 (10.0.0.7): High-Port UDP Flood (:8080 @ ~11,400 PPS)\n')
        self.mn.get('h7').cmd('hping3 -i u88 --udp -p 8080 10.0.0.3 >/dev/null 2>&1 &')
        
        # h8: True Pulsing / Wave DDoS (10s ON / 5s OFF on port 53 UDP)
        info('    -> h8 (10.0.0.8): True Pulsing Wave DDoS (10s ON @ ~7,600 PPS / 5s OFF on :53 UDP)\n')
        h8_pulse_script = (
            'bash -c \'while true; do '
            'hping3 -i u131 --udp -p 53 10.0.0.3 >/dev/null 2>&1 & '
            'HP_PID=$!; sleep 10; kill -9 $HP_PID 2>/dev/null; sleep 5; '
            'done\' &'
        )
        self.mn.get('h8').cmd(h8_pulse_script)
        
        info('*** Distributed multi-vector botnet assault is running! Type "stop_attack" to halt attacks.\n')

    def do_stop_attack(self, _line):
        """Stop all attacks across botnet nodes while retaining legitimate user traffic."""
        info('*** Halting all botnet attack processes...\n')
        for h in ['h5', 'h6', 'h7', 'h8']:
            node = self.mn.get(h)
            if node:
                node.cmd('pkill -9 -f hping3 2>/dev/null')
                node.cmd('pkill -9 -f slowloris 2>/dev/null')
                node.cmd('pkill -9 -f bash 2>/dev/null')
        # On mixed nodes h2 and h4, stop attack streams (:80) while preserving benign streams (:5001, :53)
        self.mn.get('h2').cmd('pkill -9 -f "hping3.*-p 80" 2>/dev/null')
        self.mn.get('h4').cmd('pkill -9 -f "hping3.*-p 80" 2>/dev/null')
        info('*** All botnet attacks stopped. Legitimate traffic from h1, h11, h12, h2, h4 continues.\n')

    def do_stop_all(self, _line):
        """Stop all traffic (both attacks and legitimate user traffic)."""
        self.do_stop_attack(_line)
        for h in ['h1', 'h11', 'h12', 'h2', 'h4']:
            node = self.mn.get(h)
            if node:
                node.cmd('pkill -9 -f hping3 2>/dev/null')
                node.cmd('pkill -9 -f iperf 2>/dev/null')
        info('*** All traffic (legitimate + attack) halted.\n')

    def do_legit(self, _line):
        """Start or restart continuous legitimate background traffic (h1, h11, h12 -> h3)."""
        # h1: UDP streaming to port 5001 (~820 PPS)
        h1 = self.mn.get('h1')
        h1.cmd('pkill -9 -f iperf 2>/dev/null')
        h1.cmd('pkill -9 -f hping3 2>/dev/null')
        h1.cmd('hping3 -i u1220 --udp -p 5001 10.0.0.3 >/dev/null 2>&1 &')
        
        # h11: Legitimate HTTP web traffic to port 80 (~310 PPS)
        h11 = self.mn.get('h11')
        h11.cmd('pkill -9 -f curl 2>/dev/null')
        h11.cmd('pkill -9 -f hping3 2>/dev/null')
        h11.cmd('while true; do curl -s -m 1 http://10.0.0.3/ >/dev/null 2>&1; sleep 0.003; done &')

        # h12: Legitimate DNS query traffic to port 53 (~185 PPS)
        h12 = self.mn.get('h12')
        h12.cmd('pkill -9 -f hping3 2>/dev/null')
        h12.cmd('hping3 -i u5400 --udp -p 53 10.0.0.3 >/dev/null 2>&1 &')

        info('*** Continuous legitimate user traffic active:\n')
        info('    • h1  (10.0.0.1)  -> 10.0.0.3:5001 [UDP Stream] (~820 PPS)\n')
        info('    • h11 (10.0.0.11) -> 10.0.0.3:80   [HTTP Web]    (~310 PPS)\n')
        info('    • h12 (10.0.0.12) -> 10.0.0.3:53   [DNS Queries] (~185 PPS)\n')

    def do_menu(self, _line):
        """Run the interactive attack menu inside host h2."""
        h2 = self.mn.get('h2')
        h2.cmdPrint('bash network/attack_menu.sh')

    def do_status(self, _line):
        """Show running traffic processes on all hosts."""
        info('*** Network Traffic Status:\n')
        info('h3  (Server)     : ' + self.mn.get('h3').cmd('pgrep -a -f server_h3 || echo "Idle"').strip() + '\n')
        info('h1  (Legit Stream): ' + self.mn.get('h1').cmd('pgrep -a hping3 || pgrep -a iperf || echo "Idle"').strip() + '\n')
        info('h11 (Legit Web)   : ' + self.mn.get('h11').cmd('pgrep -a hping3 || echo "Idle"').strip() + '\n')
        info('h12 (Legit DNS)   : ' + self.mn.get('h12').cmd('pgrep -a hping3 || echo "Idle"').strip() + '\n')
        for h in ['h2', 'h4', 'h5', 'h6', 'h7', 'h8']:
            p = self.mn.get(h).cmd('pgrep -a hping3; pgrep -a -f slowloris; pgrep -a -f bash').strip()
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
    net.addLink(h3, s1)
    net.addLink(h1, s1)
    net.addLink(h11, s1)
    net.addLink(h12, s1)
    for b in botnet.values():
        net.addLink(b, s1)
        
    info('*** Starting network\n')
    net.start()

    info('*** Starting target services on h3 (multi-threaded HTTP/UDP server)\n')
    h3.cmd(f'python3 {SERVER_SCRIPT} >/dev/null 2>&1 &')
    h3.cmd('iperf -s -u -p 5001 >/dev/null 2>&1 &')
    
    # Fast ARP learning: ping each host to h3 directly (< 0.5s instead of 20s for pingAll)
    info('*** Quick ARP/MAC learning (all hosts -> target server h3)...\n')
    for h in [h1, h11, h12] + list(botnet.values()):
        net.ping([h, h3])
    info('*** Botnet network is fully initialized and ready.\n')
    info('*** Hosts active: Server (h3), Pure Legit (h1, h11, h12), Mixed/Attackers (h2, h4, h5, h6, h7, h8)\n')
    
    # Start pure legitimate user streams by default
    info('*** Bootstrapping baseline legitimate user streams...\n')
    h1.cmd('hping3 -i u1220 --udp -p 5001 10.0.0.3 >/dev/null 2>&1 &')
    h11.cmd('while true; do curl -s -m 1 http://10.0.0.3/ >/dev/null 2>&1; sleep 0.003; done &')
    h12.cmd('hping3 -i u5400 --udp -p 53 10.0.0.3 >/dev/null 2>&1 &')
    info('    • h1  (10.0.0.1)  -> 10.0.0.3:5001 [UDP Stream] (~820 PPS)\n')
    info('    • h11 (10.0.0.11) -> 10.0.0.3:80   [HTTP Web]    (~310 PPS)\n')
    info('    • h12 (10.0.0.12) -> 10.0.0.3:53   [DNS Queries] (~185 PPS)\n')
    
    info('\n========================================================================\n')
    info('*** BOTNET TOPOLOGY READY — INTERACTIVE CLI COMMANDS:\n')
    info('  • botnet      : Launch distributed multi-vector attack (h2, h4-h8)\n')
    info('  • stop_attack : Stop all botnet attacks (keeps legitimate traffic on)\n')
    info('  • stop_all    : Stop all traffic (attacks + legitimate)\n')
    info('  • legit       : Restart legitimate user streams (h1, h11, h12)\n')
    info('  • menu        : Open interactive attack menu inside h2\n')
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
            h.cmd('pkill -9 -f "iperf" 2>/dev/null')
            h.cmd('pkill -9 -f "hping3" 2>/dev/null')
            h.cmd('pkill -9 -f "curl" 2>/dev/null')
        h3.cmd('pkill -9 -f "server_h3" 2>/dev/null')
        h3.cmd('pkill -9 -f "iperf" 2>/dev/null')
        for b in botnet.values():
            b.cmd('pkill -9 -f "hping3" 2>/dev/null')
            b.cmd('pkill -9 -f "slowloris" 2>/dev/null')
            b.cmd('pkill -9 -f "bash" 2>/dev/null')
        net.stop()
        cleanup_stale()

if __name__ == '__main__':
    create_botnet_network()
