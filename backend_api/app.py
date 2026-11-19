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

SWITCH_TIMEOUT_SEC = 12.0

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
            switch_connected = bool(state.get("switch_connected", False)) and time.time() - last_updated_at <= SWITCH_TIMEOUT_SEC

            if switch_connected:
                raw_ip_traffic = state.get("ip_traffic", [])
                if raw_ip_traffic:
                    fwd = sum(float(e.get("forwardedPps", 0)) for e in raw_ip_traffic)
                    drp = sum(float(e.get("droppedPps", 0)) for e in raw_ip_traffic)
                    current_pps = fwd + drp
                    mitigated_pps = drp
                else:
                    forwarded_pps = max(0.0, float(state.get("forwarded_pps", 0)))
                    mitigated_pps = max(0.0, float(state.get("dropped_pps", 0)))
                    current_pps = max(0.0, float(state.get("current_pps", forwarded_pps + mitigated_pps)))
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

        status = state.get("status", "NORMAL")
        active_flows = max(0, int(state.get("active_flows", 0)))
        last_updated_at = float(state.get("last_updated_at", 0) or 0)
        switch_connected = bool(state.get("switch_connected", False)) and time.time() - last_updated_at <= SWITCH_TIMEOUT_SEC

        raw_ip_traffic = state.get("ip_traffic", []) if switch_connected else []

        ip_traffic = []
        for entry in raw_ip_traffic:
            ip_traffic.append({
                "ip": entry.get("ip", ""),
                "hostLabel": entry.get("hostLabel", f"Host ({entry.get('ip')})"),
                "mac": entry.get("mac", ""),
                "forwardedPps": safe_int(entry.get("forwardedPps", 0)),
                "droppedPps": safe_int(entry.get("droppedPps", 0)),
                "ingressPps": safe_int(entry.get("ingressPps", 0)),
                "allowedFlows": entry.get("allowedFlows", []),
                "blockedFlows": entry.get("blockedFlows", []),
                "status": entry.get("status", "ALLOWED"),
                "primaryReason": entry.get("primaryReason", "Clean Legitimate Traffic"),
                "severity": entry.get("severity", "Benign"),
            })

        if switch_connected:
            if ip_traffic:
                forwarded_pps = sum(e["forwardedPps"] for e in ip_traffic)
                mitigated_pps = sum(e["droppedPps"] for e in ip_traffic)
                current_pps = forwarded_pps + mitigated_pps
            else:
                forwarded_pps = max(0, int(state.get("forwarded_pps", 0)))
                mitigated_pps = max(0, int(state.get("dropped_pps", 0)))
                current_pps = max(0, int(state.get("current_pps", forwarded_pps + mitigated_pps)))
        else:
            current_pps = 0
            mitigated_pps = 0
            forwarded_pps = 0
            active_flows = 0

        fallback_threshold_pps = max(1, int(state.get("fallback_threshold_pps", FALLBACK_THRESHOLD_PPS)))

        # Convert blocked and mixed IP traffic entries into detailed Threats for the UI
        threats = []
        for entry in ip_traffic:
            if entry["droppedPps"] > 0 or entry["blockedFlows"]:
                first_bf = entry["blockedFlows"][0] if entry["blockedFlows"] else {}
                target_port = safe_int(first_bf.get("dstPort", 0), default=0)
                target_ip = first_bf.get("dstIp", "10.0.0.3")
                proto = first_bf.get("attackType", first_bf.get("protocol", "Attack Flow"))
                reason = entry.get("primaryReason") or first_bf.get("reason", f"DDoS detected by {state.get('ml_model_name', 'CIC-DDoS2019 Decision Tree')}")

                threats.append({
                    "ip": entry["ip"],
                    "country": entry["hostLabel"],
                    "mac": entry.get("mac", ""),
                    "port": max(0, target_port),
                    "protocol": proto,
                    "target": f"{target_ip}:{target_port}",
                    "reason": reason,
                    "severity": entry.get("severity", "Critical"),
                    "ratePps": entry["droppedPps"],
                    "forwardedPps": entry["forwardedPps"],
                    "ingressPps": entry["ingressPps"],
                    "action": "DROP (Priority 65535)",
                    "status": entry["status"],
                    "flows": entry["blockedFlows"] + entry["allowedFlows"]
                })

        drop_reasons = []
        if threats and mitigated_pps > 0:
            reason_counts = {}
            for t in threats:
                rate = t.get("ratePps", 0)
                if rate > 0:
                    r = t.get("protocol", "Attack Flow")
                    reason_counts[r] = reason_counts.get(r, 0) + rate
            total_drop_rate = sum(reason_counts.values())
            if total_drop_rate > 0:
                for r, rate in reason_counts.items():
                    drop_reasons.append({
                        "reason": r,
                        "share": min(100, max(0, round((rate / total_drop_rate) * 100)))
                    })

        is_under_attack = (status == "UNDER_ATTACK" and (mitigated_pps > 0 or any(t.get("ratePps", 0) > 0 for t in threats)))

        snapshot = {
            "health": "offline" if not switch_connected else ("degraded" if is_under_attack else "operational"),
            "detectionMode": state.get("detection_mode", "threshold_fallback"),
            "mlModelName": state.get("ml_model_name", "CIC-DDoS2019 Decision Tree"),
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
                "threshold": fallback_threshold_pps / 1000.0
            },
            "threats": threats,
            "ipTraffic": ip_traffic,
            "dropReasons": drop_reasons if drop_reasons else (
                [{"reason": state.get("ml_model_name", "CIC-DDoS2019 Decision Tree"), "share": 100}] if threats else []
            )
        }

        # Log state changes
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
    Returns a human-readable breakdown of ALLOWED vs BLOCKED flows with per-rule PPS.
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
