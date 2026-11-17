#!/usr/bin/env python3
import os
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

def create_network():
    setLogLevel('info')
    cleanup_stale()
    
    # Ryu runs in the same Ubuntu VM by default. Override only if it runs elsewhere.
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

    info('*** Starting iperf UDP and HTTP servers on h3\n')
    h3.cmd('iperf -s -u &')
    h3.cmd('python3 -m http.server 80 &')
    
    info('*** Bootstrapping MAC learning with pingall\n')
    net.pingAll()
    info('*** MAC learning complete. Network is ready.\n')
    
    info('*** Starting continuous legitimate background user traffic (h1 -> h3 @ ~850 PPS)\n')
    h1.cmd('iperf -c 10.0.0.3 -u -b 10m -t 86400 &')
    
    try:
        info('*** Running CLI (Type "pingall" to test, or "exit" to quit)\n')
        CLI(net)
    finally:
        info('*** Stopping network\n')
        h1.cmd('pkill -f "iperf" 2>/dev/null')
        h3.cmd('pkill -f "http.server" 2>/dev/null')
        h3.cmd('pkill -f "iperf" 2>/dev/null')
        net.stop()
        cleanup_stale()

if __name__ == '__main__':
    create_network()
