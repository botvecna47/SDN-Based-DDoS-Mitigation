import json
import os
from filelock import FileLock

# ==============================================================================
# 🚨 CRITICAL ARCHITECTURE FIX: RYU-FLASK BRIDGE 🚨
# Ryu (Eventlet) and Flask (WSGI) thread-block each other if run in the same script.
# Solution: Ryu writes to this JSON file, Flask reads from it.
# We use a FileLock so they don't corrupt the file by reading/writing simultaneously.
# ==============================================================================

STATE_FILE = os.path.join(os.path.dirname(__file__), 'shared_state.json')
LOCK_FILE = f"{STATE_FILE}.lock"

def initialize_state():
    """Run this once when the system starts to create the blank state."""
    default_state = {
        "status": "NORMAL",
        "current_pps": 0,
        "normal_baseline_pps": 0,
        "active_flows": 0,
        "blocked_count": 0,
        "timestamp": "",
        "blocked_ips": []
    }
    with FileLock(LOCK_FILE):
        with open(STATE_FILE, 'w') as f:
            json.dump(default_state, f, indent=4)

def update_state(new_data_dict):
    """RYU CONTROLLER uses this to push new data."""
    with FileLock(LOCK_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            state.update(new_data_dict)
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
        except (FileNotFoundError, json.JSONDecodeError):
            pass # Failsafe if file is missing

def read_state():
    """FLASK API uses this to serve data to React."""
    with FileLock(LOCK_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"error": "State file unavailable"}
