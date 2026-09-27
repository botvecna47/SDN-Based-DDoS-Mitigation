#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import os

def create_network():
    setLogLevel('info')
    
    # 🚨 CHANGE THIS IP to your Windows Host IP if running in a VM!
    # If running everything on the same machine/WSL, 127.0.0.1 is fine.
    CONTROLLER_IP = os.environ.get('CONTROLLER_IP', '127.0.0.1')
    
    info(f'*** Creating network, connecting to controller at {CONTROLLER_IP}\n')
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch)
    
    info('*** Adding controller\n')
    c0 = net.addController('c0', controller=RemoteController, ip=CONTROLLER_IP, port=6653)
    
    info('*** Adding switch\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    
    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01') # Legit User
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02') # Attacker
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03') # Server
    
    info('*** Creating links\n')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    
    info('*** Starting network\n')
    net.start()
    
    info('*** Running CLI (Type "pingall" to test, or "exit" to quit)\n')
    CLI(net)
    
    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    create_network()
