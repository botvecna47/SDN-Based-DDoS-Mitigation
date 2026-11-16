from flask import Flask, jsonify, make_response
from flask_cors import CORS
from datetime import datetime, timezone
import os
import time
import collections
import threading
import logging
from state_manager import FALLBACK_THRESHOLD_PPS, read_state, initialize_state

# Setup dedicated Backend API logger
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
BACKEND_LOG_PATH = os.path.join(LOGS_DIR, 'backend.log')
backend_logger = logging.getLogger('backend_api')
backend_logger.setLevel(logging.INFO)
if not backend_logger.handlers:
    bh = logging.FileHandler(BACKEND_LOG_PATH)
    bh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    backend_logger.addHandler(bh)

backend_logger.info("SDN DDoS Backend API initializing...")

app = Flask(__name__)
CORS(app, origins="*")   # Allow all origins for local demo

STATE_FILE_PATH = os.path.join(os.path.dirname(__file__), 'shared_state.json')
if not os.path.exists(STATE_FILE_PATH):
    try:
        initialize_state()
    except Exception as e:
        print(f"Failed to initialize state: {e}")

def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Rolling window for the 48-tick SVG chart in the UI
history_ingress = collections.deque([0.0]*48, maxlen=48)
history_dropped = collections.deque([0.0]*48, maxlen=48)

def safe_float(val, default=0.0):
    try:
        if val is None:
            return default
        f = float(val)
        if f != f or f == float('inf') or f == float('-inf'):
            return default
        return f
    except (ValueError, TypeError, OverflowError):
        return default

def safe_int(val, default=0):
    try:
        if val is None:
            return default
        f = float(val)
        if f != f or f == float('inf') or f == float('-inf'):
            return default
        return int(f)
    except (ValueError, TypeError, OverflowError):
        return default

def history_collector():
    """
    Background daemon thread that records traffic rates every 1.0s.
    Decouples chart history progression from API request frequency,
    eliminating request-jitter stutter and dropped ticks.
    """
    while True:
        try:
            state = read_state()
            last_updated_at = float(state.get("last_updated_at", 0) or 0)
            switch_connected = bool(state.get("switch_connected", False)) and time.time() - last_updated_at <= 5

            if switch_connected:
                current_pps = max(0.0, float(state.get("current_pps", 0)))
                mitigated_pps = max(0.0, float(state.get("dropped_pps", 0)))
            else:
                current_pps = 0.0
                mitigated_pps = 0.0

            history_ingress.append(round(current_pps / 1000.0, 2))
            history_dropped.append(round(mitigated_pps / 1000.0, 2))
        except Exception:
            pass
        time.sleep(1.0)

collector_thread = threading.Thread(target=history_collector, daemon=True)
collector_thread.start()

