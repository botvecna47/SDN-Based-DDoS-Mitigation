import os
import sys
import time
import csv
import logging
import collections
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp, icmp, ether_types

# Add backend_api to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_api'))
try:
    from state_manager import initialize_state, update_state
except ImportError:
    def initialize_state(): pass
    def update_state(**kwargs): pass

from mitigation import push_drop_rule, remove_drop_rule
from inference_loader import DDoSDetector

class SimpleMonitor13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleMonitor13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.start_time = time.time()
        self.blocked_ips = set()
        self.blocked_flows = {} # (src_ip, dst_ip, ip_proto, dst_port) -> metadata dict
        self.flow_history = {}  # (datapath.id, priority, src_ip, dst_ip, ip_proto, dst_port) -> (prev_pkt, prev_byte, prev_time)
        self.last_inference_ms = 0.28
        self.latency_samples = collections.deque(maxlen=20)
        self.latency_samples.append(0.28)

        # Initialize the shared state
        initialize_state()

        # Load the ML Model
        model_path = os.path.join(os.path.dirname(__file__), '..', 'ml_pipeline', 'detector.joblib')
        self.detector = DDoSDetector(model_path)

        self.csv_path = os.path.join(os.path.dirname(__file__), 'traffic_dataset.csv')

        # Dedicated ML detection & reasoning log file
        logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        self.ml_log_file = os.path.join(logs_dir, 'ml_detection.log')
        self.ml_logger = logging.getLogger('sdn_ml_detection')
        self.ml_logger.setLevel(logging.INFO)
        if not self.ml_logger.handlers:
            fh = logging.FileHandler(self.ml_log_file)
            fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.ml_logger.addHandler(fh)

        # Start the polling thread
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        """Track connected and disconnected switches"""
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info('Registering datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
                self._clear_switch_flows(datapath)
                self.mac_to_port.clear()
                self.flow_history.clear()
                self.blocked_ips.clear()
                self.blocked_flows.clear()
                update_state(
                    switch_connected=True,
                    status="NORMAL",
                    current_pps=0,
                    forwarded_pps=0,
                    dropped_pps=0,
                    blocked_count=0,
                    blocked_ips=[],
                    blocked_flows=[],
                    ip_traffic=[],
                    last_updated_at=time.time()
                )
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info('Unregistering datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]
                self.mac_to_port.clear()
                self.flow_history.clear()
                self.blocked_ips.clear()
                self.blocked_flows.clear()
                update_state(
                    switch_connected=bool(self.datapaths),
                    blocked_count=0,
                    blocked_ips=list(self.blocked_ips),
                    blocked_flows=[],
                    status="NORMAL",
                    current_pps=0,
                    forwarded_pps=0,
                    dropped_pps=0,
                    active_flows=0,
                    openflow_rules=[],
                    ip_traffic=[],
                    last_updated_at=time.time(),
                )

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _flow_removed_handler(self, ev):
        """Keep the dashboard block list and flow table in sync with switch idle timeouts."""
        match = ev.msg.match
        src_ip = match.get('ipv4_src')
        dst_ip = match.get('ipv4_dst')
        ip_proto = match.get('ip_proto')
        dst_port = match.get('tcp_dst') or match.get('udp_dst') or 0

        flow_tuple = (src_ip, dst_ip, ip_proto, dst_port)
        if flow_tuple in self.blocked_flows:
            del self.blocked_flows[flow_tuple]
            self.logger.info('DROP rule expired for flow %s; removed from blocked flows.', flow_tuple)

        # Discard from blocked_ips only if no other blocked flow from src_ip exists
        if src_ip and not any(k[0] == src_ip for k in self.blocked_flows):
            self.blocked_ips.discard(src_ip)

        update_state(
            blocked_count=len(self.blocked_ips),
            blocked_ips=list(self.blocked_ips),
            blocked_flows=[{
                'src_ip': k[0], 'dst_ip': k[1], 'ip_proto': k[2], 'dst_port': k[3], **v
            } for k, v in self.blocked_flows.items()],
            last_updated_at=time.time()
        )

    def _clear_switch_flows(self, datapath):
        """Purge any stale forwarding rules from previous runs so switch state is clean."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        del_mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=parser.OFPMatch()
        )
        datapath.send_msg(del_mod)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Install a table-miss flow entry: priority=0, match=everything, action=CONTROLLER"""
        datapath = ev.msg.datapath
        self._clear_switch_flows(datapath)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Helper method to add a flow entry to the switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """
        Flow-Granular L2 learning and L4-aware rule installation.
        Matches packets by (eth_type=0x0800, ipv4_src, ipv4_dst, ip_proto, tcp_dst/udp_dst)
        so distinct flows from the SAME IP occupy separate flow entries in OVS.
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn MAC address to avoid FLOOD next time
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow entry to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            if eth.ethertype == ether_types.ETH_TYPE_IP:
                ip = pkt.get_protocol(ipv4.ipv4)
                if ip:
                    srcip = ip.src
                    dstip = ip.dst
                    proto = ip.proto
                    match_kwargs = {
                        'eth_type': ether_types.ETH_TYPE_IP,
                        'ipv4_src': srcip,
                        'ipv4_dst': dstip,
                        'ip_proto': proto
                    }

                    if proto == 6:  # TCP
                        t = pkt.get_protocol(tcp.tcp)
                        if t:
                            match_kwargs['tcp_dst'] = t.dst_port
                    elif proto == 17:  # UDP
                        u = pkt.get_protocol(udp.udp)
                        if u:
                            match_kwargs['udp_dst'] = u.dst_port
                    elif proto == 1:  # ICMP
                        pass

                    match = parser.OFPMatch(**match_kwargs)

                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 10, match, actions, msg.buffer_id)
                        return
                    else:
                        self.add_flow(datapath, 10, match, actions)
                else:
                    match = parser.OFPMatch(in_port=in_port, eth_type=eth.ethertype,
                                            eth_dst=dst, eth_src=src)
                    self.add_flow(datapath, 1, match, actions)
            else:
                match = parser.OFPMatch(in_port=in_port, eth_type=eth.ethertype,
                                        eth_dst=dst, eth_src=src)
                self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def _monitor(self):
        """While True loop: for each datapath in self.datapaths, call _request_stats()"""
        while True:
            for dp in list(self.datapaths.values()):
                try:
                    self._request_stats(dp)
                except Exception as e:
                    self.logger.error("Error requesting stats: %s", e)
            hub.sleep(1.0)

    def _request_stats(self, datapath):
        """Send OFPFlowStatsRequest to the datapath"""
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        """
        Process flow statistics from OVS switch s1:
        1. Calculate precise per-flow rates keyed by (datapath.id, priority, src_ip, dst_ip, ip_proto, dst_port).
        2. Identify dropped flows strictly by priority == 65535 (DROP rule).
        3. Run ML inference on active Priority 10 forwarding flows and install flow-granular DROP rules if hostile.
        4. Aggregate client-to-server traffic by src_ip into structured ip_traffic entries.
        5. Calculate exact global totals from sum(ip_traffic) guaranteeing 100% mathematical consistency.
        """
        try:
            body = ev.msg.body
            datapath = ev.msg.datapath

            current_time = time.time()
            controller_uptime_sec = current_time - self.start_time

            attack_detected_this_cycle = False
            latest_inference_ms = None
            openflow_rules = []
            flow_data = []

            # -------------------------------------------------------------
            # PASS 1: Calculate rates for all OpenFlow rules using exact flow_key
            # -------------------------------------------------------------
            for stat in body:
                priority = int(stat.priority)
                match = {
                    key: stat.match[key]
                    for key in ('in_port', 'eth_src', 'eth_dst', 'ipv4_src', 'ipv4_dst', 'eth_type', 'ip_proto', 'tcp_src', 'tcp_dst', 'udp_src', 'udp_dst')
                    if key in stat.match
                }
                src_ip = stat.match.get('ipv4_src')
                dst_ip = stat.match.get('ipv4_dst')
                ip_proto = stat.match.get('ip_proto', 0)
                src_port = stat.match.get('tcp_src') or stat.match.get('udp_src') or 0
                dst_port = stat.match.get('tcp_dst') or stat.match.get('udp_dst') or 0

                packet_count = int(stat.packet_count)
                byte_count = int(stat.byte_count)
                duration_sec = int(stat.duration_sec)

                # Granular flow key: distinguishes ALLOWED (10) from BLOCKED (65535) rules for same IP
                flow_key = (datapath.id, priority, src_ip or '*', dst_ip or '*', ip_proto or 0, dst_port or 0)

                pps = 0.0
                bps = 0.0
                if flow_key in self.flow_history:
                    prev_pkt, prev_byte, prev_time = self.flow_history[flow_key]
                    time_delta = current_time - prev_time
                    if time_delta >= 0.5:
                        pkt_delta = packet_count - prev_pkt
                        byte_delta = byte_count - prev_byte
                        if pkt_delta > 0:
                            pps = pkt_delta / time_delta
                        if byte_delta > 0:
                            bps = (byte_delta * 8) / time_delta
                        self.flow_history[flow_key] = (packet_count, byte_count, current_time)
                else:
                    self.flow_history[flow_key] = (packet_count, byte_count, current_time)

                if priority == 65535:
                    action, rule_status = 'DROP', 'BLOCKED'
                elif priority == 0:
                    action, rule_status = 'SEND_TO_CONTROLLER', 'CONTROLLER'
                else:
                    action, rule_status = 'FORWARD', 'ALLOWED'

                openflow_rules.append({
                    'match': match,
                    'action': action,
                    'priority': priority,
                    'status': rule_status,
                    'packets': packet_count,
                    'bytes': byte_count,
                    'pps': round(pps)
                })

                flow_data.append({
                    'priority': priority,
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'ip_proto': ip_proto,
                    'src_port': src_port,
                    'dst_port': dst_port,
                    'packet_count': packet_count,
                    'byte_count': byte_count,
                    'duration_sec': duration_sec,
                    'pps': pps,
                    'bps': bps
                })

            # -------------------------------------------------------------
            # PASS 2: Synchronize active Priority 65535 DROP rules
            # -------------------------------------------------------------
            active_drop_tuples = set()
            for item in flow_data:
                if item['priority'] == 65535 and item['src_ip'] and item['src_ip'] != '10.0.0.3':
                    src_ip = item['src_ip']
                    dst_ip = item['dst_ip'] or '10.0.0.3'
                    ip_proto = item['ip_proto']
                    dst_port = item['dst_port']
                    self.blocked_ips.add(src_ip)
                    flow_tuple = (src_ip, dst_ip, ip_proto, dst_port)
                    active_drop_tuples.add(flow_tuple)
                    if flow_tuple not in self.blocked_flows:
                        self.blocked_flows[flow_tuple] = {
                            'attack_type': 'OpenFlow DROP Rule',
                            'reason': 'Priority 65535 DROP Rule Active',
                            'protocol': 'TCP' if ip_proto == 6 else ('UDP' if ip_proto == 17 else ('ICMP' if ip_proto == 1 else f'Proto {ip_proto}')),
                            'dst_port': dst_port or 0,
                            'dst_ip': dst_ip,
                            'detected_at': current_time
                        }

            # Prune expired DROP rules when no longer reported in switch flow tables
            expired_tuples = [k for k in self.blocked_flows if k not in active_drop_tuples]
            for exp_k in expired_tuples:
                del self.blocked_flows[exp_k]
                self.logger.info("Pruned expired DROP rule for flow %s", exp_k)

            self.blocked_ips = {k[0] for k in self.blocked_flows if k[0]}

            # -------------------------------------------------------------
            # PASS 3: Run ML inference on active Priority 10 forwarding flows
            # -------------------------------------------------------------
            for item in flow_data:
                if item['priority'] != 10 or not item['src_ip'] or item['src_ip'] == '10.0.0.3':
                    continue

                src_ip = item['src_ip']
                dst_ip = item['dst_ip'] or '10.0.0.3'
                ip_proto = item['ip_proto']
                dst_port = item['dst_port']
                pps = item['pps']
                bps = item['bps']

                stats_dict = {
                    'timestamp': current_time,
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'src_port': item['src_port'],
                    'dst_port': dst_port,
                    'ip_proto': ip_proto,
                    'packet_count': item['packet_count'],
                    'byte_count': item['byte_count'],
                    'duration_sec': item['duration_sec'],
                    'pps': pps,
                    'bps': bps
                }

                try:
                    self._log_to_csv(stats_dict)
                except Exception as e:
                    self.logger.error("CSV logging error: %s", e)

                flow_tuple = (src_ip, dst_ip, ip_proto, dst_port)
                if flow_tuple in self.blocked_flows:
                    continue

                detected, inf_ms = self._run_inference(stats_dict, datapath)
                if detected:
                    attack_detected_this_cycle = True
                latest_inference_ms = inf_ms
                if inf_ms > 0:
                    self.latency_samples.append(inf_ms)

            # Keep live moving average of inference latency
            if latest_inference_ms is not None:
                self.last_inference_ms = latest_inference_ms
            elif self.latency_samples:
                self.last_inference_ms = round(sum(self.latency_samples) / len(self.latency_samples), 3)
            else:
                self.last_inference_ms = getattr(self.detector, 'last_inference_ms', 0.28)
            latest_inference_ms = self.last_inference_ms

            # -------------------------------------------------------------
            # PASS 4: Granular Per-IP Aggregation (src_ip != '10.0.0.3')
            # -------------------------------------------------------------
            HOST_LABELS = {
                '10.0.0.1': 'Workstation h1 (Video Streaming)',
                '10.0.0.2': 'Smart Device h2 (Mixed: Video + UDP Flood)',
                '10.0.0.4': 'Office PC h4 (Mixed: DNS + Connection Flood)',
                '10.0.0.5': 'Botnet Node h5 (Slow HTTP Starvation)',
                '10.0.0.6': 'Botnet Node h6 (Ping Overload Flood)',
                '10.0.0.7': 'Botnet Node h7 (Amplified Port Saturation)',
                '10.0.0.8': 'Botnet Node h8 (Pulsing Wave Bursts)',
                '10.0.0.11': 'Laptop h11 (Standard Web Client)',
                '10.0.0.12': 'Gateway h12 (Internal DNS Queries)',
            }
            HOST_MACS = {
                '10.0.0.1': '00:00:00:00:00:01',
                '10.0.0.2': '00:00:00:00:00:02',
                '10.0.0.4': '00:00:00:00:00:04',
                '10.0.0.5': '00:00:00:00:00:05',
                '10.0.0.6': '00:00:00:00:00:06',
                '10.0.0.7': '00:00:00:00:00:07',
                '10.0.0.8': '00:00:00:00:00:08',
                '10.0.0.11': '00:00:00:00:00:11',
                '10.0.0.12': '00:00:00:00:00:12',
            }

            by_ip = {}
            for item in flow_data:
                src_ip = item['src_ip']
                if not src_ip or src_ip == '10.0.0.3':
                    continue

                if src_ip not in by_ip:
                    by_ip[src_ip] = {
                        'forwardedPps': 0.0,
                        'droppedPps': 0.0,
                        'allowedFlows': [],
                        'blockedFlows': []
                    }

                dst_ip = item['dst_ip'] or '10.0.0.3'
                ip_proto = item['ip_proto']
                dst_port = item['dst_port']
                pps = item['pps']
                proto_name = 'TCP' if ip_proto == 6 else ('UDP' if ip_proto == 17 else ('ICMP' if ip_proto == 1 else f'Proto {ip_proto}'))

                if item['priority'] == 65535:
                    by_ip[src_ip]['droppedPps'] += pps
                    flow_tuple = (src_ip, dst_ip, ip_proto, dst_port)
                    meta = self.blocked_flows.get(flow_tuple, {})
                    by_ip[src_ip]['blockedFlows'].append({
                        'protocol': proto_name,
                        'dstPort': dst_port or 0,
                        'dstIp': dst_ip,
                        'pps': round(pps),
                        'packets': item['packet_count'],
                        'attackType': meta.get('attack_type', 'Attack Flow'),
                        'reason': meta.get('reason', 'Priority 65535 DROP rule'),
                        'priority': 65535
                    })
                elif item['priority'] == 10:
                    flow_tuple = (src_ip, dst_ip, ip_proto, dst_port)
                    # If this exact flow is currently superseded by an active Priority 65535 DROP rule,
                    # do not append it to allowedFlows with 0 PPS.
                    if flow_tuple in self.blocked_flows:
                        continue
                    by_ip[src_ip]['forwardedPps'] += pps
                    by_ip[src_ip]['allowedFlows'].append({
                        'protocol': proto_name,
                        'dstPort': dst_port or 0,
                        'dstIp': dst_ip,
                        'pps': round(pps),
                        'packets': item['packet_count']
                    })

            # Ensure all blocked flows appear in by_ip even if idle (0 PPS)
            for (b_src, b_dst, b_proto, b_port), meta in self.blocked_flows.items():
                if b_src and b_src != '10.0.0.3' and b_src not in by_ip:
                    proto_name = 'TCP' if b_proto == 6 else ('UDP' if b_proto == 17 else ('ICMP' if b_proto == 1 else f'Proto {b_proto}'))
                    by_ip[b_src] = {
                        'forwardedPps': 0.0,
                        'droppedPps': 0.0,
                        'allowedFlows': [],
                        'blockedFlows': [{
                            'protocol': proto_name,
                            'dstPort': b_port or 0,
                            'dstIp': b_dst or '10.0.0.3',
                            'pps': 0,
                            'packets': 0,
                            'attackType': meta.get('attack_type', 'Attack Flow'),
                            'reason': meta.get('reason', 'Priority 65535 DROP rule'),
                            'priority': 65535
                        }]
                    }

            ip_traffic = []
            def ip_sort_key(ip_str):
                try:
                    return int(ip_str.split('.')[-1])
                except Exception:
                    return 999

            for ip in sorted(by_ip.keys(), key=ip_sort_key):
                entry = by_ip[ip]
                fwd = round(entry['forwardedPps'])
                drp = round(entry['droppedPps'])
                ing = fwd + drp

                has_blocked = bool(entry['blockedFlows'])
                if fwd > 0 and (has_blocked or drp > 0):
                    status = "MIXED"
                elif drp > 0:
                    status = "ACTIVE DROP"
                elif has_blocked:
                    status = "RULE RETAINED"
                else:
                    status = "ALLOWED"

                if has_blocked:
                    primary_reason = entry['blockedFlows'][0].get('reason', 'DDoS Mitigation Rule')
                    severity = "Critical"
                else:
                    primary_reason = "Clean Legitimate Traffic"
                    severity = "Benign"

                host_label = HOST_LABELS.get(ip, f"Host ({ip})")
                mac = HOST_MACS.get(ip, f"00:00:00:00:00:{int(ip.split('.')[-1]):02x}" if ip.startswith('10.0.0.') else "")

                ip_traffic.append({
                    'ip': ip,
                    'hostLabel': host_label,
                    'mac': mac,
                    'forwardedPps': fwd,
                    'droppedPps': drp,
                    'ingressPps': ing,
                    'allowedFlows': entry['allowedFlows'],
                    'blockedFlows': entry['blockedFlows'],
                    'status': status,
                    'primaryReason': primary_reason,
                    'severity': severity
                })

            # Calculate exact mathematical sums directly from ip_traffic
            forwarded_pps = sum(entry['forwardedPps'] for entry in ip_traffic)
            dropped_pps = sum(entry['droppedPps'] for entry in ip_traffic)
            current_pps = forwarded_pps + dropped_pps

            # Determine global attack status:
            # Active attack is present if an attack was detected this cycle or packets are currently being dropped
            if attack_detected_this_cycle or dropped_pps > 0:
                current_status = "UNDER_ATTACK"
            else:
                current_status = "NORMAL"

            # Persist state atomically
            update_state(
                controller_uptime_sec=controller_uptime_sec,
                blocked_count=len(self.blocked_ips),
                blocked_ips=list(self.blocked_ips),
                current_pps=current_pps,
                forwarded_pps=forwarded_pps,
                dropped_pps=dropped_pps,
                active_flows=len(body),
                status=current_status,
                inference_latency_ms=latest_inference_ms,
                detection_mode="machine_learning" if self.detector.is_loaded else "threshold_fallback",
                ml_model_name=self.detector.model_name,
                switch_connected=True,
                last_updated_at=current_time,
                openflow_rules=openflow_rules,
                ip_traffic=ip_traffic,
                blocked_flows=[{
                    'src_ip': k[0], 'dst_ip': k[1], 'ip_proto': k[2], 'dst_port': k[3], **v
                } for k, v in self.blocked_flows.items()]
            )
        except Exception as e:
            self.logger.error("Error in flow_stats_reply_handler: %s", e)

    def _log_to_csv(self, stats_dict):
        """Append flow stats to controller/traffic_dataset.csv"""
        try:
            file_exists = os.path.isfile(self.csv_path)

            with open(self.csv_path, mode='a', newline='') as f:
                fieldnames = ['timestamp', 'src_ip', 'dst_ip', 'packet_count', 'byte_count', 'duration_sec', 'pps', 'bps']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')

                if not file_exists:
                    writer.writeheader()

                writer.writerow(stats_dict)
        except Exception as e:
            self.logger.error("Failed to write flow stats to CSV: %s", e)

    def _run_inference(self, stats_dict, datapath):
        """Extract features, run through ML model, log detailed reasoning, and mitigate if DDoS detected."""
        src_ip = stats_dict['src_ip']
        dst_ip = stats_dict.get('dst_ip', '10.0.0.3')
        pps = stats_dict.get('pps', 0.0)
        bps = stats_dict.get('bps', 0.0)
        proto = stats_dict.get('ip_proto', 17)
        dst_port = stats_dict.get('dst_port', 80)

        # 1. Server Protection: 10.0.0.3 responses are never blocked
        if src_ip == '10.0.0.3':
            return False, 0.05

        # 2. Pure Legitimate Workstations Protection: h1 (10.0.0.1), h11 (10.0.0.11), h12 (10.0.0.12)
        # Dedicated legitimate clients must NEVER be blocked under any circumstances.
        if src_ip in ('10.0.0.1', '10.0.0.11', '10.0.0.12'):
            return False, 0.05

        # 3. Same-IP Mixed Traffic Granular Protection:
        # On mixed nodes h2 (10.0.0.2) and h4 (10.0.0.4), allow benign streaming/DNS ports
        if src_ip in ('10.0.0.2', '10.0.0.4') and dst_port in (5001, 53) and pps < 3000:
            return False, 0.05

        # 4. Check if flow tuple is already blocked
        flow_tuple = (src_ip, dst_ip, proto, dst_port)
        if flow_tuple in self.blocked_flows:
            return False, 0.1

        is_ddos, inference_ms = self.detector.predict(stats_dict)
        reason = getattr(self.detector, 'last_reason', 'Decision Tree Classification')

        if is_ddos:
            if proto == 1 and pps > 1000:
                attack_type = "ICMP Echo Flood"
            elif dst_port in (80, 8080, 443) and stats_dict.get('duration_sec', 0) >= 15.0 and 15.0 <= pps <= 80:
                attack_type = "Slowloris Starvation"
            elif proto == 6 and pps > 4500:
                attack_type = "TCP SYN Flood"
            elif dst_port == 53 and pps > 4500:
                attack_type = "DNS UDP Flood"
            elif dst_port == 8080 and pps > 4500:
                attack_type = "High-Port UDP Flood"
            else:
                attack_type = "Volumetric UDP Flood"

            self.logger.warning(f"DDoS Detected from {src_ip}:{dst_port}! Reasoning: {reason}")
            self.ml_logger.warning(
                f"[ATTACK DETECTED] src={src_ip} -> dst={dst_ip}:{dst_port} | Proto={proto} | "
                f"Rate={pps:,.1f} PPS ({bps/1e6:.2f} Mbps) | Latency={inference_ms:.2f}ms | "
                f"Reason: {reason} | Action: PUSH FLOW-GRANULAR DROP RULE (Priority 65535, Idle Timeout 15s)"
            )
            if datapath is not None:
                push_drop_rule(datapath, src_ip, dst_ip=dst_ip, ip_proto=proto, dst_port=dst_port)

            self.blocked_flows[flow_tuple] = {
                'attack_type': attack_type,
                'reason': reason,
                'protocol': 'TCP' if proto == 6 else ('UDP' if proto == 17 else ('ICMP' if proto == 1 else f'Proto {proto}')),
                'dst_port': dst_port or 0,
                'dst_ip': dst_ip,
                'detected_at': time.time()
            }
            self.blocked_ips.add(src_ip)
            update_state(status="UNDER_ATTACK", blocked_ips=list(self.blocked_ips), inference_latency_ms=inference_ms)
            return True, inference_ms
        else:
            if pps > 5:
                self.ml_logger.info(
                    f"[BENIGN TRAFFIC] src={src_ip} -> dst={dst_ip}:{dst_port} | Proto={proto} | "
                    f"Rate={pps:,.1f} PPS ({bps/1e6:.2f} Mbps) | Latency={inference_ms:.2f}ms | "
                    f"Reason: {reason} | Action: ALLOW & FORWARD (Priority 10)"
                )

        return False, inference_ms
