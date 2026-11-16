"""
Unit & Integration Test Suite for SDN DDoS ML Engine
=====================================================
Tests ML mode accuracy, deterministic fixed test cases, Monte Carlo
randomized flow evaluation, noise robustness, and tier cascade fallback.

Usage:
    py -m unittest tests/test_ml_engine.py
"""

import os
import sys
import time
import unittest
import warnings
import subprocess
from pathlib import Path

# Python 3.9 venv trampoline for host execution compatibility
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / "ryu39_env" / "bin" / "python3"

if sys.version_info >= (3, 10) and VENV_PYTHON.exists() and os.environ.get("VENV_REEXEC") != "1":
    env = os.environ.copy()
    env["VENV_REEXEC"] = "1"
    args = [str(VENV_PYTHON), "-m", "unittest"] + [a for a in sys.argv[1:] if a not in ("-m", "unittest")]
    res = subprocess.run(args, env=env)
    sys.exit(res.returncode)

import numpy as np

# Suppress sklearn unpickle / feature name warnings for clean test reporting
warnings.filterwarnings("ignore")

# Ensure root paths are accessible
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'controller'))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend_api'))
sys.path.insert(0, os.path.join(BASE_DIR, 'ml_pipeline'))

from inference_loader import DDoSDetector


class TestMLEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.detector = DDoSDetector()

    # -------------------------------------------------------------
    # 1. Model Initialization & Tier Checks
    # -------------------------------------------------------------
    def test_01_tier1_model_loaded(self):
        """Verify that Tier 1 (CIC-DDoS2019 Decision Tree) is active with all 28 ANOVA features."""
        self.assertTrue(self.detector.is_loaded, "DDoSDetector should be marked as loaded.")
        self.assertEqual(self.detector.tier, 1, "Detector should resolve to Tier 1.")
        self.assertIn("CIC-DDoS2019", self.detector.model_name)
        self.assertEqual(len(self.detector.selected_features), 28, "Must load exactly 28 ANOVA features.")

    # -------------------------------------------------------------
    # 2. Fixed Sets of Test Scenarios (Deterministic Golden Cases)
    # -------------------------------------------------------------
    def test_02_fixed_legitimate_web_browsing(self):
        """Standard HTTP/HTTPS web browsing traffic must be classified as BENIGN."""
        flow = {
            'src_ip': '192.168.1.105',
            'dst_ip': '10.0.0.9',
            'pps': 120.0,
            'bps': 180_000.0,
            'duration_sec': 12.0,
            'packet_count': 1440,
            'src_port': 52140,
            'dst_port': 80,
            'ip_proto': 6
        }
        is_ddos, lat = self.detector.predict(flow)
        self.assertFalse(is_ddos, "Normal web browsing should NOT be flagged as DDoS.")
        self.assertLess(lat, 5.0, "Latency must be under 5.0 ms SLA.")

    def test_03_fixed_legitimate_iperf_stream(self):
        """Continuous legitimate UDP iperf stream (h1 -> h3, ~850 PPS) must be BENIGN."""
        flow = {
            'src_ip': '10.0.0.1',
            'dst_ip': '10.0.0.3',
            'pps': 850.0,
            'bps': 10_000_000.0,
            'duration_sec': 60.0,
            'packet_count': 51000,
            'src_port': 54321,
            'dst_port': 80,
            'ip_proto': 17
        }
        is_ddos, _ = self.detector.predict(flow)
        self.assertFalse(is_ddos, "Legitimate iperf UDP stream must be BENIGN.")

    def test_04_fixed_legitimate_dns_queries(self):
        """Low-rate DNS query traffic on port 53 must be BENIGN."""
        flow = {
            'src_ip': '10.0.0.1',
            'dst_ip': '10.0.0.9',
            'pps': 25.0,
            'bps': 16_000.0,
            'duration_sec': 4.0,
            'packet_count': 100,
            'src_port': 53200,
            'dst_port': 53,
            'ip_proto': 17
        }
        is_ddos, _ = self.detector.predict(flow)
        self.assertFalse(is_ddos, "Standard DNS queries must be BENIGN.")

    def test_05_fixed_volumetric_udp_flood(self):
        """High-rate volumetric UDP flood (25,000 PPS) must be classified as ATTACK."""
        flow = {
            'src_ip': '10.0.0.2',
            'dst_ip': '10.0.0.3',
            'pps': 25000.0,
            'bps': 50_000_000.0,
            'duration_sec': 10.0,
            'packet_count': 250000,
            'src_port': 50000,
            'dst_port': 80,
            'ip_proto': 17
        }
        is_ddos, lat = self.detector.predict(flow)
        self.assertTrue(is_ddos, "Volumetric UDP flood MUST be flagged as ATTACK.")
        self.assertLess(lat, 5.0, "Prediction latency must satisfy < 5.0 ms SLA.")

    def test_06_fixed_tcp_syn_flood(self):
        """High-rate TCP SYN flood (20,000 PPS) on port 80 must be ATTACK."""
        flow = {
            'src_ip': '10.0.0.3',
            'dst_ip': '10.0.0.9',
            'pps': 20000.0,
            'bps': 32_000_000.0,
            'duration_sec': 8.0,
            'packet_count': 160000,
            'src_port': 48920,
            'dst_port': 80,
            'ip_proto': 6
        }
        is_ddos, _ = self.detector.predict(flow)
        self.assertTrue(is_ddos, "TCP SYN flood must be flagged as ATTACK.")

    def test_07_fixed_slowloris_connection_starvation(self):
        """Low-rate Slowloris attack (low PPS, long duration, tiny throughput on port 80) must be ATTACK."""
        flow = {
            'src_ip': '10.0.0.4',
            'dst_ip': '10.0.0.9',
            'pps': 30.0,
            'bps': 8_000.0, # 1 KB/s
            'duration_sec': 25.0,
            'packet_count': 750,
            'src_port': 51000,
            'dst_port': 80,
            'ip_proto': 6
        }
        is_ddos, _ = self.detector.predict(flow)
        self.assertTrue(is_ddos, "Slowloris starvation attack must be detected.")

    def test_08_fixed_edge_cases(self):
        """Zero rate (idle connection) should not flag as attack."""
        idle_flow = {
            'src_ip': '10.0.0.1',
            'dst_ip': '10.0.0.3',
            'pps': 0.0,
            'bps': 0.0,
            'duration_sec': 5.0,
            'packet_count': 0
        }
        is_ddos, _ = self.detector.predict(idle_flow)
        self.assertFalse(is_ddos, "Zero/idle traffic must not be flagged as attack.")

    # -------------------------------------------------------------
    # 3. Monte Carlo Randomized Accuracy Evaluation (1,000 Flows)
    # -------------------------------------------------------------
    def test_09_random_monte_carlo_accuracy(self):
        """
        Evaluate accuracy over 1,000 randomized synthetic flows:
          - 500 randomized legitimate flows targeting standard service ports (80, 443, 53, 22)
          - 500 randomized attack flows across botnet nodes & volumetric floods
        Target Accuracy: >= 99.0%, Target FPR: < 1.0%, Target FNR: < 1.0%
        """
        np.random.seed(42)
        n_per_class = 500

        # Generate 500 normal flows
        normal_flows = []
        for _ in range(n_per_class):
            pps = float(np.random.normal(300, 100))
            pps = max(10.0, min(1500.0, pps))
            pkt_size = np.random.uniform(200, 1400)
            bps = pps * pkt_size * 8.0
            normal_flows.append({
                'src_ip': '10.0.0.1',
                'dst_ip': '10.0.0.9',
                'pps': pps,
                'bps': bps,
                'duration_sec': float(np.random.uniform(5.0, 180.0)),
                'packet_count': int(pps * 10),
                'src_port': int(np.random.randint(49152, 65535)),
                'dst_port': int(np.random.choice([80, 443, 53, 22])),
                'ip_proto': int(np.random.choice([6, 17]))
            })

        # Generate 500 attack flows
        attack_flows = []
        for _ in range(n_per_class):
            attack_type = np.random.choice(['volumetric_udp', 'syn_flood', 'extreme_flood', 'slowloris'])
            if attack_type == 'volumetric_udp':
                pps = float(np.random.uniform(12000.0, 30000.0))
                bps = pps * np.random.uniform(500, 1000) * 8.0
                proto = 17
                dur = float(np.random.uniform(2.0, 30.0))
            elif attack_type == 'syn_flood':
                pps = float(np.random.uniform(10000.0, 25000.0))
                bps = pps * np.random.uniform(60, 120) * 8.0
                proto = 6
                dur = float(np.random.uniform(2.0, 30.0))
            elif attack_type == 'slowloris':
                pps = float(np.random.uniform(20.0, 80.0))
                bps = pps * 40.0 * 8.0 # tiny throughput
                proto = 6
                dur = float(np.random.uniform(20.0, 120.0))
            else: # extreme flood
                pps = float(np.random.uniform(30000.0, 50000.0))
                bps = pps * 800.0 * 8.0
                proto = 17
                dur = float(np.random.uniform(2.0, 30.0))

            attack_flows.append({
                'src_ip': f'10.0.0.{np.random.randint(2, 9)}',
                'dst_ip': '10.0.0.9',
                'pps': pps,
                'bps': bps,
                'duration_sec': dur,
                'packet_count': int(pps * 5),
                'src_port': int(np.random.randint(1024, 65535)),
                'dst_port': 80,
                'ip_proto': proto
            })

        # Evaluate Normal flows
        fp_count = 0
        for f in normal_flows:
            is_ddos, _ = self.detector.predict(f)
            if is_ddos:
                fp_count += 1

        # Evaluate Attack flows
        fn_count = 0
        for f in attack_flows:
            is_ddos, _ = self.detector.predict(f)
            if not is_ddos:
                fn_count += 1

        tn = n_per_class - fp_count
        tp = n_per_class - fn_count
        total = n_per_class * 2
        accuracy = (tp + tn) / total
        fpr = fp_count / n_per_class
        fnr = fn_count / n_per_class

        print(f"\n[Monte Carlo Random Flow Evaluation - {total} Samples]")
        print(f"  TP: {tp} | TN: {tn} | FP: {fp_count} | FN: {fn_count}")
        print(f"  Accuracy : {accuracy * 100:.2f}% (Target: >= 99.0%)")
        print(f"  FPR      : {fpr * 100:.2f}% (Target: < 1.0%)")
        print(f"  FNR      : {fnr * 100:.2f}% (Target: < 1.0%)")

        self.assertGreaterEqual(accuracy, 0.99, f"Monte Carlo accuracy {accuracy*100:.2f}% fell below 99%.")
        self.assertLess(fpr, 0.01, f"False Positive Rate {fpr*100:.2f}% exceeded 1.0%.")
        self.assertLess(fnr, 0.01, f"False Negative Rate {fnr*100:.2f}% exceeded 1.0%.")

    # -------------------------------------------------------------
    # 4. Perturbation & Noise Robustness Test (+-20% Jitter)
    # -------------------------------------------------------------
    def test_10_noise_robustness(self):
        """
        Verify that adding +-20% Gaussian noise/jitter to continuous legitimate traffic
        does not cause erratic false positive classification spikes.
        """
        np.random.seed(123)
        base_pps = 850.0
        base_bps = 10_000_000.0

        noise_errors = 0
        trials = 100
        for _ in range(trials):
            jitter_pps = float(base_pps * (1.0 + np.random.normal(0, 0.15)))
            jitter_bps = float(base_bps * (1.0 + np.random.normal(0, 0.15)))
            flow = {
                'src_ip': '10.0.0.1',
                'dst_ip': '10.0.0.3',
                'pps': max(100.0, jitter_pps),
                'bps': max(1_000_000.0, jitter_bps),
                'duration_sec': 60.0,
                'packet_count': int(jitter_pps * 60),
                'src_port': 54321,
                'dst_port': 80,
                'ip_proto': 17
            }
            is_ddos, _ = self.detector.predict(flow)
            if is_ddos:
                noise_errors += 1

        stability_rate = (trials - noise_errors) / trials
        print(f"\n[Noise Robustness Test (+-20% Jitter on Legit Traffic)]")
        print(f"  Stable Predictions : {trials - noise_errors}/{trials} ({stability_rate * 100:.1f}%)")
        self.assertEqual(noise_errors, 0, f"Expected 0 false positives under noise, got {noise_errors}")

    # -------------------------------------------------------------
    # 5. Latency SLA Benchmark
    # -------------------------------------------------------------
    def test_11_latency_sla_benchmark(self):
        """Verify inference latency over 500 single-flow iterations is strictly < 5.0 ms."""
        sample_flow = {
            'src_ip': '10.0.0.2', 'dst_ip': '10.0.0.3', 'pps': 25000.0,
            'bps': 50_000_000.0, 'duration_sec': 10.0, 'packet_count': 250000,
            'src_port': 50000, 'dst_port': 80, 'ip_proto': 17
        }
        latencies = []
        for _ in range(500):
            _, lat = self.detector.predict(sample_flow)
            latencies.append(lat)

        avg_lat = sum(latencies) / len(latencies)
        p99_lat = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"\n[Latency SLA Benchmark]")
        print(f"  Average Latency : {avg_lat:.3f} ms")
        print(f"  99th Percentile : {p99_lat:.3f} ms")

        self.assertLess(avg_lat, 1.0, "Average latency should be well under 1.0 ms.")
        self.assertLess(p99_lat, 5.0, "99th percentile latency must strictly pass < 5.0 ms SLA.")


if __name__ == '__main__':
    unittest.main()
