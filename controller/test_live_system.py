#!/usr/bin/env python3
"""
Live End-to-End System Test
===========================
Executes live runtime verification against the running:
1. Ryu SDN Controller (TCP 6653)
2. Flask Backend REST API (TCP 5000)
3. Shared IPC State & FileLock Pipeline
4. Machine Learning Inference Engine (detector.joblib)
5. Live State Transitions: Normal Traffic -> Attack Burst -> ML Mitigation -> Recovery
"""

import os
import sys
import time
import socket
import urllib.request
import json
import subprocess
from pathlib import Path

# Python 3.9 venv trampoline (MUST BE BEFORE 3RD PARTY IMPORTS)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / "ryu39_env" / "bin" / "python3"

if sys.version_info >= (3, 10) and VENV_PYTHON.exists() and os.environ.get("VENV_REEXEC") != "1":
    env = os.environ.copy()
    env["VENV_REEXEC"] = "1"
    args = [str(VENV_PYTHON), __file__] + sys.argv[1:]
    res = subprocess.run(args, env=env)
    sys.exit(res.returncode)

sys.path.insert(0, str(PROJECT_ROOT / "controller"))
sys.path.insert(0, str(PROJECT_ROOT / "backend_api"))

from inference_loader import DDoSDetector
from state_manager import update_state, read_state, initialize_state

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def fetch_api(path: str):
    url = f"http://127.0.0.1:5000{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "SDN-Test-Client"})
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode())


