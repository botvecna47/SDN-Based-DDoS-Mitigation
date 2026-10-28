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

### 1.2 Class Diagram (Backend & ML)
Shows the object-oriented structure of the Controller and API layer.

```mermaid
classDiagram
    class RyuControllerApp {
        +mac_to_port: dict
        +monitor_thread: Thread
        +__init__()
        +packet_in_handler(ev)
        +flow_stats_reply_handler(ev)
        +request_stats()
        +push_drop_rule(ip_src)
    }

    class MLDetector {
        -model: RandomForestClassifier
        -scaler: StandardScaler
        +load_model(filepath)
        +extract_features(flow_stats)
        +predict(features): boolean
    }

    class FlowLogger {
        +filepath: string
        +log_to_csv(stats_dict)
    }

    class FlaskAPI {
        +state_manager: StateManager
        +get_network_stats(): JSON
        +get_blocked_ips(): JSON
    }

    class StateManager {
        +current_pps: int
        +status: string
        +blocked_ips: list
        +update_state(new_data)
    }

    RyuControllerApp --> FlowLogger : "Logs raw stats"
    RyuControllerApp --> MLDetector : "Passes stats for inference"
    RyuControllerApp --> StateManager : "Updates memory state"
    FlaskAPI --> StateManager : "Reads memory state"
```

### 1.3 Deployment Diagram
Maps software components to virtual/physical hardware.

```mermaid
flowchart TD
    subgraph Host["Host Machine (Windows/Mac)"]
        Browser["Web Browser\n(React UI)"]
        
        subgraph VM["Ubuntu VM (Hypervisor)"]
            subgraph Mininet["Mininet Virtual Sandbox"]
                h1["h1 (User)"]
                h2["h2 (Attacker)"]
                h3["h3 (Server)"]
                s1["s1 (OVS Switch)"]
            end
            
            subgraph ControllerNode["Controller Process"]
                Ryu["Ryu Controller (Port 6653)"]
                ML["ML Engine (.joblib)"]
            end
            
            subgraph APINode["API Process"]
                Flask["Flask App (Port 5000)"]
            end
        end
    end

    Browser <-->|HTTP GET| Flask
    Flask <-->|IPC / State| Ryu
    s1 <-->|OpenFlow 1.3| Ryu
    h1 --> s1
    h2 --> s1
    s1 --> h3
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
