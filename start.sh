#!/bin/bash
# ==============================================================================
# Helper Script: SDN DDoS Mitigation Project Bootstrapper
# Note: This is a convenience script. Individual components can be run manually.
# ==============================================================================

echo "========================================="
echo "   SDN DDoS Project Bootstrapper         "
echo "========================================="

echo "1) Start Mininet Topology (Requires sudo)"
echo "2) Start Ryu Controller"
echo "3) Start Flask API"
echo "4) Start React Dashboard"
echo "5) Exit"
echo ""
read -p "Select a component to run: " choice

case $choice in
    1)
        echo "Starting Mininet Topology..."
        if [ -f "network/topo.py" ]; then
            sudo python3 network/topo.py
        else
            echo "Error: network/topo.py not found."
        fi
        ;;
    2)
        echo "Starting Ryu Controller..."
        if [ -d "ryu-env" ]; then
            source ryu-env/bin/activate
        fi
        ryu-manager controller/simple_monitor.py
        ;;
    3)
        echo "Starting Flask API..."
        if [ -d "ryu-env" ]; then
            source ryu-env/bin/activate
        fi
        cd backend_api && python3 app.py
        ;;
    4)
        echo "Starting React Dashboard..."
        cd dashboard && npm run dev
        ;;
    5)
        exit 0
        ;;
    *)
        echo "Invalid choice."
        ;;
esac
