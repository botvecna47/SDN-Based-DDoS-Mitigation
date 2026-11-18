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
echo "Recommended order: Ryu -> Flask -> Mininet -> Dashboard"
echo "1) Start Ryu controller (start first)"
echo "2) Start Flask API"
echo "3) Start 10-Host Botnet topology (network/topo_botnet.py; requires sudo)"
echo "4) Start 3-Host Classic topology (network/topo.py; requires sudo)"
echo "5) Launch Interactive Attack Menu (network/attack_menu.sh; requires sudo)"
echo "6) Start React dashboard (npm run dev)"
echo "7) Train ML model (ml_pipeline/train.py)"
echo "8) Exit"
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
        exec sudo python3 "$PROJECT_ROOT/network/topo_botnet.py"
        ;;
    4)
        sudo mn -c
        exec sudo python3 "$PROJECT_ROOT/network/topo.py"
        ;;
    5)
        exec sudo bash "$PROJECT_ROOT/network/attack_menu.sh"
        ;;
    6)
        exec npm run dev
        ;;
    7)
        activate_backend_venv
        exec python3 "$PROJECT_ROOT/ml_pipeline/train.py"
        ;;
    8)
        exit 0
        ;;
    *)
        echo "Invalid choice." >&2
        exit 2
        ;;
esac