@app.route('/api/network-stats', methods=['GET'])
def network_stats():
    try:
        state = read_state()
        if "error" in state:
            return jsonify({"error": state["error"]}), 503

        current_pps = max(0.0, float(state.get("current_pps", 0)))
        status = state.get("status", "NORMAL")
        blocked_ips = state.get("blocked_ips", [])
        active_flows = max(0, int(state.get("active_flows", 0)))
        last_updated_at = float(state.get("last_updated_at", 0) or 0)
        switch_connected = bool(state.get("switch_connected", False)) and time.time() - last_updated_at <= 5
        if not switch_connected:
            current_pps = 0.0
            active_flows = 0

        fallback_threshold_pps = max(1, int(state.get("fallback_threshold_pps", FALLBACK_THRESHOLD_PPS)))

        # Ryu calculates this from the switch's source-IP DROP flow counters.
        mitigated_pps = max(0.0, float(state.get("dropped_pps", 0))) if switch_connected else 0.0
        forwarded_pps = max(0.0, current_pps - mitigated_pps)

        # Convert simple list of blocked IPs into the structured Threat object the UI expects
        threats = []
        for blocked in blocked_ips:
            ip_val = blocked if isinstance(blocked, str) else blocked.get("ip", "Unknown")
            if ip_val == "10.0.0.3":
                continue  # Never display the protected target server as an attacker
            if ip_val == "10.0.0.2":
                host_label = "h2 (Attacker Host)"
            elif ip_val.startswith("10.0.0."):
                try:
                    octet = int(ip_val.split(".")[-1])
                    if 4 <= octet <= 8:
                        host_label = f"h{octet} (Botnet Attacker)"
                    elif octet == 1:
                        host_label = "h1 (Legitimate User)"
                    else:
                        host_label = f"Host ({ip_val})"
                except ValueError:
                    host_label = "Mininet Host"
            else:
                host_label = f"Host ({ip_val})"

            threats.append({
                "ip": ip_val,
                "country": host_label,
                "port": 80,
                "protocol": "UDP",
                "reason": f"DDoS detected by {state.get('ml_model_name', 'ML Decision Tree')}" if state.get("detection_mode") == "machine_learning" else "DDoS detected by PPS threshold fallback",
                "severity": "Critical"
            })

        snapshot = {
            "health": "offline" if not switch_connected else ("degraded" if status == "UNDER_ATTACK" else "operational"),
            "detectionMode": state.get("detection_mode", "threshold_fallback"),
            "mlModelName": state.get("ml_model_name", "CIC-DDoS2019 Decision Tree"),
            # Only the OpenFlow switch connection is observed directly here;
            # host reachability is not verified by the controller.
            "endpointsOnline": 1 if switch_connected else 0,
            "endpointsTotal": 1,
            "metrics": {
                "currentPps": safe_int(current_pps),
                "droppedPps": safe_int(mitigated_pps),
                "forwardedPps": safe_int(forwarded_pps),
                "uptimeSec": safe_int(state.get("controller_uptime_sec", 0)),
                "activeRules": active_flows if switch_connected else 0,
                "mlLatencyMs": round(safe_float(state.get("inference_latency_ms", 0.28)), 3)
            },
            "traffic": {
                "ingress": list(history_ingress),
                "dropped": list(history_dropped),
                "threshold": fallback_threshold_pps / 1000.0 # PPS shown in thousands
            },
            "threats": threats,
            "dropReasons": [
                {"reason": state.get("ml_model_name", "ML Decision Tree") if state.get("detection_mode") == "machine_learning" else "PPS threshold fallback", "share": 100},
            ] if threats else []
        }

        # Log system state changes to logs/backend.log
        health_state = snapshot["health"]
        global last_logged_health
        if 'last_logged_health' not in globals() or last_logged_health != health_state:
            last_logged_health = health_state
            backend_logger.info(
                f"[STATE CHANGE] Health: {health_state.upper()} | Controller Status: {status} | "
                f"Ingress: {safe_int(current_pps):,} PPS | Dropped: {safe_int(mitigated_pps):,} PPS | "
                f"Clean Forwarded: {safe_int(forwarded_pps):,} PPS | Active Threats: {len(threats)}"
            )

        response = make_response(jsonify(snapshot))
        return add_no_cache_headers(response)
    except Exception as e:
        print(f"Error in network_stats: {e}")
        return jsonify({"error": "Internal Server Error"}), 503

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

@app.route('/api/flow-table', methods=['GET'])
def flow_table():
    """
    Returns a human-readable breakdown of ALLOWED vs BLOCKED flows.
    This makes it clear what traffic is being permitted vs dropped by Ryu.
    """
    try:
        state = read_state()
        last_updated_at = float(state.get("last_updated_at", 0) or 0)
        connected = bool(state.get("switch_connected", False)) and time.time() - last_updated_at <= 5
        rules = state.get("openflow_rules", []) if connected else []
        flow_table = {
            "summary": {
                "description": "Latest OpenFlow 1.3 flow-stat snapshot reported by OVS Switch s1",
                "connected": connected,
                "snapshotAgeSeconds": max(0.0, time.time() - last_updated_at) if last_updated_at else None,
                "allowed_flows": [rule for rule in rules if rule.get("status") == "ALLOWED"],
                "blocked_flows": [rule for rule in rules if rule.get("status") == "BLOCKED"],
                "table_miss": next((rule for rule in rules if rule.get("status") == "CONTROLLER"), None),
                "other_flows": [rule for rule in rules if rule.get("status") not in ("ALLOWED", "BLOCKED", "CONTROLLER")],
            }
        }
        response = make_response(jsonify(flow_table))
        return add_no_cache_headers(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 503

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
