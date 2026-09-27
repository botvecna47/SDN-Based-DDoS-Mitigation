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

        data = {
            "status": state.get("status", "NORMAL"),
            "current_pps": state.get("current_pps", 0),
            "normal_baseline_pps": state.get("normal_baseline_pps", 0),
            "active_flows": state.get("active_flows", 0),
            "blocked_count": len(state.get("blocked_ips", [])),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "controller_uptime_sec": state.get("controller_uptime_sec", 0)
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
