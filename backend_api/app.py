from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from datetime import datetime
import os
import time
import collections
from state_manager import read_state, initialize_state

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

# Rolling window for the 48-tick SVG chart in the new UI
history_ingress = collections.deque([0]*48, maxlen=48)
history_dropped = collections.deque([0]*48, maxlen=48)
last_update_time = 0

@app.route('/api/network-stats', methods=['GET'])
def network_stats():
    global last_update_time
    try:
        state = read_state()
        if "error" in state:
            return jsonify({"error": state["error"]}), 503

        current_pps = state.get("current_pps", 0)
        status = state.get("status", "NORMAL")
        blocked_ips = state.get("blocked_ips", [])
        active_flows = state.get("active_flows", 0)

        # Estimate dropped traffic (if mitigating, we drop ~95% of attack volume)
        mitigated_pps = current_pps * 0.95 if status == "UNDER_ATTACK" else 0
        
        # We only want to append to the chart history once per second max,
        # otherwise fast API polling will artificially squash the chart time window.
        now = time.time()
        if now - last_update_time >= 1.0:
            history_ingress.append(current_pps / 1000.0) # UI expects values in "k" (thousands)
            history_dropped.append(mitigated_pps / 1000.0)
            last_update_time = now

        # Convert simple list of blocked IPs into the structured Threat object the new UI expects
        threats = []
        for i, blocked in enumerate(blocked_ips):
            threats.append({
                "ip": blocked if isinstance(blocked, str) else blocked.get("ip", "Unknown"),
                "country": "Local Mininet",
                "port": 80,
                "protocol": "UDP",
                "reason": "DDoS Signature Detected by ML" if status == "UNDER_ATTACK" else "Flow Anomaly",
                "score": 98 - i,
                "severity": "Critical",
                "time": "Just now"
            })

        # Calculate TB metrics (simulated/estimated based on pps for the visual cards)
        ingress_tb = sum(history_ingress) / 1000.0
        dropped_tb = sum(history_dropped) / 1000.0

        snapshot = {
            "health": "degraded" if status == "UNDER_ATTACK" else "operational",
            "endpointsOnline": 4, # h1, h2, h3, s1
            "endpointsTotal": 4,
            "metrics": {
                "ingressTb": float(max(0.01, ingress_tb)), 
                "droppedTb": float(dropped_tb), 
                "activeRules": int(active_flows + len(threats)), 
                "mlLatencyMs": float(state.get("inference_latency_ms", 3.1))
            },
            "traffic": {
                "ingress": list(history_ingress),
                "dropped": list(history_dropped),
                "threshold": 8 # 8k PPS threshold
            },
            "threats": threats,
            "dropReasons": [
                {"reason": "ML DDoS Classification", "share": 100}
            ] if threats else []
        }
        
        response = make_response(jsonify(snapshot))
        return add_no_cache_headers(response)
    except Exception as e:
        print(f"Error in network_stats: {e}")
        return jsonify({"error": "Internal Server Error"}), 503

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
