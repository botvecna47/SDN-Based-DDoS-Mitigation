# Academic UML Diagrams & Risk Management
## SDN-Based DDoS Detection and Mitigation System

This document supplements the core architecture with formal UML diagrams and risk analysis typically required for academic evaluations and rigorous software engineering standards.

---

## 1. Additional UML Diagrams

### 1.1 Use Case Diagram
Maps the external actors to the system's core capabilities.

```mermaid
flowchart LR
    %% Actors
    Admin(["🧑‍💻 Network Admin"])
    LegitUser(["👤 Legitimate User"])
    Attacker(["🥷 Attacker"])

    %% System Boundary
    subgraph System["SDN Defense System Boundary"]
        UC1(["View Live Telemetry"])
        UC2(["View Blocked IPs"])
        UC3(["Access Web Server"])
        UC4(["Flood Network"])
        UC5(["Detect Anomalies (ML)"])
        UC6(["Push Drop Rules (SDN)"])
    end

    %% Connections
    Admin --> UC1
    Admin --> UC2
    
    LegitUser --> UC3
    Attacker --> UC4
    
    UC4 -.->|Triggers| UC5
    UC5 -.->|Invokes| UC6
    UC6 -.->|Blocks| Attacker
    UC6 -.->|Protects| UC3
```

### 1.2 Class Diagram (Backend, Controller & ML Architecture)
Shows the object-oriented structure and module interfaces of the SDN Controller, Inference Engine, and Backend API.

```mermaid
classDiagram
    class SimpleMonitor13 {
        +mac_to_port: dict
        +datapaths: dict
        +blocked_ips: set
        +flow_history: dict
        +detector: DDoSDetector
        +monitor_thread: hub.spawn
        +__init__()
        +state_change_handler(ev)
        +flow_removed_handler(ev)
        +switch_features_handler(ev)
        +add_flow(datapath, priority, match, actions)
        +packet_in_handler(ev)
        +_monitor()
        +_request_stats(datapath)
        +_flow_stats_reply_handler(ev)
        +_run_inference(stats_dict, datapath)
        +_log_to_csv(stats_dict)
    }

    class DDoSDetector {
        +model: RandomForestClassifier
        +is_loaded: boolean
        +__init__(model_path)
        +predict(pps, bps, duration_sec, packet_count): tuple
    }

    class MitigationEngine {
        +push_drop_rule(datapath, src_ip)
        +push_rate_limit_rule(datapath, src_ip, rate_kbps)
    }

    class StateManager {
        +STATE_FILE_PATH: string
        +FALLBACK_THRESHOLD_PPS: int
        +initialize_state(): dict
        +read_state(): dict
        +update_state(kwargs): dict
    }

    class FlaskAPI {
        +network_stats(): Response
        +flow_table(): Response
        +health(): Response
        +add_no_cache_headers(response)
    }

    class ReactDashboard {
        +source: "demo" | "live"
        +demoMode: DemoMode
        +snapshot: Snapshot
        +fetchSnapshot(signal): Promise
        +TrafficChart(traffic)
        +MetricCard(label, value)
    }

    SimpleMonitor13 --> DDoSDetector : "Invokes predict() on flow delta"
    SimpleMonitor13 --> MitigationEngine : "Calls push_drop_rule() on attack"
    SimpleMonitor13 --> StateManager : "Writes telemetry via update_state()"
    FlaskAPI --> StateManager : "Reads state via read_state()"
    ReactDashboard --> FlaskAPI : "Polls GET /api/network-stats"
```

### 1.3 Deployment Diagram
Maps software components to virtual/physical hardware and network boundaries.

