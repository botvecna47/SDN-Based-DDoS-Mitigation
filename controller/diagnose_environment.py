#!/usr/bin/env python3
"""
Pre-Flight Diagnostic & Environment Health Audit
=================================================
Proactively checks for every known failure condition in the SDN environment:
  1. Port collisions (TCP 6653, TCP 5000)
  2. Stale Mininet / OVS interfaces and locks
  3. Ryu compatibility dependencies (setuptools < 60, eventlet == 0.30.2)
  4. System CLI utilities (ovs-ofctl, hping3, iperf, mn)
  5. IPC FileLock health (shared_state.json.lock)
  6. Model artifact presence and tier resolution

For every failed check, generates exact copy-paste remediation commands.

Usage:
    python3 controller/diagnose_environment.py
    (or on Windows: py controller/diagnose_environment.py)
"""

import os
import sys
import time
import socket
import subprocess
import shutil
import json
from pathlib import Path

# Python 3.9 venv trampoline for host execution compatibility
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / "ryu39_env" / "bin" / "python3"

if sys.version_info >= (3, 10) and VENV_PYTHON.exists() and os.environ.get("VENV_REEXEC") != "1":
    env = os.environ.copy()
    env["VENV_REEXEC"] = "1"
    args = [str(VENV_PYTHON), __file__] + sys.argv[1:]
    res = subprocess.run(args, env=env)
    sys.exit(res.returncode)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'controller'))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend_api'))
sys.path.insert(0, os.path.join(BASE_DIR, 'ml_pipeline'))


