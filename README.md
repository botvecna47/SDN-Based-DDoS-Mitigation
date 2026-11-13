# SDN DDoS Mitigation Project

A comprehensive Software-Defined Networking (SDN) project that detects and mitigates Distributed Denial of Service (DDoS) attacks in real-time. Designed for an academic setting, this system utilizes a Ryu controller to collect OpenFlow statistics, applies Machine Learning (with a robust threshold fallback) to identify malicious traffic, immediately installs blocking rules on an OVS switch, and visualizes the network state on a React dashboard.

## Architecture Diagram

```mermaid
flowchart TD
    subgraph WindowsHost["🖥️ Windows Host Machine"]
        RD["⚛️ React Dashboard UI\n(App.tsx · Port 5173)"]
        Browser["🌐 User Web Browser\n(http://localhost:5173)"]
        RD <--> Browser
    end

    subgraph UbuntuVM["🐧 Ubuntu Linux Guest VM (192.168.x.x)"]
        subgraph MininetSandbox["🌐 Mininet Network Sandbox (network/topo.py)"]
            H1["👤 h1: Legitimate User\n(IP: 10.0.0.1 · MAC: ...01)"]
            H2["🥷 h2: Malicious Attacker\n(IP: 10.0.0.2 · MAC: ...02)"]
            H3["🎯 h3: Target Server\n(IP: 10.0.0.3 · iperf UDP:5001)"]
            S1{{"⚡ s1: Open vSwitch (OVS)\n(OpenFlow 1.3 Datapath)"}}
            
            H1 -->|Legitimate UDP Traffic| S1
            H2 -->|"hping3 Flood Attack"| S1
            S1 -->|Forwarded Safe Packets| H3
        end

        subgraph ControlPlane["🧠 Control & Detection Plane"]
            Ryu["🛡️ Ryu SDN Controller\n(controller/simple_monitor.py · Port 6653)"]
            ML["🔍 Anomaly Detection Engine\n(Random Forest / PPS > 10k Fallback)"]
            Mitigation["🚫 OpenFlow Mitigation Engine\n(controller/mitigation.py)"]
            
            Ryu <-->|Flow Statistics Request / Reply| S1
            Ryu -->|Traffic Features| ML
            ML -->|Attack Alert: 10.0.0.2| Ryu
            Ryu -->|Trigger Block| Mitigation
            Mitigation -->|"OFPFlowMod: Priority 65535 DROP"| S1
        end

        subgraph BackendAPI["🔌 Backend State & API Layer"]
            StateFile[("📁 shared_state.json\n(Thread-Safe IPC via FileLock)")]
            Flask["🚀 Flask REST API\n(backend_api/app.py · Port 5000)"]
            
            Ryu -->|Atomic State Updates| StateFile
            Flask -->|Read Telemetry| StateFile
        end
    end

    RD <-->|"HTTP REST (GET /api/network-stats)\nPolling every 1 second"| Flask

    classDef hostStyle fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a;
    classDef attackerStyle fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#0f172a;
    classDef switchStyle fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#0f172a;
    classDef controllerStyle fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#0f172a;
    classDef storageStyle fill:#f1f5f9,stroke:#475569,stroke-width:2px,color:#0f172a;
    classDef uiStyle fill:#ecfdf5,stroke:#059669,stroke-width:2px,color:#0f172a;

    class H1,H3 hostStyle;
    class H2 attackerStyle;
    class S1 switchStyle;
    class Ryu,ML,Mitigation controllerStyle;
    class StateFile storageStyle;
    class RD,Browser,Flask uiStyle;
```

### Real-Time Mitigation Flow

```mermaid
flowchart LR
    A["🥷 Attacker (h2)\nFloods ~24,000 pkts/s"] -->|Hostile Flood| S["⚡ Switch (s1)"]
    U["👤 User (h1)\nNormal ~85 pkts/s"] -->|Safe Requests| S

    S -->|1.5s Flow Stats| R["🧠 Ryu Controller"]
    R -->|Rate > 10k PPS| D{"⚠️ DDoS Detected?"}
    
    D -->|YES: Attacker 10.0.0.2| P["🚫 Push Priority 65535 DROP"]
    P -->|OFPFlowMod| S

    S -.->|10.0.0.2 Blocked at Port| X["❌ 600k Packets DROPPED"]
    S ===>|10.0.0.1 Forwarded Smoothly| V["🎯 Victim Server (h3)\n100% Online & Protected"]
```

