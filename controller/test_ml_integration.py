import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_api'))
from inference_loader import DDoSDetector

def test_inference_engine():
    print("==================================================")
    print("Testing Upgraded DDoSDetector ML Inference Engine")
    print("==================================================")

    detector = DDoSDetector()
    print(f"Active Tier   : {detector.tier}")
    print(f"Model Name    : {detector.model_name}")
    print(f"Is Loaded     : {detector.is_loaded}")
    assert detector.tier == 1, f"Expected Tier 1, got Tier {detector.tier}"

    # 1. Test Legitimate Traffic (h1 -> h3, 850 PPS, 10 Mbps)
    legit_flow = {
        'src_ip': '10.0.0.1',
        'dst_ip': '10.0.0.3',
        'pps': 850.0,
        'bps': 10_000_000.0,
        'duration_sec': 60.0,
        'packet_count': 51000,
        'byte_count': 75_000_000,
        'src_port': 54321,
        'dst_port': 80,
        'ip_proto': 17
    }
    is_ddos, lat = detector.predict(legit_flow)
    print(f"\n[Legit Flow h1 -> h3]")
    print(f"  Classification : {'ATTACK' if is_ddos else 'BENIGN'} (Expected: BENIGN)")
    print(f"  Latency        : {lat:.3f} ms")
    assert not is_ddos, "Legitimate flow was falsely flagged as DDoS!"

    # 2. Test Attack Traffic (h2 -> h3, 25,000 PPS, 50 Mbps UDP flood)
    attack_flow = {
        'src_ip': '10.0.0.2',
        'dst_ip': '10.0.0.3',
        'pps': 25000.0,
        'bps': 50_000_000.0,
        'duration_sec': 10.0,
        'packet_count': 250000,
        'byte_count': 62_500_000,
        'src_port': 50000,
        'dst_port': 80,
        'ip_proto': 17
    }
    is_ddos, lat = detector.predict(attack_flow)
    print(f"\n[Attack Flow h2 -> h3]")
    print(f"  Classification : {'ATTACK' if is_ddos else 'BENIGN'} (Expected: ATTACK)")
    print(f"  Latency        : {lat:.3f} ms")
    assert is_ddos, "DDoS flood was not detected!"

    # 3. Test Backward Compatibility with positional args
    is_ddos_legacy, lat_legacy = detector.predict(850.0, 10_000_000.0, 60.0, 51000)
    print(f"\n[Legacy Positional Args Call]")
    print(f"  Classification : {'ATTACK' if is_ddos_legacy else 'BENIGN'}")
    print(f"  Latency        : {lat_legacy:.3f} ms")

    # 4. Latency SLA Benchmark (500 iterations)
    latencies = []
    for _ in range(500):
        _, l = detector.predict(attack_flow)
        latencies.append(l)

    avg_lat = sum(latencies) / len(latencies)
    max_lat = max(latencies)
    print(f"\n[500-Iteration Latency Benchmark]")
    print(f"  Average Latency : {avg_lat:.3f} ms")
    print(f"  Max Latency     : {max_lat:.3f} ms")
    print(f"  SLA Target      : < 5.000 ms")
    assert avg_lat < 5.0, f"Average latency {avg_lat} ms exceeded 5.0 ms SLA!"
    print(f"  SLA Status      : PASSED")

    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    test_inference_engine()
