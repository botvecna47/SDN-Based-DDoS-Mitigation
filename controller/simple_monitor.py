import os
import sys
import time
import csv
import logging
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet, ipv4, ether_types

# Add backend_api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_api'))
try:
    from state_manager import initialize_state, update_state
except ImportError:
    # Dummy fallback if not present
    def initialize_state(): pass
    def update_state(**kwargs): pass

from mitigation import push_drop_rule
from inference_loader import DDoSDetector

class SimpleMonitor13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleMonitor13, self).__init__(*args, **kwargs)
        self.mac_to_port = {
            1: {
                '00:00:00:00:00:01': 1,
                '00:00:00:00:00:02': 2,
                '00:00:00:00:00:03': 3,
            }
        }
        self.datapaths = {}
        self.start_time = time.time()
        self.blocked_ips = set()
        self.flow_history = {} # dict of (datapath.id, src_ip, dst_ip) -> (prev_pkt, prev_byte, prev_time)

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
                update_state(switch_connected=True, last_updated_at=time.time())
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info('Unregistering datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]
                self.blocked_ips.clear()
                update_state(
                    switch_connected=bool(self.datapaths),
                    blocked_ips=list(self.blocked_ips),
                    status="NORMAL",
                    current_pps=0,
                    dropped_pps=0,
                    active_flows=0,
                    openflow_rules=[],
                    last_updated_at=time.time(),
                )

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _flow_removed_handler(self, ev):
        """Keep the dashboard block list in sync with switch idle timeouts."""
        src_ip = ev.msg.match['ipv4_src'] if 'ipv4_src' in ev.msg.match else None
        if src_ip and src_ip in self.blocked_ips:
            self.blocked_ips.discard(src_ip)
            update_state(blocked_ips=list(self.blocked_ips), last_updated_at=time.time())
            self.logger.info('DROP rule expired for %s; removed from block list.', src_ip)

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
        """Standard L2 learning: learn MAC addresses, install flow entries, forward packets"""
        # If you hit this you might want to add mac learning
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            # check IP Protocol and create a match for IP
            if eth.ethertype == ether_types.ETH_TYPE_IP:
                ip = pkt.get_protocol(ipv4.ipv4)
                if ip:
                    srcip = ip.src
                    dstip = ip.dst
                    match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                            ipv4_src=srcip, ipv4_dst=dstip)

                    # verify if we have a valid buffer_id, if yes avoid to send both
                    # flow_mod & packet_out
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
        """Process flow statistics from the switch, calculate rates, and run ML detection."""
        try:
            body = ev.msg.body
            datapath = ev.msg.datapath

            current_time = time.time()
            controller_uptime_sec = current_time - self.start_time

            total_pps = 0.0
            dropped_pps = 0.0
            attack_detected_this_cycle = False
            latest_inference_ms = 3.1
            openflow_rules = []

            for stat in body:
                priority = int(stat.priority)
                match = {
                    key: stat.match[key]
                    for key in ('in_port', 'eth_src', 'eth_dst', 'ipv4_src', 'ipv4_dst', 'eth_type', 'ip_proto', 'tcp_src', 'tcp_dst', 'udp_src', 'udp_dst')
                    if key in stat.match
                }
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
                    'packets': int(stat.packet_count),
                    'bytes': int(stat.byte_count),
                })

            for stat in body:
                # We are only interested in IPv4 flows
                if 'ipv4_src' not in stat.match:
                    continue

                src_ip = stat.match['ipv4_src']
                dst_ip = stat.match['ipv4_dst'] if 'ipv4_dst' in stat.match else None
                ip_proto = stat.match.get('ip_proto', 17)
                src_port = stat.match.get('tcp_src', stat.match.get('udp_src', 0))
                dst_port = stat.match.get('tcp_dst', stat.match.get('udp_dst', 0))

                packet_count = stat.packet_count
                byte_count = stat.byte_count
                duration_sec = stat.duration_sec

                # Key for flow history
                flow_key = (datapath.id, src_ip, dst_ip or '*')

                pps = 0.0
                bps = 0.0

                if flow_key in self.flow_history:
                    prev_pkt, prev_byte, prev_time = self.flow_history[flow_key]
                    time_delta = current_time - prev_time
                    if time_delta > 0:
                        pkt_delta = packet_count - prev_pkt
                        byte_delta = byte_count - prev_byte
                        if pkt_delta > 0:
                            pps = pkt_delta / time_delta
                        if byte_delta > 0:
                            bps = (byte_delta * 8) / time_delta

                total_pps += pps
                if dst_ip is None:
                    # DROP rules match only source IP, so retain their rate and
                    # rebuild the block list if Ryu restarted while OVS stayed up.
                    if stat.priority == 65535 and src_ip != '10.0.0.3':
                        self.blocked_ips.add(src_ip)
                    self.blocked_ips.discard('10.0.0.3')
                    if src_ip in self.blocked_ips:
                        dropped_pps += pps
                    self.flow_history[flow_key] = (packet_count, byte_count, current_time)
                    continue

                # Store history
                self.flow_history[flow_key] = (packet_count, byte_count, current_time)

                stats_dict = {
                    'timestamp': current_time,
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'src_port': src_port,
                    'dst_port': dst_port,
                    'ip_proto': ip_proto,
                    'packet_count': packet_count,
                    'byte_count': byte_count,
                    'duration_sec': duration_sec,
                    'pps': pps,
                    'bps': bps
                }

                try:
                    self._log_to_csv(stats_dict)
                except Exception as e:
                    self.logger.error("CSV logging error: %s", e)

                detected, inf_ms = self._run_inference(stats_dict, datapath)
                if detected:
                    attack_detected_this_cycle = True
                latest_inference_ms = inf_ms

            # Auto-recover status if traffic drops
            # UNDER_ATTACK if attack detected this cycle OR packets are actively being dropped OR
            # blocked IPs exist and traffic is still arriving.
            if attack_detected_this_cycle:
                current_status = "UNDER_ATTACK"
            elif dropped_pps > 0:
                current_status = "UNDER_ATTACK"
            elif len(self.blocked_ips) > 0 and total_pps > 100:
                current_status = "UNDER_ATTACK"
            elif len(self.blocked_ips) > 0:
                current_status = "UNDER_ATTACK"
            else:
                current_status = "NORMAL"

            # Update shared state
            update_state(
                controller_uptime_sec=controller_uptime_sec,
                blocked_ips=list(self.blocked_ips),
                current_pps=total_pps,
                active_flows=len(body),
                status=current_status,
                inference_latency_ms=latest_inference_ms,
                dropped_pps=dropped_pps,
                detection_mode="machine_learning" if self.detector.is_loaded else "threshold_fallback",
                ml_model_name=self.detector.model_name,
                switch_connected=True,
                last_updated_at=current_time,
                openflow_rules=openflow_rules,
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

        # 1. Server Whitelist: Server (10.0.0.3) responses must never be blocked
        if src_ip == '10.0.0.3':
            return False, 0.05

        # 2. Already blocked IPs
        if src_ip in self.blocked_ips:
            return False, 0.1

        is_ddos, inference_ms = self.detector.predict(stats_dict)
        reason = getattr(self.detector, 'last_reason', 'Decision Tree Classification')

        if is_ddos:
            self.logger.warning(f"DDoS Detected from {src_ip}! Reasoning: {reason}")
            self.ml_logger.warning(
                f"[ATTACK DETECTED] src={src_ip} -> dst={dst_ip}:{dst_port} | Proto={proto} | "
                f"Rate={pps:,.1f} PPS ({bps/1e6:.2f} Mbps) | Latency={inference_ms:.2f}ms | "
                f"Reason: {reason} | Action: PUSH DROP RULE (Priority 65535, Idle Timeout 300s)"
            )
            push_drop_rule(datapath, src_ip)
            self.blocked_ips.add(src_ip)
            # Immediately write UNDER_ATTACK status so Flask picks it up on next poll
            # without waiting for the next 1.5s flow stats cycle
            update_state(status="UNDER_ATTACK", blocked_ips=list(self.blocked_ips), inference_latency_ms=inference_ms)
            return True, inference_ms
        else:
            # Log verified legitimate traffic passing through
            if pps > 5:
                self.ml_logger.info(
                    f"[BENIGN TRAFFIC] src={src_ip} -> dst={dst_ip}:{dst_port} | Proto={proto} | "
                    f"Rate={pps:,.1f} PPS ({bps/1e6:.2f} Mbps) | Latency={inference_ms:.2f}ms | "
                    f"Reason: {reason} | Action: ALLOW & FORWARD (Priority 10)"
                )

        return False, inference_ms

