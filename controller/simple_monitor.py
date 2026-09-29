import os
import sys
import time
import csv
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
        self.mac_to_port = {}
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
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info('Unregistering datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Install a table-miss flow entry: priority=0, match=everything, action=CONTROLLER"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

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
                srcip = ip.src
                dstip = ip.dst
                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                        ipv4_src=srcip, ipv4_dst=dstip,
                                        in_port=in_port, eth_dst=dst, eth_src=src)
                
                # verify if we have a valid buffer_id, if yes avoid to send both
                # flow_mod & packet_out
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                    return
                else:
                    self.add_flow(datapath, 1, match, actions)
            else:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
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
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(1.5)

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
        body = ev.msg.body
        datapath = ev.msg.datapath
        
        current_time = time.time()
        controller_uptime_sec = current_time - self.start_time
        
        total_pps = 0.0
        
        for stat in body:
            # We are only interested in IPv4 flows
            if 'ipv4_src' not in stat.match or 'ipv4_dst' not in stat.match:
                continue
                
            src_ip = stat.match['ipv4_src']
            dst_ip = stat.match['ipv4_dst']
            
            packet_count = stat.packet_count
            byte_count = stat.byte_count
            duration_sec = stat.duration_sec
            
            # Key for flow history
            flow_key = (datapath.id, src_ip, dst_ip)
            
            pps = 0.0
            bps = 0.0
            
            if flow_key in self.flow_history:
                prev_pkt, prev_byte, prev_time = self.flow_history[flow_key]
                time_delta = current_time - prev_time
                if time_delta > 0:
                    pps = (packet_count - prev_pkt) / time_delta
                    # calculate bps, byte_count is in bytes, so * 8 for bits
                    bps = ((byte_count - prev_byte) * 8) / time_delta
            
            total_pps += pps
            
            # Store history
            self.flow_history[flow_key] = (packet_count, byte_count, current_time)
            
            stats_dict = {
                'timestamp': current_time,
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'packet_count': packet_count,
                'byte_count': byte_count,
                'duration_sec': duration_sec,
                'pps': pps,
                'bps': bps
            }
            
            self._log_to_csv(stats_dict)
            self._run_inference(stats_dict, datapath)
            
        # Update shared state
        update_state(
            controller_uptime_sec=controller_uptime_sec,
            blocked_ips=list(self.blocked_ips),
            current_pps=total_pps,
            active_flows=len(body)
        )

    def _log_to_csv(self, stats_dict):
        """Append flow stats to controller/traffic_dataset.csv"""
        file_exists = os.path.isfile(self.csv_path)
        
        with open(self.csv_path, mode='a', newline='') as f:
            fieldnames = ['timestamp', 'src_ip', 'dst_ip', 'packet_count', 'byte_count', 'duration_sec', 'pps', 'bps']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(stats_dict)

    def _run_inference(self, stats_dict, datapath):
        """Extract features, run through ML model, and mitigate if DDoS detected."""
        src_ip = stats_dict['src_ip']
        if src_ip in self.blocked_ips:
            return  # Already blocked

        is_ddos, inference_ms = self.detector.predict(
            pps=stats_dict['pps'],
            bps=stats_dict['bps'],
            duration_sec=stats_dict['duration_sec'],
            packet_count=stats_dict['packet_count']
        )

        # Push inference latency to shared state so React dashboard shows real value
        update_state(inference_latency_ms=inference_ms)

        if is_ddos:
            self.logger.warning(f"DDoS Detected from {src_ip}! Pushing drop rule...")
            push_drop_rule(datapath, src_ip)
            self.blocked_ips.add(src_ip)
            update_state(status="UNDER_ATTACK", blocked_ips=list(self.blocked_ips))

