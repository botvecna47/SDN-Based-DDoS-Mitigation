# OpenFlow 1.3 DDoS Mitigation Module

def push_drop_rule(datapath, src_ip, dst_ip=None, ip_proto=None, dst_port=None):
    """
    Constructs and sends an OFPFlowMod message to BLOCK traffic.
    When flow tuple parameters (ip_proto, dst_port, dst_ip) are supplied,
    installs a flow-granular DROP rule matching that specific malicious flow
    tuple rather than blackholing the entire source IP.
    
    This enables same-IP mixed traffic scenarios:
    - Malicious flow (e.g. 10.0.0.2:80 UDP flood) matches Priority 65535 DROP rule.
    - Benign flow from same IP (e.g. 10.0.0.2:5001 UDP) continues matching Priority 10 FORWARD rule.
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    
    match_kwargs = {'eth_type': 0x0800, 'ipv4_src': src_ip}
    if dst_ip:
        match_kwargs['ipv4_dst'] = dst_ip
    
    if ip_proto is not None:
        proto = int(ip_proto)
        match_kwargs['ip_proto'] = proto
        if proto == 6:  # TCP
            if dst_port is not None and int(dst_port) > 0:
                match_kwargs['tcp_dst'] = int(dst_port)
        elif proto == 17:  # UDP
            if dst_port is not None and int(dst_port) > 0:
                match_kwargs['udp_dst'] = int(dst_port)
        elif proto == 1:  # ICMP
            pass

    match = parser.OFPMatch(**match_kwargs)
    actions = []
    instructions = [parser.OFPInstructionActions(ofproto.OFPIT_CLEAR_ACTIONS, actions)]
    
    mod = parser.OFPFlowMod(
        datapath=datapath,
        priority=65535,  # Highest priority to preempt Priority 10 forwarding rules
        match=match,
        instructions=instructions,
        command=ofproto.OFPFC_ADD,
        idle_timeout=300,  # Auto-expire after 5 minutes of inactivity
        hard_timeout=0,
        flags=ofproto.OFPFF_SEND_FLOW_REM
    )
    
    datapath.send_msg(mod)
    print(f"DROP rule installed: {match_kwargs} (Priority 65535)")


def remove_drop_rule(datapath, src_ip, dst_ip=None, ip_proto=None, dst_port=None):
    """
    Removes an existing drop rule (OFPFC_DELETE).
    Matches the exact flow tuple or IP rule previously installed.
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    
    match_kwargs = {'eth_type': 0x0800, 'ipv4_src': src_ip}
    if dst_ip:
        match_kwargs['ipv4_dst'] = dst_ip
    
    if ip_proto is not None:
        proto = int(ip_proto)
        match_kwargs['ip_proto'] = proto
        if proto == 6:
            if dst_port is not None and int(dst_port) > 0:
                match_kwargs['tcp_dst'] = int(dst_port)
        elif proto == 17:
            if dst_port is not None and int(dst_port) > 0:
                match_kwargs['udp_dst'] = int(dst_port)
        elif proto == 1:
            pass

    match = parser.OFPMatch(**match_kwargs)
    
    mod = parser.OFPFlowMod(
        datapath=datapath,
        match=match,
        command=ofproto.OFPFC_DELETE,
        out_port=ofproto.OFPP_ANY,
        out_group=ofproto.OFPG_ANY
    )
    
    datapath.send_msg(mod)
    print(f"DROP rule removed: {match_kwargs}")
