# OpenFlow 1.3 DDoS Mitigation Module

def push_drop_rule(datapath, src_ip):
    """
    Constructs and sends an OFPFlowMod message to BLOCK traffic from src_ip.
    
    OpenFlow 1.3 specifics used here:
    - ofproto: The OpenFlow protocol constants for this datapath
    - parser: The OpenFlow message constructor/parser for this datapath
    - match: Defines what packets this rule applies to. We match IPv4 packets (eth_type=0x0800)
             originating from the attacker's IP (ipv4_src=src_ip).
    - instructions: What to do with the matching packets.
             We use OFPIT_CLEAR_ACTIONS with an empty list, meaning DROP the packet.
    - priority: Highest priority (65535) so this rule overrides normal forwarding rules.
    - idle_timeout: Rule expires if no matching packets are seen for 300 seconds (5 mins).
    - hard_timeout: Rule forcefully expires after 600 seconds (10 mins) regardless of activity.
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    
    # Match any IPv4 packet coming from the specified source IP
    match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip)
    
    # Empty actions = DROP
    actions = []
    
    # Clear any existing actions (drop the packet)
    instructions = [parser.OFPInstructionActions(ofproto.OFPIT_CLEAR_ACTIONS, actions)]
    
    # Construct the Flow Modification message to ADD the rule
    mod = parser.OFPFlowMod(
        datapath=datapath,
        priority=65535,  # Highest priority to preempt normal forwarding
        match=match,
        instructions=instructions,
        command=ofproto.OFPFC_ADD,
        idle_timeout=300,  # Auto-expire after 5 minutes of inactivity
        hard_timeout=600   # Auto-expire after 10 minutes total
    )
    
    # Send the rule to the switch
    datapath.send_msg(mod)
    print(f"DROP rule installed for IP: {src_ip}")


def push_rate_limit_rule(datapath, src_ip, rate_kbps):
    """
    BONUS: For future use. Structure is identical but with a meter action instead of drop.
    """
    # TODO: Implement rate limiting using OpenFlow Meters.
    # Note: The meter ID would need to be pre-configured on the switch using an OFPMeterMod message
    # before we can reference it here in an OFPInstructionMeter.
    pass


def remove_drop_rule(datapath, src_ip):
    """
    Removes an existing drop rule (OFPFC_DELETE).
    Useful if we want to unblock an IP after a timeout.
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    
    # Match the exact same conditions as the drop rule
    match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip)
    
    # Construct the Flow Modification message to DELETE the rule
    mod = parser.OFPFlowMod(
        datapath=datapath,
        match=match,
        command=ofproto.OFPFC_DELETE,
        out_port=ofproto.OFPP_ANY,
        out_group=ofproto.OFPG_ANY
    )
    
    # Send the rule to the switch
    datapath.send_msg(mod)
    print(f"DROP rule removed for IP: {src_ip}")
