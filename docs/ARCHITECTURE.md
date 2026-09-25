# System Architecture
## SDN-Based DDoS Detection and Mitigation System

> **Document Version:** 1.0  
> **Last Updated:** 2026-09-24  
> **Status:** Active

---

## Table of Contents

1. [Overview](#1-overview)
2. [High-Level Component Diagram](#2-high-level-component-diagram)
3. [Attack Detection Sequence Diagram](#3-attack-detection-sequence-diagram)
4. [Data Flow: Packets to Dashboard](#4-data-flow-packets-to-dashboard)
5. [Network Topology](#5-network-topology)
6. [System State Machine](#6-system-state-machine)
7. [Component Responsibilities](#7-component-responsibilities)

---

## 1. Overview

The system is structured as a **5-layer architecture** that separates concerns cleanly, from raw packet forwarding at the bottom to the user-facing dashboard at the top.

| Layer | Name | Role |
|-------|------|------|
| **L1** | **Virtual Network Layer** | Mininet-emulated hosts and Open vSwitch (OVS) switches generate and forward actual network packets. This is where legitimate traffic and attack traffic both originate. |
| **L2** | **Control Layer** | The Ryu SDN Controller communicates with OVS via the OpenFlow 1.3 protocol. It installs, modifies, and removes flow rules in real time — including DROP rules for attacker IPs. |
| **L3** | **Intelligence Layer** | A pre-trained scikit-learn ML model (`detector.joblib`) runs inside the controller process. It periodically polls flow statistics, extracts features, and classifies traffic as Normal or DDoS. |
| **L4** | **API Layer** | A Flask REST API exposes system state (current PPS, blocked IPs, attack status) to any HTTP consumer. It shares in-process state with the Ryu controller. |
| **L5** | **Presentation Layer** | A React + Vite dashboard polls the Flask API every second and renders live charts, attack alerts, and blocked-IP tables for the operator. |

---

## 2. High-Level Component Diagram

```mermaid
flowchart TD
    A["h1 - Legitimate User\n10.0.0.1"] --> C
    B["h2 - Attacker\n10.0.0.2"] --> C
    C["s1 - OVS Switch\nOpenFlow 1.3 Dataplane"] --> D
    C <-->|"OpenFlow 1.3\nControl Channel"| E
    D["h3 - Web Server\n10.0.0.3"]
    E["Ryu SDN Controller\ncontroller.py"] --> F
    E --> G
    E --> H
    F["CSV Logger\ntraffic_log.csv"]
    G["ML Inference Engine\ndetector.joblib"]
    H["Flask REST API\nlocalhost:5000"]
    G -->|"DDoS Detected"| I
    I["OFPFlowMod DROP Rule"] --> C
    H -->|"JSON Polling\nevery 1s"| J
    J["React Dashboard\nlocalhost:5173"]

    style A fill:#4CAF50,color:#fff
    style B fill:#f44336,color:#fff
    style C fill:#2196F3,color:#fff
    style D fill:#4CAF50,color:#fff
    style E fill:#9C27B0,color:#fff
    style F fill:#607D8B,color:#fff
    style G fill:#FF9800,color:#fff
    style H fill:#009688,color:#fff
    style I fill:#f44336,color:#fff
    style J fill:#3F51B5,color:#fff
```

**Key relationships:**
- Both legitimate and attack hosts connect to the same OVS switch `s1`.
- The Ryu controller has **bidirectional** OpenFlow control over `s1` — it can query stats and push flow rules.
- The ML model runs **inside** the controller process (same Python runtime, no IPC needed).
- The Flask API is mounted in the **same Python process** via a background thread, sharing in-process variables with the controller.
- The React dashboard is purely a **consumer** — it reads from the API and never writes to the controller directly.

---

## 3. Attack Detection Sequence Diagram

```mermaid
sequenceDiagram
    participant h2 as h2_Attacker
    participant s1 as s1_Switch
    participant Ryu as Ryu_Controller
    participant ML as ML_Model
    participant API as Flask_API
    participant UI as React_Dashboard

    Note over h2,s1: NORMAL PHASE - Baseline Traffic
    h2->>s1: Normal packets (low rate)
    s1->>Ryu: OFPPacketIn (table-miss)
    Ryu->>s1: OFPFlowMod (install forward rule)

    Note over Ryu,ML: MONITORING PHASE - Every 5 seconds
    Ryu->>s1: OFPFlowStatsRequest
    s1-->>Ryu: OFPFlowStatsReply (byte_count, packet_count)
    Ryu->>ML: extract_features(flow_stats)
    ML-->>Ryu: prediction = NORMAL confidence = 0.97

    Note over h2,s1: ATTACK PHASE - DDoS Begins
    h2->>s1: SYN Flood (high rate 24000+ pps)
    s1->>Ryu: OFPPacketIn (burst)
    Ryu->>s1: OFPFlowStatsRequest
    s1-->>Ryu: OFPFlowStatsReply (anomalous packet_count delta)
    Ryu->>ML: extract_features(flow_stats)
    ML-->>Ryu: prediction = DDoS confidence = 0.99

    Note over Ryu,s1: MITIGATION PHASE - Block Attacker
    Ryu->>Ryu: identify_attacker_ip(flow_stats)
    Ryu->>s1: OFPFlowMod (priority=100, match src=10.0.0.2, action=DROP)
    s1-->>Ryu: ACK (flow installed)
    Ryu->>Ryu: add_to_blocked_list("10.0.0.2")
    Ryu->>Ryu: log_to_csv(event=DDOS_BLOCKED)
    Ryu->>API: update_shared_state(status=MITIGATING)

    Note over API,UI: REPORTING PHASE - Dashboard Updates
    UI->>API: GET /api/network-stats (poll interval 1s)
    API-->>UI: {"status": "MITIGATING", "current_pps": 24500, "blocked_count": 1}
    UI->>API: GET /api/blocked-ips
    API-->>UI: [{"ip": "10.0.0.2", "reason": "DDoS - ML Classification"}]
    UI->>UI: render_alert("DDoS Attack Detected!")
    UI->>UI: update_chart(pps_spike)
    UI->>UI: update_blocked_table()

    Note over h2,s1: RECOVERY PHASE - Attack Stops
    h2->>h2: attacker stops sending
    Ryu->>s1: OFPFlowStatsRequest
    s1-->>Ryu: OFPFlowStatsReply (pps back to normal)
    Ryu->>ML: extract_features(flow_stats)
    ML-->>Ryu: prediction = NORMAL confidence = 0.94
    Ryu->>API: update_shared_state(status=NORMAL)
    UI->>API: GET /api/network-stats
    API-->>UI: {"status": "NORMAL", "current_pps": 260}
    UI->>UI: clear_alert() and show_recovery_toast()
```

---

## 4. Data Flow: Packets to Dashboard

```mermaid
flowchart LR
    A["Raw Packets\nfrom all hosts"] --> B
    B["OVS Flow Table\ns1 dataplane"] --> C
    C["OFPFlowStatsRequest\nevery 5 seconds"] --> D
    D["OFPFlowStatsReply\nbyte_count, packet_count\nduration_sec, match fields"] --> E
    E["Feature Extraction\ncalculate delta_pps\nbytes_per_packet\nflow_duration"] --> F
    F["ML Predict\ndetector.joblib\nRandomForest Classifier"] --> G
    G{"DDoS\nDetected?"}
    G -->|"YES"| H
    G -->|"NO"| I
    H["Install DROP Rule\nOFPFlowMod\npriority=100\nsrc=attacker_ip"] --> J
    I["Continue Forwarding\nExisting flow rules\nremain active"] --> J
    J["Update Shared State\nstatus, pps, blocked_ips\nblocked_count, timestamp"] --> K
    K["Flask REST API\n/api/network-stats\n/api/blocked-ips"] --> L
    L["React Dashboard\nlocalhost:5173\ncharts + tables + alerts"]

    style A fill:#607D8B,color:#fff
    style F fill:#FF9800,color:#fff
    style H fill:#f44336,color:#fff
    style I fill:#4CAF50,color:#fff
    style L fill:#3F51B5,color:#fff
```

---

## 5. Network Topology

```mermaid
graph TB
    subgraph Mininet["Mininet Virtual Network"]
        subgraph Hosts["End Hosts"]
            h1["h1\nIP: 10.0.0.1\nMAC: 00:00:00:00:00:01\nRole: Legitimate User"]
            h2["h2\nIP: 10.0.0.2\nMAC: 00:00:00:00:00:02\nRole: Simulated Attacker"]
            h3["h3\nIP: 10.0.0.3\nMAC: 00:00:00:00:00:03\nRole: Web Server Target"]
        end
        subgraph Dataplane["Dataplane"]
            s1["s1 - Open vSwitch\nDPID: 0000000000000001\nOpenFlow 1.3\nPort 1 to h1\nPort 2 to h2\nPort 3 to h3"]
        end
    end
    subgraph Controller["Control Plane - Host OS"]
        ryu["Ryu Controller\n127.0.0.1:6653\nOpenFlow Listener"]
        ml["ML Engine\ndetector.joblib\nScikit-learn"]
        flask["Flask API\n0.0.0.0:5000\nREST Endpoints"]
        csv["CSV Logger\ntraffic_log.csv"]
    end
    subgraph Frontend["Frontend - Browser"]
        react["React Dashboard\nlocalhost:5173\nVite Dev Server"]
    end

    h1 <-->|"eth port-1"| s1
    h2 <-->|"eth port-2"| s1
    h3 <-->|"eth port-3"| s1
    s1 <-->|"OpenFlow 1.3\nTCP:6653"| ryu
    ryu --> ml
    ryu --> csv
    ryu --> flask
    flask <-->|"HTTP REST\nCORS enabled"| react

    style h1 fill:#4CAF50,color:#fff
    style h2 fill:#f44336,color:#fff
    style h3 fill:#2196F3,color:#fff
    style s1 fill:#607D8B,color:#fff
    style ryu fill:#9C27B0,color:#fff
    style ml fill:#FF9800,color:#fff
    style flask fill:#009688,color:#fff
    style react fill:#3F51B5,color:#fff
```

---

## 6. System State Machine

```mermaid
stateDiagram-v2
    [*] --> NORMAL : Controller starts\nBaseline established

    NORMAL --> UNDER_ATTACK : ML predicts DDoS\nconfidence > 0.90\ncurrent_pps > 3x baseline

    UNDER_ATTACK --> MITIGATING : Attacker IP identified\nOFPFlowMod DROP rule\ninstalled on switch

    MITIGATING --> NORMAL : pps returns to baseline\nML predicts NORMAL\nfor 3 consecutive polls

    MITIGATING --> UNDER_ATTACK : New attacker IP detected\nAdditional DROP rules installed

    NORMAL --> NORMAL : Normal traffic\nML confirms NORMAL\nStats logged to CSV

    UNDER_ATTACK --> UNDER_ATTACK : Attack ongoing\nAwaiting IP identification\nController processing

    note right of NORMAL
        current_pps: 200-350
        blocked_count: 0
        Dashboard: Green status
        API status field: "NORMAL"
    end note

    note right of UNDER_ATTACK
        current_pps: 10000+
        Detection triggered
        Dashboard: Red alert banner
        API status field: "UNDER_ATTACK"
    end note

    note right of MITIGATING
        DROP rule active on s1
        blocked_count >= 1
        Dashboard: Orange warning
        API status field: "MITIGATING"
    end note
```

---

## 7. Component Responsibilities

| Component | Owner | Input | Output | Technology | File / Location |
|-----------|-------|-------|--------|------------|-----------------|
| **Mininet Topology** | Backend Lead | CLI command `sudo python3 topo.py` | Virtual network with h1, h2, h3, s1 | Python, Mininet | `topo.py` |
| **OVS Switch (s1)** | System (auto) | Raw Ethernet frames from hosts | Forwarded/dropped frames; Flow stats to controller | Open vSwitch, OpenFlow 1.3 | Managed by Mininet |
| **Ryu SDN Controller** | Backend Lead | OpenFlow messages from s1 (PacketIn, FlowStatsReply) | OpenFlow commands (FlowMod), shared state updates | Python, Ryu Framework | `controller.py` |
| **ML Inference Engine** | Backend Lead | Feature vector `[delta_pps, bytes_per_pkt, flow_duration]` | Binary label: `"NORMAL"` or `"DDoS"`, confidence score | scikit-learn, joblib | `detector.joblib`, `train_model.py` |
| **CSV Logger** | Backend Lead | Attack/normal events with timestamps, IPs, PPS values | Append-only CSV rows for post-analysis | Python `csv` module | `traffic_log.csv` |
| **Flask REST API** | Backend Lead | HTTP GET requests from frontend | JSON responses: system stats, blocked IPs | Python, Flask, Flask-CORS | `controller.py` (background thread) |
| **React Dashboard** | Frontend Dev | JSON from Flask API (polled every 1 second) | Rendered charts, tables, alerts in browser | React, Vite, Axios, Recharts | `frontend/src/` |
| **Axios Polling Service** | Frontend Dev | API base URL, polling interval config | Parsed JSON stored in React state | Axios, React useEffect | `frontend/src/hooks/useNetworkStats.js` |
| **Mock Data (Phase 1)** | Frontend Dev | `mockData.json` file | Simulated API responses for UI development | JSON | `frontend/src/mockData.json` |
| **Attack Simulator** | Backend Lead | CLI command in Mininet shell: `h2 hping3 ...` | SYN flood packets from 10.0.0.2 to 10.0.0.3 | hping3 / Python scapy | Run from Mininet CLI |