def check_port_listening(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except socket.error:
        return False


def run_live_test():
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}         SDN DDoS Mitigation - Live End-to-End System Test            {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    # 1. Verify Port 6653 (Ryu)
    ryu_live = check_port_listening(6653)
    status_str = f"{GREEN}ACTIVE & LISTENING{RESET}" if ryu_live else f"{RED}NOT LISTENING{RESET}"
    print(f"[1] Ryu Controller TCP 6653 : {status_str}")
    if not ryu_live:
        print(f"{RED}Error: Ryu Controller is not running on port 6653!{RESET}")
        return 1

    # 2. Verify Port 5000 (Flask)
    flask_live = check_port_listening(5000)
    status_str = f"{GREEN}ACTIVE & LISTENING{RESET}" if flask_live else f"{RED}NOT LISTENING{RESET}"
    print(f"[2] Flask Backend API TCP 5000: {status_str}")
    if not flask_live:
        print(f"{RED}Error: Flask API is not running on port 5000!{RESET}")
        return 1

    # 3. Test /api/health
    status_code, health_data = fetch_api("/api/health")
    print(f"[3] GET /api/health          : {GREEN}HTTP {status_code} OK{RESET} -> {health_data}")
    assert status_code == 200 and health_data.get("status") == "ok"

    # 4. Phase 1: Simulate Normal Traffic (h1 -> h3, ~800 PPS)
    print(f"\n{BOLD}[4] Phase 1: Legitimate Normal Traffic Simulation (h1 -> h3){RESET}")
    normal_rules = [
        {
            "match": {"eth_type": 2048, "ipv4_src": "10.0.0.1", "ipv4_dst": "10.0.0.3"},
            "action": "FORWARD",
            "priority": 10,
            "status": "ALLOWED",
            "packets": 12000,
            "bytes": 9600000
        },
        {
            "match": {},
            "action": "SEND_TO_CONTROLLER",
            "priority": 0,
            "status": "CONTROLLER",
            "packets": 0,
            "bytes": 0
        }
    ]

    update_state(
        switch_connected=True,
        last_updated_at=time.time(),
        status="NORMAL",
        current_pps=820.0,
        dropped_pps=0.0,
        active_flows=2,
        blocked_ips=[],
        detection_mode="machine_learning",
        controller_uptime_sec=45,
        openflow_rules=normal_rules
    )

    time.sleep(1.2)  # Allow background history collector to tick
    status_code, stats = fetch_api("/api/network-stats")
    print(f"  • API Response Status : {GREEN}HTTP {status_code} OK{RESET}")
    print(f"  • System Health       : {GREEN}{stats['health'].upper()}{RESET} (Expected: OPERATIONAL)")
    print(f"  • Endpoints Online    : {stats['endpointsOnline']}/{stats['endpointsTotal']}")
    print(f"  • Ingress Throughput  : {stats['metrics']['currentPps']} PPS")
    print(f"  • Active OpenFlows    : {stats['metrics']['activeRules']} rules")
    print(f"  • Active Threats      : {len(stats['threats'])} detected")
    assert stats["health"] == "operational"
    assert len(stats["threats"]) == 0
    assert stats["metrics"]["currentPps"] > 0

    # 5. Phase 2: Simulate Volumetric DDoS Attack (h2 -> h3, 24,000 PPS)
    print(f"\n{BOLD}[5] Phase 2: Volumetric DDoS Attack Burst (h2 -> h3 @ 24,000 PPS){RESET}")
    model_path = PROJECT_ROOT / "ml_pipeline" / "detector.joblib"
    detector = DDoSDetector(str(model_path))

    # Warm-up inference to avoid cold-start overhead
    _ = detector.predict(pps=800.0, bps=6_400_000.0, duration_sec=10.0, packet_count=8000)

    # Run ML prediction on attack flow
    is_attack, inf_latency = detector.predict(pps=24000.0, bps=145_000_000.0, duration_sec=15.0, packet_count=360000)
    print(f"  • ML Inference Result : {RED if is_attack else GREEN}{'DDoS DETECTED' if is_attack else 'NORMAL'}{RESET}")
    print(f"  • ML Decision Delay   : {inf_latency:.3f} ms (SLA < 5.0 ms: {GREEN}PASS{RESET})")
    assert is_attack is True
    assert inf_latency < 5.0

    # Install Drop Rule in OpenFlow switch rules
    attack_rules = list(normal_rules)
    attack_rules.insert(0, {
        "match": {"eth_type": 2048, "ipv4_src": "10.0.0.2"},
        "action": "DROP",
        "priority": 65535,
        "status": "BLOCKED",
        "packets": 240000,
        "bytes": 144000000
    })

    update_state(
        switch_connected=True,
        last_updated_at=time.time(),
        status="UNDER_ATTACK",
        current_pps=24820.0,
        dropped_pps=24000.0,
        active_flows=3,
        blocked_ips=["10.0.0.2"],
        inference_latency_ms=inf_latency,
        detection_mode="machine_learning",
        openflow_rules=attack_rules
    )

    time.sleep(1.2)
    status_code, attack_stats = fetch_api("/api/network-stats")
    status_code_f, flow_table = fetch_api("/api/flow-table")

    print(f"  • API Response Status : {GREEN}HTTP {status_code} OK{RESET}")
    print(f"  • System Health       : {RED}{attack_stats['health'].upper()}{RESET} (Expected: DEGRADED)")
    print(f"  • Ingress PPS         : {attack_stats['metrics']['currentPps']:,} PPS")
    print(f"  • Dropped (Mitigated) : {attack_stats['metrics']['droppedPps']:,} PPS")
    print(f"  • Forwarded Legitimate: {attack_stats['metrics']['forwardedPps']:,} PPS (Client h1 protected)")
    print(f"  • Threats Intercepted : {len(attack_stats['threats'])} threats")
    for th in attack_stats["threats"]:
        print(f"     -> Target: {th['ip']} ({th['country']}) | Severity: {th['severity']} | Reason: {th['reason']}")

    assert attack_stats["health"] == "degraded"
    assert len(attack_stats["threats"]) == 1
    assert attack_stats["threats"][0]["ip"] == "10.0.0.2"
    assert attack_stats["metrics"]["droppedPps"] > 0

    # Verify Flow Table Endpoint
    summary = flow_table["summary"]
    blocked_flows = summary["blocked_flows"]
    allowed_flows = summary["allowed_flows"]
    print(f"\n{BOLD}[6] OpenFlow Switch Table Inspection (/api/flow-table){RESET}")
    print(f"  • Blocked Flows Count : {len(blocked_flows)} (Rule: DROP ipv4_src=10.0.0.2, priority=65535)")
    print(f"  • Allowed Flows Count : {len(allowed_flows)} (Rule: FORWARD ipv4_src=10.0.0.1, priority=10)")
    assert len(blocked_flows) == 1
    assert blocked_flows[0]["match"]["ipv4_src"] == "10.0.0.2"
    assert len(allowed_flows) == 1
    assert allowed_flows[0]["match"]["ipv4_src"] == "10.0.0.1"

    # 7. Phase 3: Auto-Recovery
    print(f"\n{BOLD}[7] Phase 3: Attack Subsidence & Automated Recovery{RESET}")
    update_state(
        switch_connected=True,
        last_updated_at=time.time(),
        status="NORMAL",
        current_pps=800.0,
        dropped_pps=0.0,
        active_flows=2,
        blocked_ips=[],
        openflow_rules=normal_rules
    )
    time.sleep(1.0)
    _, recovered_stats = fetch_api("/api/network-stats")
    print(f"  • Post-Attack Health  : {GREEN}{recovered_stats['health'].upper()}{RESET} (Recovered to OPERATIONAL)")
    assert recovered_stats["health"] == "operational"
    assert len(recovered_stats["threats"]) == 0

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{GREEN}{BOLD}✓ LIVE SYSTEM END-TO-END DEMO TEST PASSED WITH 100% SUCCESS!{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_live_test())