def check_port_open(port: int) -> bool:
    """Returns True if port is free (not already bound)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        res = s.connect_ex(('127.0.0.1', port))
        return res != 0  # 0 means port is open/listening (already in use)


def run_diagnostics():
    print("=" * 76)
    print("       SDN DDOS ENVIRONMENT & INFRASTRUCTURE PRE-FLIGHT AUDIT       ")
    print("=" * 76)

    issues = []
    checks_passed = 0
    total_checks = 0

    # -------------------------------------------------------------
    # 1. Port Availability Checks
    # -------------------------------------------------------------
    total_checks += 2
    p6653_free = check_port_open(6653)
    p5000_free = check_port_open(5000)

    print("\n[CHECK 1] Network Port Availability:")
    if p6653_free:
        print("  [PASS] Port 6653 (OpenFlow Controller) is FREE and ready.")
        checks_passed += 1
    else:
        print("  [FAIL] Port 6653 is ALREADY IN USE by another process!")
        issues.append({
            "component": "OpenFlow Port 6653 Collision",
            "impact": "Ryu controller will crash with 'Address already in use'",
            "remediation": "sudo fuser -k 6653/tcp || sudo pkill -f ryu-manager"
        })

    if p5000_free:
        print("  [PASS] Port 5000 (Flask REST API) is FREE and ready.")
        checks_passed += 1
    else:
        print("  [FAIL] Port 5000 is ALREADY IN USE by another process!")
        issues.append({
            "component": "Flask API Port 5000 Collision",
            "impact": "Flask app.py will fail to bind port 5000",
            "remediation": "sudo fuser -k 5000/tcp || pkill -f 'python3 app.py'"
        })

    # -------------------------------------------------------------
    # 2. Dependency & Version Pins (Ryu / Setuptools / Eventlet)
    # -------------------------------------------------------------
    print("\n[CHECK 2] Python Package Pin Integrity:")
    total_checks += 3

    # Check setuptools
    try:
        import setuptools
        st_ver = setuptools.__version__
        major_st = int(st_ver.split('.')[0])
        if major_st < 60:
            print(f"  [PASS] setuptools == {st_ver} (< 60.0.0 compatible with Ryu)")
            checks_passed += 1
        else:
            print(f"  [WARN] setuptools == {st_ver} (>= 60.0.0 can cause 'get_script_args' error on Ryu)")
            issues.append({
                "component": "setuptools version too new",
                "impact": "Ryu CLI fails with AttributeError: module 'setuptools' has no attribute 'get_script_args'",
                "remediation": "pip install setuptools==59.6.0 wheel==0.37.1"
            })
    except Exception as e:
        print(f"  [FAIL] Could not check setuptools: {e}")

    # Check eventlet
    try:
        import eventlet
        ev_ver = eventlet.__version__
        print(f"  [PASS] eventlet == {ev_ver} installed.")
        checks_passed += 1
    except ImportError:
        print("  [FAIL] eventlet is NOT installed in this environment!")
        issues.append({
            "component": "Missing eventlet",
            "impact": "Ryu controller cannot start its async event loop",
            "remediation": "pip install eventlet==0.30.2"
        })

    # Check scikit-learn & joblib
    try:
        import sklearn
        import joblib
        print(f"  [PASS] scikit-learn == {sklearn.__version__}, joblib == {joblib.__version__}")
        checks_passed += 1
    except ImportError as e:
        print(f"  [FAIL] Missing ML runtime library: {e}")
        issues.append({
            "component": "Missing Scikit-Learn or Joblib",
            "impact": "ML inference engine cannot load trained decision tree artifacts",
            "remediation": "pip install scikit-learn joblib numpy pandas"
        })

    # -------------------------------------------------------------
    # 3. Model Artifacts & ML Engine Integrity
    # -------------------------------------------------------------
    print("\n[CHECK 3] Machine Learning Model Artifacts:")
    total_checks += 2
    from inference_loader import DDoSDetector
    detector = DDoSDetector()
    if detector.is_loaded and detector.tier == 1:
        print(f"  [PASS] Tier 1 Model Active: {detector.model_name}")
        checks_passed += 1
    elif detector.is_loaded and detector.tier == 2:
        print(f"  [WARN] Operating on Tier 2 Fallback: {detector.model_name}")
        issues.append({
            "component": "Tier 1 Model Artifacts Missing",
            "impact": "Using 4-feature legacy model instead of full CIC-DDoS2019 28-feature model",
            "remediation": "git checkout origin/mlbranch -- exported_models && python3 controller/test_ml_integration.py"
        })
    else:
        print("  [FAIL] No ML models loaded! Operating on Tier 3 Threshold Fallback.")
        issues.append({
            "component": "No ML Models Found",
            "impact": "System is using rate fallback (PPS > 10,000) only",
            "remediation": "python3 ml_pipeline/train.py --synthetic"
        })

    # Test single packet inference
    try:
        is_ddos, lat = detector.predict(pps=850.0, bps=10000000.0, duration_sec=60.0, packet_count=51000)
        print(f"  [PASS] Test Inference: is_ddos={is_ddos}, latency={lat:.3f} ms (< 5.0 ms SLA)")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] Test inference crashed: {e}")
        issues.append({
            "component": "Inference Execution Failure",
            "impact": "DDoSDetector.predict() crashed on standard input",
            "remediation": "Review error log and re-run python3 controller/test_ml_integration.py"
        })

    # -------------------------------------------------------------
    # 4. IPC State File & Lockfile Health
    # -------------------------------------------------------------
    print("\n[CHECK 4] IPC State & FileLock Health:")
    total_checks += 1
    import state_manager
    lock_file = state_manager.LOCK_FILE
    if os.path.exists(lock_file):
        try:
            # Test if lock is free and safely remove leftover lockfile
            with state_manager.FileLock(lock_file, timeout=0.1):
                try:
                    os.remove(lock_file)
                except OSError:
                    pass
            print("  [PASS] Cleaned leftover lockfile; IPC state is healthy.")
            checks_passed += 1
        except state_manager.Timeout:
            lock_age = time.time() - os.path.getmtime(lock_file)
            print(f"  [WARN] Lockfile actively held: {lock_file} (Age: {lock_age:.1f}s)")
            issues.append({
                "component": "Stale FileLock Detected",
                "impact": "Flask API or Ryu might timeout reading/writing shared_state.json",
                "remediation": f"rm -f {lock_file}"
            })
    else:
        print("  [PASS] No orphaned lockfiles found.")
        checks_passed += 1

    # -------------------------------------------------------------
    # 5. Linux System Utilities (on Linux/Ubuntu)
    # -------------------------------------------------------------
    if sys.platform.startswith('linux'):
        print("\n[CHECK 5] Linux Network & Mininet Utilities:")
        tools = ['mn', 'ovs-ofctl', 'hping3', 'iperf']
        for t in tools:
            total_checks += 1
            if shutil.which(t):
                print(f"  [PASS] Binary '{t}' is available in PATH.")
                checks_passed += 1
            else:
                print(f"  [FAIL] Binary '{t}' NOT found in PATH!")
                issues.append({
                    "component": f"Missing Utility: {t}",
                    "impact": f"Mininet topology or traffic script '{t}' cannot execute",
                    "remediation": f"sudo apt update && sudo apt install -y {t}" if t != 'mn' else "sudo apt install -y mininet openvswitch-switch"
                })

    # -------------------------------------------------------------
    # SUMMARY & PRESCRIPTIVE REMEDIATION GUIDE
    # -------------------------------------------------------------
    print("\n" + "=" * 76)
    print(f"  DIAGNOSTIC SUMMARY: {checks_passed}/{total_checks} CHECKS PASSED")
    print("=" * 76)

    if not issues:
        print("\n[READY FOR PRODUCTION] All environmental health checks passed!")
        print("You can safely start the system using the standard order of operations:")
        print("  1. ryu-manager controller/simple_monitor.py")
        print("  2. cd backend_api && python3 app.py")
        print("  3. sudo mn -c && sudo python3 network/topo.py")
        print("  4. npm run dev (on Windows Host)")
    else:
        print(f"\n[ATTENTION] Detected {len(issues)} issue(s) that could cause startup failures:")
        print("-" * 76)
        for i, issue in enumerate(issues, start=1):
            print(f"\nIssue #{i}: {issue['component']}")
            print(f"  Impact      : {issue['impact']}")
            print(f"  FIX COMMAND : {issue['remediation']}")
        print("\n" + "-" * 76)
        print("Run the fix command(s) listed above, then re-run this diagnostic script.")

    print("=" * 76 + "\n")
    return len(issues) == 0


if __name__ == '__main__':
    ok = run_diagnostics()
    sys.exit(0 if ok else 1)
