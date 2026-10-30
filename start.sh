#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

activate_backend_venv() {
    local activate_script="$PROJECT_ROOT/ryu39_env/bin/activate"
    if [[ ! -f "$activate_script" ]]; then
        echo "Missing ryu39_env. Follow RUNNING_GUIDE.md to create the Python 3.9 environment." >&2
        exit 1
    fi
    # shellcheck disable=SC1091
    source "$activate_script"
}

echo "SDN DDoS project launcher"
echo "Start Ryu first, then Flask, then Mininet."
echo "1) Start Ryu controller (start first)"
echo "2) Start Flask API"
echo "3) Start Mininet topology (after Ryu; requires sudo)"
echo "4) Start React dashboard on this machine (use npm run dev on Windows for VMware setup)"
echo "5) Train ML Random Forest model (ml_pipeline/train.py)"
echo "6) Exit"
read -r -p "Select a component: " choice

case "$choice" in
    1)
        activate_backend_venv
        exec ryu-manager controller/simple_monitor.py
        ;;
    2)
        activate_backend_venv
        cd "$PROJECT_ROOT/backend_api"
        exec python3 app.py
        ;;
    3)
        sudo mn -c
        exec sudo python3 "$PROJECT_ROOT/network/topo.py"
        ;;
    4)
        exec npm run dev
        ;;
    5)
        activate_backend_venv
        exec python3 "$PROJECT_ROOT/ml_pipeline/train.py"
        ;;
    6)
        exit 0
        ;;
    *)
        echo "Invalid choice." >&2
        exit 2
        ;;
esac
