import os
import sys
import time
import json

# Setup import path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'controller'))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend_api'))
sys.path.insert(0, os.path.join(BASE_DIR, 'ml_pipeline'))

from inference_loader import DDoSDetector
import state_manager

results = {}

def run_checks():
    print("=" * 65)
    print("   SDN DDoS ML MODEL INTEGRATION - UAT VERIFICATION SUITE   ")
    print("=" * 65)

    # ---------------------------------------------------------
    # TEST 1: File Existence & Integrity Check
    # ---------------------------------------------------------
    print("\n[TEST 1] Verifying File Placement and Artifact Integrity...")
    critical_files = [
        "ml_pipeline/exported_models/best_sdn_model.joblib",
        "ml_pipeline/exported_models/scaler.joblib",
        "ml_pipeline/exported_models/anova_selector.joblib",
        "ml_pipeline/exported_models/selected_features.json",
        "ml_pipeline/exported_models/model_metadata.json",
        "ml_pipeline/detector.joblib",
        "ml_pipeline/predict.py",
        "controller/inference_loader.py",
        "controller/simple_monitor.py",
        "backend_api/app.py",
        "backend_api/state_manager.py",
        "docs/SDN_DDOS_PIPELINE_REPORT.md",
        "docs/presentation/SDN_DDoS_ML_Pipeline_Presentation.pptx",
        "docs/visualizations/accuracy_vs_latency.png"
    ]
    missing = []
    file_sizes = {}
    for f in critical_files:
        full_p = os.path.join(BASE_DIR, f)
        if not os.path.exists(full_p):
            missing.append(f)
        else:
            file_sizes[f] = os.path.getsize(full_p)

    if missing:
        print(f"  [FAIL] Missing files: {missing}")
        results["test_1_files"] = {"status": "FAIL", "missing": missing}
    else:
        print(f"  [PASS] All {len(critical_files)} critical files present and readable.")
        for f, sz in file_sizes.items():
            print(f"     - {f} ({sz:,} bytes)")
        results["test_1_files"] = {"status": "PASS", "files_verified": len(critical_files)}

    # ---------------------------------------------------------
    # TEST 2: DDoSDetector Initialization & Tier 1 Active
    # ---------------------------------------------------------
    print("\n[TEST 2] Verifying DDoSDetector Engine Initialization...")
    detector = DDoSDetector()
    print(f"  - Active Tier      : Tier {detector.tier}")
    print(f"  - Model Name       : {detector.model_name}")
    print(f"  - Is Loaded        : {detector.is_loaded}")
    print(f"  - ANOVA Features   : {len(detector.selected_features)}")

    if detector.tier == 1 and detector.is_loaded and len(detector.selected_features) == 28:
        print("  [PASS] Tier 1 CIC-DDoS2019 Decision Tree is fully active with 28 features.")
        results["test_2_init"] = {"status": "PASS", "tier": detector.tier, "model": detector.model_name}
    else:
        print(f"  [FAIL] Expected Tier 1 active with 28 features, got Tier {detector.tier}.")
        results["test_2_init"] = {"status": "FAIL", "tier": detector.tier}

    # ---------------------------------------------------------
    # TEST 3: Classification Accuracy on SDN Traffic Scenarios
    # ---------------------------------------------------------
    print("\n[TEST 3] Verifying Flow Classification Accuracy...")
    test_cases = [
        {
            "name": "Legitimate Host (h1 -> h3, 200 PPS idle/web)",
            "flow": {'src_ip': '10.0.0.1', 'dst_ip': '10.0.0.3', 'pps': 200.0, 'bps': 200*1200*8, 'duration_sec': 30.0, 'packet_count': 6000, 'src_port': 54321, 'dst_port': 80, 'ip_proto': 17},
            "expected_ddos": False
        },
        {
            "name": "Legitimate Host (h1 -> h3, 850 PPS continuous iperf)",
            "flow": {'src_ip': '10.0.0.1', 'dst_ip': '10.0.0.3', 'pps': 850.0, 'bps': 10_000_000.0, 'duration_sec': 60.0, 'packet_count': 51000, 'src_port': 54321, 'dst_port': 80, 'ip_proto': 17},
            "expected_ddos": False
        },
        {
            "name": "Volumetric UDP Flood (h2 -> h3, 15,000 PPS)",
            "flow": {'src_ip': '10.0.0.2', 'dst_ip': '10.0.0.3', 'pps': 15000.0, 'bps': 15000*700*8, 'duration_sec': 5.0, 'packet_count': 75000, 'src_port': 50000, 'dst_port': 80, 'ip_proto': 17},
            "expected_ddos": True
        },
        {
            "name": "Extreme DDoS Flood (h2 -> h3, 35,000 PPS line rate)",
            "flow": {'src_ip': '10.0.0.2', 'dst_ip': '10.0.0.3', 'pps': 35000.0, 'bps': 70_000_000.0, 'duration_sec': 10.0, 'packet_count': 350000, 'src_port': 50000, 'dst_port': 80, 'ip_proto': 17},
            "expected_ddos": True
        },
        {
            "name": "Legacy Positional Arg Interface (pps=850, bps=10M)",
            "positional": (850.0, 10_000_000.0, 60.0, 51000),
            "expected_ddos": False
        }
    ]

    all_passed = True
    for tc in test_cases:
        if "flow" in tc:
            is_ddos, lat = detector.predict(tc["flow"])
        else:
            is_ddos, lat = detector.predict(*tc["positional"])

        expected = tc["expected_ddos"]
        actual_label = "ATTACK" if is_ddos else "BENIGN"
        expected_label = "ATTACK" if expected else "BENIGN"
        match = (is_ddos == expected)

        print(f"  - {tc['name']}")
        print(f"    Expected: {expected_label} | Actual: {actual_label} | Latency: {lat:.3f} ms | Status: {'[PASS]' if match else '[FAIL]'}")
        if not match:
            all_passed = False

    results["test_3_classification"] = {"status": "PASS" if all_passed else "FAIL"}

    # ---------------------------------------------------------
    # TEST 4: Single-Packet Latency SLA Benchmark (1,000 runs)
    # ---------------------------------------------------------
    print("\n[TEST 4] Measuring 1,000-Iteration Latency Benchmark (Ryu SLA Target: < 5.0 ms)...")
    sample_flow = {
        'src_ip': '10.0.0.2', 'dst_ip': '10.0.0.3', 'pps': 25000.0,
        'bps': 50_000_000.0, 'duration_sec': 10.0, 'packet_count': 250000,
        'src_port': 50000, 'dst_port': 80, 'ip_proto': 17
    }

    # Warmup
    for _ in range(50):
        detector.predict(sample_flow)

    latencies = []
    t_start = time.perf_counter()
    for _ in range(1000):
        _, lat = detector.predict(sample_flow)
        latencies.append(lat)
    t_total = time.perf_counter() - t_start

    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    avg_lat = sum(latencies) / len(latencies)
    throughput_pps = 1000.0 / t_total

    print(f"  - Average Latency : {avg_lat:.3f} ms")
    print(f"  - Median (p50)    : {p50:.3f} ms")
    print(f"  - 95th Percentile : {p95:.3f} ms")
    print(f"  - 99th Percentile : {p99:.3f} ms")
    print(f"  - Peak Throughput : {throughput_pps:,.0f} flow inferences/sec")
    print(f"  - SLA Compliance  : {'[PASS] (< 5.0 ms SLA)' if p99 < 5.0 else '[FAIL]'}")

    results["test_4_latency"] = {
        "status": "PASS" if p99 < 5.0 else "FAIL",
        "avg_ms": round(avg_lat, 3),
        "p99_ms": round(p99, 3),
        "throughput_fps": int(throughput_pps)
    }

    # ---------------------------------------------------------
    # TEST 5: State Synchronization & Shared State Verification
    # ---------------------------------------------------------
    print("\n[TEST 5] Verifying State Management Synchronization...")
    state_manager.initialize_state()
    state_manager.update_state(
        status="UNDER_ATTACK",
        blocked_ips=["10.0.0.2"],
        current_pps=25000,
        dropped_pps=25000,
        active_flows=3,
        detection_mode="machine_learning",
        ml_model_name=detector.model_name,
        inference_latency_ms=avg_lat
    )
    current_state = state_manager.read_state()

    print(f"  - State Status        : {current_state.get('status')}")
    print(f"  - Blocked IPs         : {current_state.get('blocked_ips')}")
    print(f"  - Detection Mode      : {current_state.get('detection_mode')}")
    print(f"  - ML Model Name       : {current_state.get('ml_model_name')}")
    print(f"  - ML Latency Recorded : {current_state.get('inference_latency_ms'):.3f} ms")

    state_valid = (
        current_state.get('detection_mode') == "machine_learning" and
        current_state.get('status') == "UNDER_ATTACK" and
        "10.0.0.2" in current_state.get('blocked_ips', []) and
        "CIC-DDoS2019" in str(current_state.get('ml_model_name', ''))
    )
    print(f"  - State Check Status  : {'[PASS]' if state_valid else '[FAIL]'}")
    results["test_5_state"] = {"status": "PASS" if state_valid else "FAIL"}

    # Restore clean state
    state_manager.initialize_state()

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print("\n" + "=" * 65)
    all_tests_pass = all(v["status"] == "PASS" for v in results.values())
    if all_tests_pass:
        print("SUCCESS: ALL 5 UAT VERIFICATION TESTS PASSED WITH 100% SUCCESS!")
    else:
        print("FAILURE: ONE OR MORE TESTS FAILED - REVIEW LOGS ABOVE.")
    print("=" * 65)

    return all_tests_pass

if __name__ == '__main__':
    ok = run_checks()
    sys.exit(0 if ok else 1)
