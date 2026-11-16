import json
import os
import time
from filelock import FileLock, Timeout

FALLBACK_THRESHOLD_PPS = 10_000

# ==============================================================================
# 🚨 CRITICAL ARCHITECTURE FIX: RYU-FLASK BRIDGE 🚨
# Ryu (Eventlet) and Flask (WSGI) thread-block each other if run in the same script.
# Solution: Ryu writes to this JSON file, Flask reads from it.
# We use a FileLock so they don't corrupt the file by reading/writing simultaneously.
# ==============================================================================

STATE_FILE = os.path.join(os.path.dirname(__file__), 'shared_state.json')
LOCK_FILE = f"{STATE_FILE}.lock"


def get_default_state():
    """Default baseline network state dictionary."""
    return {
        "status": "NORMAL",
        "current_pps": 0,
        "normal_baseline_pps": 0,
        "active_flows": 0,
        "blocked_count": 0,
        "blocked_ips": [],
        "dropped_pps": 0,
        "detection_mode": "machine_learning",
        "ml_model_name": "CIC-DDoS2019 Decision Tree",
        "inference_latency_ms": 0.28,
        "fallback_threshold_pps": FALLBACK_THRESHOLD_PPS,
        "switch_connected": False,
        "last_updated_at": 0,
        "openflow_rules": [],
        "timestamp": "",
        "controller_uptime_sec": 0,
    }


def initialize_state():
    """Run this once when the system starts to create the blank state."""
    default_state = get_default_state()
    try:
        with FileLock(LOCK_FILE, timeout=2):
            with open(STATE_FILE, 'w') as f:
                json.dump(default_state, f, indent=4)
    except Timeout:
        pass


def update_state(**kwargs):
    """RYU CONTROLLER uses this to push new data. Auto-heals corrupted JSON."""
    try:
        with FileLock(LOCK_FILE, timeout=2):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                state.update(kwargs)
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=4)
            except (FileNotFoundError, json.JSONDecodeError):
                state = get_default_state()
                state.update(kwargs)
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=4)
    except Timeout:
        pass


def read_state():
    """FLASK API uses this to serve data to React. Auto-recovers stale lockfiles."""
    try:
        with FileLock(LOCK_FILE, timeout=2):
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {"error": "State file unavailable"}
    except Timeout:
        try:
            if os.path.exists(LOCK_FILE) and (time.time() - os.path.getmtime(LOCK_FILE) > 5.0):
                os.remove(LOCK_FILE)
                with FileLock(LOCK_FILE, timeout=1):
                    with open(STATE_FILE, 'r') as f:
                        return json.load(f)
        except Exception:
            pass
        return {"error": "State file lock timeout"}