```mermaid
flowchart TD
    subgraph WindowsHost["🖥️ Host Machine (Windows 11)"]
        Browser["🌐 Web Browser\n(Google Chrome / Edge)"]
        ViteServer["⚡ Vite React Dev Server\n(localhost:5173 · Node.js)"]
        Browser <-->|"Render DOM & SVG Charts"| ViteServer
    end

    subgraph VMware["📦 VMware Workstation / Hypervisor"]
        subgraph UbuntuVM["🐧 Guest OS: Ubuntu Linux (Bridged IP: 192.168.x.x)"]
            subgraph ControllerProc["Ryu Controller Process (Python 3.9 venv)"]
                Ryu["🛡️ Ryu SDN Controller (:6653)\n(controller/simple_monitor.py)"]
                Detector["🧠 DDoS Detector (Inference / Fallback)\n(controller/inference_loader.py)"]
                CSV["📊 Dataset Logger\n(controller/traffic_dataset.csv)"]
                Ryu --- Detector
                Ryu --- CSV
            end

            subgraph BackendProc["Flask Web Service Process (Python 3.9 venv)"]
                Flask["🚀 Flask REST API (:5000)\n(backend_api/app.py)"]
                IPC[("📁 shared_state.json\n(Atomic FileLock)")]
                Flask <--> IPC
            end

            subgraph MininetSandbox["Mininet Virtual Network Namespace"]
                H1["👤 Host h1 (10.0.0.1)\nLegitimate Client"]
                H2["🥷 Host h2 (10.0.0.2)\nAttacker"]
                H3["🎯 Host h3 (10.0.0.3)\nTarget Server (UDP 5001)"]
                S1{{"⚡ Switch s1\nOpen vSwitch Kernel Switch"}}
                
                H1 ---|"veth pair"| S1
                H2 ---|"veth pair"| S1
                S1 ---|"veth pair"| H3
            end
        end
    end

    ViteServer <-->|"HTTP REST (TCP :5000)\nCross-Origin Requests"| Flask
    Ryu -->|"Thread-safe IPC Write"| IPC
    S1 <-->|"OpenFlow 1.3 (TCP :6653)\nStatsRequest & FlowMod"| Ryu
```

### 1.4 Visual Project Timeline (Gantt Chart)

```mermaid
gantt
    title 12-Week Project Execution Plan
    dateFormat  YYYY-MM-DD
    axisFormat  Week %W
    
    section Phase 1 (45%)
    VM & Mininet Setup       :a1, 2026-10-01, 14d
    Ryu Poller & CSV Logger  :a2, 2026-10-01, 28d
    React UI Skeleton        :a3, 2026-10-01, 28d
    Traffic Scripts (hping3) :a4, 2026-10-15, 14d

    section Phase 2 (70%)
    Data Labeling & EDA      :b1, 2026-10-29, 14d
    Train RandomForest Model :b2, 2026-11-05, 14d
    Flask API Integration    :b3, 2026-11-12, 14d
    React Live Data Hookup   :b4, 2026-11-12, 14d

    section Phase 3 (100%)
    Live ML Inference Engine :c1, 2026-11-26, 14d
    Multi-vector Attack Test :c2, 2026-12-03, 14d
    Benchmark & Final Polish :c3, 2026-12-10, 14d
    Demo Rehearsal & Docs    :c4, 2026-12-17, 7d
```

---

## 2. Risk Management & Threat Model

### 2.1 Technical Risks
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| **Control Plane Saturation:** The flood of OpenFlow `Packet-In` messages overwhelms the Ryu controller before rules are pushed. | High | Critical | Implement proactive flow polling instead of relying solely on reactive `Packet-In` events. Limit polling frequency to 1.5s to save CPU. |
| **Model False Positives:** Legitimate heavy traffic (e.g., a file download) is misclassified as a DDoS attack. | Medium | High | Fine-tune the RandomForest threshold; ensure the dataset contains normal traffic bursts. Implement an auto-timeout for blocked IPs so false positives eventually recover. |
| **VM Resource Exhaustion:** Mininet, Ryu, Flask, and React running on one VM causes memory swapping and crashes. | Medium | High | Allocate minimum 4GB RAM / 2 vCPUs to the Ubuntu VM. Run the React frontend on the Host machine instead of the VM to save memory. |

### 2.2 Project Management Risks
| Risk Description | Mitigation Strategy |
|---|---|
| **Member Drops Out / Is Blocked:** | The `TEAM_PLAN.md` isolates dependencies through API contracts (`mockData.json`). If the backend is delayed, the frontend can still build UI. If ML is delayed, manual thresholds can trigger the mitigation rules as a fallback. |
| **ML Model Accuracy is Low:** | Switch to a simpler Decision Tree or a static math-based threshold (PPS > X) to ensure the system is demonstrable, then optimize ML later. |
