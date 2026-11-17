#!/usr/bin/env python3
"""
Multi-Host Botnet Topology for Distributed DDoS Emulation
=========================================================
Spins up an 8-host Mininet topology to test multi-source distributed attacks:
  - h1: Legitimate User (10.0.0.1)
  - h2-h8: Botnet Attacker Nodes (10.0.0.2 - 10.0.0.8)
  - h3: Protected Target Server (10.0.0.3)
  - s1: OpenFlow 1.3 OVS Switch connected to Ryu controller

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

def cleanup_stale():
    """Removes stale veth interfaces and switch bridges to prevent RTNETLINK File exists errors."""
    info('*** Auto-cleaning stale virtual interfaces and switch bridges...\n')
    os.system("ovs-vsctl --if-exists del-br s1 2>/dev/null")
    os.system("ip link show | grep -oE '(s1-eth[0-9]+|h[0-9]+-eth[0-9]+)' | xargs -r -n 1 ip link delete 2>/dev/null")
    os.system("pkill -9 -f 'iperf -s' 2>/dev/null")
    os.system("pkill -9 -f 'iperf -c' 2>/dev/null")
    os.system("pkill -9 -f 'http.server 80' 2>/dev/null")
    os.system("pkill -9 -f 'hping3' 2>/dev/null")
    os.system("pkill -9 -f 'slowloris.py' 2>/dev/null")

class BotnetCLI(CLI):
    prompt = 'mininet-botnet> '

    def __init__(self, mininet, *args, **kwargs):
        self.net = mininet
        super().__init__(mininet, *args, **kwargs)

    def do_botnet(self, _line):
        """Launch distributed botnet attack across hosts h2, h4, h5, h6, h7, h8 targeting h3."""
        info('*** [ATTACK] Dispatched multi-vector botnet assault against 10.0.0.3:\n')
        info('    -> h2 (10.0.0.2): Volumetric UDP Flood (port 80)\n')
        self.mn.get('h2').cmd('hping3 -i u100 --udp -p 80 10.0.0.3 >/dev/null 2>&1 &')
        info('    -> h4 (10.0.0.4): TCP SYN Handshake Flood (port 80)\n')
        self.mn.get('h4').cmd('hping3 -i u100 -S -p 80 10.0.0.3 >/dev/null 2>&1 &')
        info('    -> h5 (10.0.0.5): Slowloris HTTP Connection Starvation\n')
        self.mn.get('h5').cmd('python3 network/slowloris.py 10.0.0.3 80 80 >/dev/null 2>&1 &')
        info('    -> h6 (10.0.0.6): High-Rate ICMP Flood\n')
        self.mn.get('h6').cmd('hping3 -i u100 --icmp 10.0.0.3 >/dev/null 2>&1 &')
        info('    -> h7 (10.0.0.7): UDP Flood on port 8080\n')
        self.mn.get('h7').cmd('hping3 -i u100 --udp -p 8080 10.0.0.3 >/dev/null 2>&1 &')
        info('    -> h8 (10.0.0.8): UDP Flood on DNS port 53\n')
        self.mn.get('h8').cmd('hping3 -i u100 --udp -p 53 10.0.0.3 >/dev/null 2>&1 &')
        info('*** Botnet is running in background! Type "stop_attack" to halt.\n')

    def do_stop_attack(self, _line):
        """Stop all attacks across botnet nodes while retaining legitimate user traffic."""
        info('*** Halting all botnet attack processes...\n')
        for h in ['h2', 'h4', 'h5', 'h6', 'h7', 'h8']:
            node = self.mn.get(h)
            if node:
                node.cmd('pkill -9 -f hping3 2>/dev/null')
                node.cmd('pkill -9 -f slowloris 2>/dev/null')
        info('*** All botnet attacks stopped. Legitimate h1 user traffic is still streaming.\n')

    def do_stop_all(self, _line):
        """Stop all traffic (both attacks and legitimate user traffic)."""
        self.do_stop_attack(_line)
        self.mn.get('h1').cmd('pkill -9 -f iperf 2>/dev/null')
        info('*** All traffic (legitimate + attack) halted.\n')

    def do_legit(self, _line):
        """Start or restart continuous legitimate background traffic (h1 -> h3)."""
        h1 = self.mn.get('h1')
        h1.cmd('pkill -9 -f iperf 2>/dev/null')
        h1.cmd('iperf -c 10.0.0.3 -u -b 10m -t 86400 &')
        info('*** Continuous legitimate user traffic active (h1 -> h3 @ ~850 PPS)\n')

    def do_menu(self, _line):
        """Run the interactive attack menu inside host h2."""
        h2 = self.mn.get('h2')
        h2.cmdPrint('bash network/attack_menu.sh')

    def do_status(self, _line):
        """Show running traffic processes on all hosts."""
        info('*** Network Traffic Status:\n')
        info('h1 (Legit User) : ' + self.mn.get('h1').cmd('pgrep -a iperf || echo "Idle"').strip() + '\n')
        info('h3 (Server)     : ' + self.mn.get('h3').cmd('pgrep -a iperf || echo "No iperf"; pgrep -a -f "http.server 80" || echo "No http"').strip() + '\n')
        for h in ['h2', 'h4', 'h5', 'h6', 'h7', 'h8']:
            p = self.mn.get(h).cmd('pgrep -a hping3; pgrep -a -f slowloris').strip()
            info(f'{h} (Attacker)   : ' + (p if p else "Idle") + '\n')

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
    
    info('*** Adding hosts (h1: User, h3: Server, h2/h4-h8: Botnet Nodes)\n')
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01') # Legitimate User
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03') # Target Server
    
    # Botnet nodes h2, h4, h5, h6, h7, h8
    botnet = {}
    for i in [2, 4, 5, 6, 7, 8]:
        name = f'h{i}'
        ip = f'10.0.0.{i}'
        mac = f'00:00:00:00:00:0{i}'
        botnet[name] = net.addHost(name, ip=ip, mac=mac)
    
    info('*** Creating switch links\n')
    net.addLink(h1, s1)
    net.addLink(h3, s1)
    for b in botnet.values():
        net.addLink(b, s1)
        
    info('*** Starting network\n')
    net.start()

    info('*** Starting target services on h3 (iperf UDP + Simple HTTP Server)\n')
    h3.cmd('iperf -s -u &')
    h3.cmd('python3 -m http.server 80 &')
    
    info('*** Bootstrapping ARP/MAC learning across all 8 nodes\n')
    net.pingAll()
    info('*** Botnet network is fully initialized and ready.\n')
    info('*** Hosts available: h1 (Legitimate), h3 (Server), and Botnet Nodes: h2, h4, h5, h6, h7, h8\n')
    
    info('*** Starting continuous legitimate background user traffic (h1 -> h3 @ ~850 PPS)\n')
    h1.cmd('iperf -c 10.0.0.3 -u -b 10m -t 86400 &')
    
    info('\n========================================================================\n')
    info('*** BOTNET TOPOLOGY READY — INTERACTIVE CLI COMMANDS:\n')
    info('  • botnet      : Launch distributed multi-vector attack (h2, h4-h8)\n')
    info('  • stop_attack : Stop all botnet attacks (keeps legitimate traffic on)\n')
    info('  • stop_all    : Stop all traffic (attacks + legitimate)\n')
    info('  • legit       : Restart legitimate user stream (h1 -> h3)\n')
    info('  • menu        : Open interactive attack menu inside h2\n')
    info('  • status      : Inspect running traffic processes across all nodes\n')
    info('  • pingall     : Test ping connectivity across all 8 nodes\n')
    info('========================================================================\n\n')

    try:
        BotnetCLI(net)
    finally:
        info('*** Stopping network and cleaning up...\n')
        h1.cmd('pkill -f "iperf" 2>/dev/null')
        h3.cmd('pkill -f "http.server" 2>/dev/null')
        h3.cmd('pkill -f "iperf" 2>/dev/null')
        for b in botnet.values():
            b.cmd('pkill -f "hping3" 2>/dev/null')
            b.cmd('pkill -f "slowloris" 2>/dev/null')
        net.stop()
        cleanup_stale()

if __name__ == '__main__':
    create_botnet_network()
