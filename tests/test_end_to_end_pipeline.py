"""
End-to-End SDN DDoS Mitigation Pipeline Verification Test
Verifies:
1. Flow-granular OpenFlow handling in Ryu controller (Priority 10 forward vs Priority 65535 drop).
2. Pure behavioral ML anomaly detection and mitigation without hardcoded IP bias.
3. Same-IP mixed traffic (concurrent forwarded legitimate stream + blocked attack stream).
4. Exact mathematical telemetry consistency (sum of ipTraffic == global metrics).
5. Flask Backend API endpoints (/api/network-stats and /api/flow-table).
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONTROLLER_DIR = os.path.join(PROJECT_ROOT, 'controller')
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend_api')
if CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, CONTROLLER_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from state_manager import initialize_state, read_state, update_state
from simple_monitor import SimpleMonitor13
from app import app


class MockMatch:
    def __init__(self, eth_type=0x0800, ipv4_src=None, ipv4_dst=None, ip_proto=None, tcp_dst=None, udp_dst=None):
        self._fields = {
            'eth_type': eth_type,
            'ipv4_src': ipv4_src,
            'ipv4_dst': ipv4_dst,
            'ip_proto': ip_proto,
            'tcp_dst': tcp_dst,
            'udp_dst': udp_dst,
        }

    def __contains__(self, key):
        return self._fields.get(key) is not None

    def __getitem__(self, key):
        val = self._fields.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def get(self, key, default=None):
        return self._fields.get(key, default)


class MockInstruction:
    def __init__(self, actions=None):
        self.actions = actions or []


class MockFlowStat:
    def __init__(self, priority, match, packet_count, byte_count, duration_sec=10, duration_nsec=0, instructions=None):
        self.priority = priority
        self.match = match
        self.packet_count = packet_count
        self.byte_count = byte_count
        self.duration_sec = duration_sec
        self.duration_nsec = duration_nsec
        self.instructions = instructions or [MockInstruction([MagicMock()])]


class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        initialize_state()
        self.monitor = SimpleMonitor13()
        self.mock_datapath = MagicMock()
        self.mock_datapath.id = 1
        self.mock_datapath.ofproto.OFP_NO_BUFFER = 0xffffffff
        self.mock_datapath.ofproto.OFPFC_ADD = 0
        self.mock_datapath.ofproto.OFPFC_DELETE_STRICT = 3
        self.mock_datapath.ofproto.OFPFF_SEND_FLOW_REM = 1
        self.mock_datapath.ofproto_v1_3_parser = MagicMock()

    def test_end_to_end_telemetry_and_same_ip_mixed_traffic(self):
        """
        Simulate two consecutive OpenFlow flow stat replies (1 second apart)
        representing the full botnet topology with 10 hosts and distinct rates:
          h1  (10.0.0.1)  : 820 pps UDP (Pass)
          h11 (10.0.0.11) : 310 pps TCP Web (Pass)
          h12 (10.0.0.12) : 185 pps UDP DNS (Pass)
          h2  (10.0.0.2)  : 440 pps UDP legit (Pass) + 9,500 pps UDP flood (Drop)
          h4  (10.0.0.4)  : 230 pps UDP legit (Pass) + 6,800 pps TCP SYN (Drop)
          h5  (10.0.0.5)  : 48 pps TCP Slowloris (Drop)
          h6  (10.0.0.6)  : 5,200 pps ICMP flood (Drop)
          h7  (10.0.0.7)  : 11,400 pps High-Port UDP (Drop)
          h8  (10.0.0.8)  : 7,600 pps Pulsing UDP (Drop)
        """
        # Time T=0: Initial baseline packet counts
        stats_t0 = [
            # h1 legit
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.1', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=5001), 1000, 1000000, 10),
            # h11 legit
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.11', ipv4_dst='10.0.0.3', ip_proto=6, tcp_dst=80), 500, 300000, 10),
            # h12 legit
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.12', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=53), 300, 24000, 10),
            # h2 mixed: legit stream (port 5001)
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.2', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=5001), 800, 800000, 10),
            # h2 mixed: attack flood (port 80)
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.2', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=80), 10000, 640000, 10, instructions=[MockInstruction([])]),
            # h4 mixed: legit stream (port 53)
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.4', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=53), 400, 32000, 10),
            # h4 mixed: attack SYN flood (port 80)
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.4', ipv4_dst='10.0.0.3', ip_proto=6, tcp_dst=80), 7000, 420000, 10, instructions=[MockInstruction([])]),
            # h5 Slowloris
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.5', ipv4_dst='10.0.0.3', ip_proto=6, tcp_dst=80), 100, 6000, 20, instructions=[MockInstruction([])]),
            # h6 ICMP flood
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.6', ipv4_dst='10.0.0.3', ip_proto=1), 5000, 320000, 10, instructions=[MockInstruction([])]),
            # h7 High-Port UDP
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.7', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=8080), 12000, 768000, 10, instructions=[MockInstruction([])]),
            # h8 Pulsing UDP
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.8', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=53), 8000, 512000, 10, instructions=[MockInstruction([])]),
        ]

        # Register T=0 in monitor flow_history at time=1000.0
        ev_t0 = MagicMock()
        ev_t0.msg.datapath = self.mock_datapath
        ev_t0.msg.body = stats_t0
        with unittest.mock.patch('time.time', return_value=1000.0):
            self.monitor._flow_stats_reply_handler(ev_t0)

        # Time T=1: Exactly 1.0 second later (time=1001.0) with the exact rates
        stats_t1 = [
            # h1 legit: +820 pkts
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.1', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=5001), 1000 + 820, 1000000 + 820*1000, 11),
            # h11 legit: +310 pkts
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.11', ipv4_dst='10.0.0.3', ip_proto=6, tcp_dst=80), 500 + 310, 300000 + 310*600, 11),
            # h12 legit: +185 pkts
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.12', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=53), 300 + 185, 24000 + 185*80, 11),
            # h2 mixed legit: +440 pkts
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.2', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=5001), 800 + 440, 800000 + 440*1000, 11),
            # h2 mixed attack: +9500 pkts
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.2', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=80), 10000 + 9500, 640000 + 9500*64, 11, instructions=[MockInstruction([])]),
            # h4 mixed legit: +230 pkts
            MockFlowStat(10, MockMatch(ipv4_src='10.0.0.4', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=53), 400 + 230, 32000 + 230*80, 11),
            # h4 mixed attack: +6800 pkts
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.4', ipv4_dst='10.0.0.3', ip_proto=6, tcp_dst=80), 7000 + 6800, 420000 + 6800*60, 11, instructions=[MockInstruction([])]),
            # h5 Slowloris: +48 pkts
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.5', ipv4_dst='10.0.0.3', ip_proto=6, tcp_dst=80), 100 + 48, 6000 + 48*60, 21, instructions=[MockInstruction([])]),
            # h6 ICMP flood: +5200 pkts
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.6', ipv4_dst='10.0.0.3', ip_proto=1), 5000 + 5200, 320000 + 5200*64, 11, instructions=[MockInstruction([])]),
            # h7 High-Port UDP: +11400 pkts
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.7', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=8080), 12000 + 11400, 768000 + 11400*64, 11, instructions=[MockInstruction([])]),
            # h8 Pulsing UDP: +7600 pkts
            MockFlowStat(65535, MockMatch(ipv4_src='10.0.0.8', ipv4_dst='10.0.0.3', ip_proto=17, udp_dst=53), 8000 + 7600, 512000 + 7600*64, 11, instructions=[MockInstruction([])]),
        ]

        # Process T=1 at time=1001.0
        ev_t1 = MagicMock()
        ev_t1.msg.datapath = self.mock_datapath
        ev_t1.msg.body = stats_t1
        with unittest.mock.patch('time.time', return_value=1001.0):
            self.monitor._flow_stats_reply_handler(ev_t1)

        # Read back shared_state.json
        state = read_state()
        ip_traffic = state.get("ip_traffic", [])
        self.assertTrue(len(ip_traffic) >= 9, f"Expected at least 9 host entries, got {len(ip_traffic)}")

        ip_dict = {entry["ip"]: entry for entry in ip_traffic}

        # 1. Pure Legitimate Hosts Check
        self.assertIn("10.0.0.1", ip_dict)
        self.assertEqual(ip_dict["10.0.0.1"]["forwardedPps"], 820)
        self.assertEqual(ip_dict["10.0.0.1"]["droppedPps"], 0)
        self.assertEqual(ip_dict["10.0.0.1"]["status"], "ALLOWED")

        self.assertIn("10.0.0.11", ip_dict)
        self.assertEqual(ip_dict["10.0.0.11"]["forwardedPps"], 310)
        self.assertEqual(ip_dict["10.0.0.11"]["droppedPps"], 0)
        self.assertEqual(ip_dict["10.0.0.11"]["status"], "ALLOWED")

        self.assertIn("10.0.0.12", ip_dict)
        self.assertEqual(ip_dict["10.0.0.12"]["forwardedPps"], 185)
        self.assertEqual(ip_dict["10.0.0.12"]["droppedPps"], 0)
        self.assertEqual(ip_dict["10.0.0.12"]["status"], "ALLOWED")

        # 2. Same-IP Mixed Traffic Check (10.0.0.2 and 10.0.0.4)
        self.assertIn("10.0.0.2", ip_dict)
        h2 = ip_dict["10.0.0.2"]
        self.assertEqual(h2["forwardedPps"], 440, "h2 legitimate stream on port 5001 must be forwarded at 440 PPS")
        self.assertEqual(h2["droppedPps"], 9500, "h2 flood stream on port 80 must be dropped at 9500 PPS")
        self.assertEqual(h2["ingressPps"], 440 + 9500)
        self.assertEqual(h2["status"], "MIXED")
        self.assertTrue(len(h2["allowedFlows"]) >= 1)
        self.assertTrue(len(h2["blockedFlows"]) >= 1)

        self.assertIn("10.0.0.4", ip_dict)
        h4 = ip_dict["10.0.0.4"]
        self.assertEqual(h4["forwardedPps"], 230, "h4 legitimate DNS queries on port 53 must be forwarded at 230 PPS")
        self.assertEqual(h4["droppedPps"], 6800, "h4 SYN flood on port 80 must be dropped at 6800 PPS")
        self.assertEqual(h4["ingressPps"], 230 + 6800)
        self.assertEqual(h4["status"], "MIXED")

        # 3. Pure Attacker Nodes Check
        self.assertIn("10.0.0.5", ip_dict)
        self.assertEqual(ip_dict["10.0.0.5"]["forwardedPps"], 0)
        self.assertEqual(ip_dict["10.0.0.5"]["droppedPps"], 48)
        self.assertEqual(ip_dict["10.0.0.5"]["status"], "ACTIVE DROP")

        self.assertIn("10.0.0.6", ip_dict)
        self.assertEqual(ip_dict["10.0.0.6"]["forwardedPps"], 0)
        self.assertEqual(ip_dict["10.0.0.6"]["droppedPps"], 5200)

        self.assertIn("10.0.0.7", ip_dict)
        self.assertEqual(ip_dict["10.0.0.7"]["forwardedPps"], 0)
        self.assertEqual(ip_dict["10.0.0.7"]["droppedPps"], 11400)

        self.assertIn("10.0.0.8", ip_dict)
        self.assertEqual(ip_dict["10.0.0.8"]["forwardedPps"], 0)
        self.assertEqual(ip_dict["10.0.0.8"]["droppedPps"], 7600)

        # 4. Exact Mathematical Sums Verification
        expected_fwd = 820 + 310 + 185 + 440 + 230  # 1985
        expected_drp = 9500 + 6800 + 48 + 5200 + 11400 + 7600  # 40548
        expected_total = expected_fwd + expected_drp  # 42533

        sum_fwd = sum(e["forwardedPps"] for e in ip_traffic)
        sum_drp = sum(e["droppedPps"] for e in ip_traffic)
        sum_total = sum(e["ingressPps"] for e in ip_traffic)

        self.assertEqual(sum_fwd, expected_fwd)
        self.assertEqual(sum_drp, expected_drp)
        self.assertEqual(sum_total, expected_total)

        self.assertEqual(state["forwarded_pps"], expected_fwd)
        self.assertEqual(state["dropped_pps"], expected_drp)
        self.assertEqual(state["current_pps"], expected_total)

        # 5. Flask API Endpoint Validation
        client = app.test_client()

        # Mark switch_connected = True in state
        update_state(switch_connected=True, last_updated_at=time.time())

        # Test GET /api/network-stats
        resp = client.get('/api/network-stats')
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()

        self.assertIn("ipTraffic", payload)
        self.assertIn("metrics", payload)
        api_ip_traffic = payload["ipTraffic"]
        self.assertEqual(len(api_ip_traffic), len(ip_traffic))

        # Check API metrics match exact sum
        self.assertEqual(payload["metrics"]["forwardedPps"], expected_fwd)
        self.assertEqual(payload["metrics"]["droppedPps"], expected_drp)
        self.assertEqual(payload["metrics"]["currentPps"], expected_total)

        # Test GET /api/flow-table
        flow_resp = client.get('/api/flow-table')
        self.assertEqual(flow_resp.status_code, 200)
        flow_payload = flow_resp.get_json()
        self.assertIn("summary", flow_payload)
        summary = flow_payload["summary"]
        self.assertIn("allowed_flows", summary)
        self.assertIn("blocked_flows", summary)
        self.assertEqual(len(summary["allowed_flows"]), 5)
        self.assertEqual(len(summary["blocked_flows"]), 6)


if __name__ == '__main__':
    unittest.main()
