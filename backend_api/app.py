from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from datetime import datetime
import os
from state_manager import read_state, initialize_state

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

if not os.path.exists("shared_state.json"):
    try:
        initialize_state()
    except Exception as e:
        print(f"Failed to initialize state: {e}")

def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/api/network-stats', methods=['GET'])
def network_stats():
    try:
        state = read_state()
        if "error" in state:
            return jsonify({"error": state["error"]}), 503

        current_pps = state.get("current_pps", 0)
        baseline_pps = state.get("normal_baseline_pps", 0)
        blocked_ips  = state.get("blocked_ips", [])
        status       = state.get("status", "NORMAL")
        active_flows = state.get("active_flows", 0)
        uptime       = state.get("controller_uptime_sec", 0)
        mitigated    = current_pps - baseline_pps if current_pps > baseline_pps else 0
        bandwidth    = round((current_pps * 1100 * 8) / (1024 * 1024), 2)  # Mbps estimate

        data = {
            # ── Our internal schema fields ──────────────────────────────
            "status":               status,
            "current_pps":          current_pps,
            "normal_baseline_pps":  baseline_pps,
            "active_flows":         active_flows,
            "blocked_count":        len(blocked_ips),
            "timestamp":            datetime.utcnow().isoformat() + "Z",
            "controller_uptime_sec": uptime,

            # ── Tanmay's frontend (App.jsx) field names ─────────────────
            # App.jsx Live API mode reads these exact keys:
            "system_state":             status,           # "NORMAL" | "UNDER_ATTACK"
            "ingress_pps":              current_pps,
            "mitigated_pps":            mitigated,
            "active_flow_rules":        active_flows,
            "bandwidth_mbps":           bandwidth,
            "blocked_ips_count":        len(blocked_ips),
            "ml_inference_latency_ms":  state.get("inference_latency_ms", 3.1),
            "packet_drop_rate_pct":     round((mitigated / current_pps * 100) if current_pps > 0 else 0, 1),
        }
        
        response = make_response(jsonify(data))
        return add_no_cache_headers(response)
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 503

@app.route('/api/blocked-ips', methods=['GET'])
def blocked_ips():
    try:
        state = read_state()
        if "error" in state:
            return jsonify({"error": state["error"]}), 503
            
        data = state.get("blocked_ips", [])
        
        response = make_response(jsonify(data))
        return add_no_cache_headers(response)
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 503
        
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