## Quick Start

### Ubuntu VM (Backend & Network)
Open 4 separate terminals and run:

**Terminal 1 (Ryu Controller):**
```bash
source ryu39_env/bin/activate
ryu-manager controller/simple_monitor.py
```

**Terminal 2 (Flask API):**
```bash
source ryu39_env/bin/activate
cd backend_api
python3 app.py
```

**Terminal 3 (Mininet):**
```bash
sudo mn -c
sudo python3 network/topo.py
```

### Windows Host (Frontend)
Open 1 terminal in the project root:

```powershell
npm install
npm run dev
```

The dashboard starts in Demo mode for presentations. To use VMware telemetry, configure `VITE_DEFENSE_API_URL` in `.env`, restart Vite, and select **Live** after the Flask API and Mininet switch are running.

## Project Structure

```text
DDoS Mitigation/
├── backend_api/
│   ├── app.py                 # Flask REST API reading shared state
│   └── shared_state.json      # Generated at runtime; ignored by Git
├── controller/
│   ├── simple_monitor.py      # Ryu app polling stats & driving logic
│   ├── mitigation.py          # Pushes OpenFlow DROP rules to switch
│   ├── inference_loader.py    # Loads ML model / threshold logic
│   └── traffic_dataset.csv    # Live traffic logging for datasets
├── docs/                      # Documentation folder
├── ml_pipeline/               # Scripts and notebooks for ML training
├── network/
│   ├── topo.py                # Mininet topology script (h1, h2, h3, s1)
│   └── *.sh                   # Traffic generation scripts
├── src/                       # React frontend source code (App.tsx, etc.)
└── README.md                  # This file
```

The root `src/` dashboard is the runnable frontend. `dashboard/` is an old placeholder and `CybersecurityDashboardUIUX/` is a separate design submodule; neither is started by the root Vite app.

## How It Works

1. **Traffic Generation:** Mininet orchestrates endpoints. Legitimate traffic flows from `h1`, while attack traffic is flooded from `h2` towards `h3`.
2. **Statistics Collection:** The Ryu controller (`simple_monitor.py`) queries the OVS switch (`s1`) for flow statistics every 1.5 seconds.
3. **Detection:** Ryu classifies each observed IPv4 source/destination flow using the provided model when available, with a 10,000 packets/sec per-flow threshold fallback when it is not. The API only observes the OVS switch connection; it does not independently probe host reachability.
4. **Mitigation & Visualization:** Upon detection, Ryu instructs `mitigation.py` to push a high-priority DROP rule to `s1`. Simultaneously, Ryu updates `shared_state.json`. Flask serves this updated state to the React dashboard, dynamically painting the UI red.

## Configuration

To configure the dashboard to point to your specific Ubuntu VM IP:
1. Copy `.env.example` to `.env` in the root directory.
2. Edit `.env` to set `VITE_DEFENSE_API_URL` to your Flask endpoint, e.g., `http://192.168.8.147:5000/api/network-stats`.

## Documentation Index

| Document | Description |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Deep dive into system components, data flows, and state logic. |
| [API Schema](docs/API_SCHEMA.md) | Contract for the Flask REST API endpoints and data models. |
| [Demo Script](docs/DEMO_SCRIPT.md) | Step-by-step guide to showcasing the project in a presentation. |

`docs/BACKEND_PLAN.md`, `docs/TEAM_PLAN.md`, `docs/SDLC_PHASES.md`, and `docs/SRS.md` are planning/requirements records; some describe earlier designs. Use the running guide, architecture, and API schema above for current launch steps and runtime behavior.

## Team

| Role | Responsibility |
|---|---|
| **Lead** | Backend Architecture & Machine Learning Pipelines |
| **Friend 1** | Network Topology & Ryu Controller Logic |
| **Friend 2** | React Frontend Dashboard & Quality Assurance |

## Current Status

- **Implemented:** Mininet topology, Ryu controller, IPC state sharing, Flask API, React dashboard, and OpenFlow mitigation rules. Confirm live operation on the VMware setup before presenting it as verified.
- **Pending:** `ml_pipeline/detector.joblib` is not included. Ryu uses the 10,000 PPS per-flow fallback until a compatible model is supplied. Run the training notebook with `ml_pipeline/notebooks` as its working directory; it writes to the path Ryu loads.

*Last Updated: 2026-10-28*
