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
    sudo mn -c
    sudo python3 network/topo_botnet.py
"""

import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def create_botnet_network():
    setLogLevel('info')
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
    
    CLI(net)
    
    info('*** Stopping network\n')
    h1.cmd('pkill -f "iperf"')
    h3.cmd('pkill -f "http.server"')
    h3.cmd('pkill -f "iperf"')
    net.stop()

if __name__ == '__main__':
    create_botnet_network()
