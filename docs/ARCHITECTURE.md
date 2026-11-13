# System Architecture

This document describes the implemented architecture of the SDN DDoS Mitigation project.

## 1. Overview

| Layer | Description |
|---|---|
| **Network (Mininet)** | Emulated environment with 1 switch (s1) and 3 hosts (h1, h2, h3). Handles raw traffic generation. |
| **Control (Ryu)** | OpenFlow 1.3 controller polling switch stats every 1.5s. Manages MAC learning and attack detection. |
| **Detection (ML/Threshold)** | Ryu classifies each IPv4 source/destination flow using `detector.joblib` when present, otherwise the shared 10,000 PPS per-flow fallback. |
| **Backend (Flask + IPC)** | Flask API serving JSON state to the frontend. IPC is via `shared_state.json` modified by Ryu. |
| **Frontend (React)** | Root TypeScript React dashboard polls state every 1s in Live mode; Demo mode is self-contained and does not imply backend connectivity. |

## 2. High-Level Component Diagram

```mermaid
flowchart TD
    subgraph VM["🐧 Ubuntu Virtual Machine (192.168.x.x)"]
        subgraph Mininet["🌐 Mininet Emulation Sandbox (network/topo.py)"]
            H1["👤 Host h1 (10.0.0.1)\nLegitimate User (iperf client)"]
            H2["🥷 Host h2 (10.0.0.2)\nAttacker (hping3 UDP flood)"]
            H3["🎯 Host h3 (10.0.0.3)\nTarget Web/App Server (iperf -s -u)"]
            S1{{"⚡ Switch s1 (Open vSwitch)\nOpenFlow 1.3 Kernel Datapath"}}
            
            H1 ---|"Port 1 (s1-eth1)"| S1
            H2 ---|"Port 2 (s1-eth2)"| S1
            S1 ---|"Port 3 (s1-eth3)"| H3
        end
        
        subgraph Controller["🧠 SDN Control Plane"]
            Ryu["🛡️ Ryu Controller App\n(controller/simple_monitor.py)\nListens on TCP :6653"]
            Inference["🔍 Inference Engine\n(controller/inference_loader.py)\nRandomForest / PPS > 10k Fallback"]
            Mitigation["🚫 Mitigation Engine\n(controller/mitigation.py)\nPriority 65535 FlowMod"]
            Dataset["📊 Dataset Logger\n(controller/traffic_dataset.csv)"]
            
            S1 <-->|"OpenFlow 1.3 (TCP:6653)\nStatsRequest & PacketIn / FlowMod"| Ryu
            Ryu -->|"Flow Telemetry (PPS, BPS, Pkts)"| Inference
            Ryu -->|"Append Raw Flow Samples"| Dataset
            Inference -->|"DDoS Threat Alert"| Mitigation
            Mitigation -->|"Push Priority 65535 DROP"| S1
        end

        subgraph Backend["🔌 Backend State & API Layer"]
            StateFile[("📁 shared_state.json\nThread-Safe FileLock IPC\n(backend_api/state_manager.py)")]
            Flask["🚀 Flask REST API\n(backend_api/app.py)\nServes on TCP :5000"]
            
            Ryu -->|"Write State (Status, PPS, Drops, Threats)"| StateFile
            Flask -->|"Read Current State"| StateFile
        end
    end
    
    subgraph Windows["🖥️ Windows Host Machine"]
        React["⚛️ React Dashboard UI\n(src/App.tsx · Port 5173)\nLive 48s Window & Blocked Threats"]
    end

    React <-->|"HTTP GET /api/network-stats\n(Polled every 1.0s via Native Fetch)"| Flask
    React <-->|"HTTP GET /api/flow-table\n(Inspection Endpoint)"| Flask
```

## 3. Attack Detection Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant S as OVS Switch (s1)
    participant R as Ryu Controller
    participant M as ML / Fallback Engine
    participant SS as shared_state.json
    participant F as Flask API (app.py)
    participant UI as React UI (App.tsx)

    Note over F,UI: Async Frontend Polling Loop (Every 1s)
    loop Every 1 second
        UI->>F: GET /api/network-stats
        F->>SS: Read shared_state (filelock protected)
        SS-->>F: JSON State (current_pps, dropped_pps, threats)
        F-->>UI: 200 OK (Full Telemetry Snapshot)
        UI->>UI: Update 48s Chart, Status Banner & Threats Table
    end

    Note over S,R: Control Plane Statistics Polling Loop (Every 1.5s)
    loop Every 1.5 seconds
        R->>S: OFPFlowStatsRequest(datapath)
        S-->>R: OFPFlowStatsReply(body=[flow_stats...])
        R->>R: Calculate Δpackets / Δtime = PPS per flow
        
        alt Flow matches IPv4 Source & Destination
            R->>M: predict(pps, bps, duration, packets)
            M-->>R: is_ddos=True (PPS > 10,000 threshold or ML alert)
            R->>R: Log alert: DDoS Detected from 10.0.0.2
            R->>S: OFPFlowMod(priority=65535, match=10.0.0.2, actions=[DROP], idle_timeout=300)
            R->>SS: update_state(status="UNDER_ATTACK", blocked_ips=["10.0.0.2"])
        end
    end

    Note over S,R: Rule Expiration Handshake (After 300s of inactivity)
    S-->>R: EventOFPFlowRemoved(match=10.0.0.2, reason=IDLE_TIMEOUT)
    R->>R: Discard 10.0.0.2 from active blocklist
    R->>SS: update_state(blocked_ips=[], status="NORMAL")
```

## 4. Data Flow: Packets to Dashboard

```mermaid
flowchart LR
    Packets["📦 Raw Packets\n(h1 iperf + h2 hping3)"] --> OVS["⚡ OVS Switch (s1)\nKernel Hardware/Software Counters"]
    OVS -->|"OFPFlowStatsReply\n(packet_count, byte_count)"| Ryu["🧠 Ryu Controller\nRate Delta Engine (pps, bps)"]
    Ryu -->|"DDoS Classification & Metrics"| IPC[("📁 shared_state.json\nAtomic FileLock IPC")]
    IPC -->|"Fast In-Memory Read"| Flask["🚀 Flask REST API\nTransforms to UI Schema"]
    Flask -->|"HTTP JSON Payload\n(Ingress, Dropped, Threats)"| Dashboard["⚛️ React Dashboard\nReal-Time 3-Curve Chart"]
```

## 5. Network Topology

```mermaid
graph TB
    subgraph MininetTopology["🌐 Mininet SDN Topology (OpenFlow 1.3)"]
        s1{{"⚡ s1: Open vSwitch\nDPID: 0000000000000001"}}
        
        h1["👤 h1: Legitimate User\nIP: 10.0.0.1 · MAC: 00:00:00:00:00:01\nPort: s1-eth1 (1)"]
        h2["🥷 h2: Malicious Attacker\nIP: 10.0.0.2 · MAC: 00:00:00:00:00:02\nPort: s1-eth2 (2)"]
        h3["🎯 h3: Target Server\nIP: 10.0.0.3 · MAC: 00:00:00:00:00:03\nPort: s1-eth3 (3)"]

        h1 -->|"1 Mbps UDP Stream (~85 pkts/s)"| s1
        h2 -->|"Volumetric Flood (~24,000 pkts/s)"| s1
        s1 -->|"Filtered Clean Traffic"| h3
    end

    classDef switch fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#0f172a;
    classDef legit fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a;
    classDef attack fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#0f172a;
    classDef server fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#0f172a;

    class s1 switch;
    class h1 legit;
    class h2 attack;
    class h3 server;
```
*Note: On startup, `net.pingAll()` auto-runs for MAC learning, and iperf server auto-starts on h3. The API uses the switch connection as a readiness signal; it does not independently probe the three hosts.*

## 6. System State Machine

```mermaid
stateDiagram-v2
    [*] --> NORMAL : Controller & Switch Connect

    state NORMAL {
        [*] --> BaselineFlows
        BaselineFlows : Legitimate traffic forwarded (~85 pkts/s)
        BaselineFlows : Priority 1 forward rules active
    }

    NORMAL --> UNDER_ATTACK : Single flow PPS > 10,000 or ML Alert
    
    state UNDER_ATTACK {
        [*] --> MitigationActive
        MitigationActive : Priority 65535 DROP installed for 10.0.0.2
        MitigationActive : Dropped packets increment on s1
        MitigationActive : Clean traffic continues to 10.0.0.3
    }

    UNDER_ATTACK --> MITIGATED_RETAINED : Flood stops (PPS falls < 5,000)
    
    state MITIGATED_RETAINED {
        [*] --> RuleRetained
        RuleRetained : Status returns to NORMAL
        RuleRetained : Attacker IP retained in table under 300s idle timeout
    }

    MITIGATED_RETAINED --> NORMAL : Switch fires EventOFPFlowRemoved (300s idle)
    MITIGATED_RETAINED --> UNDER_ATTACK : Attacker re-floods before timeout
```

## 7. OpenFlow Rule Priority Hierarchy

```mermaid
flowchart TD
    P["📦 Packet Enters Switch s1"] --> MatchHighest{"Check Priority 65535\n(Mitigation Table)"}
    
    MatchHighest -->|"Match: ipv4_src=10.0.0.2"| ActionDrop["🚫 Action: CLEAR_ACTIONS\n(Instant Hardware DROP)\nAttacker Blocked!"]
    MatchHighest -->|"No Match"| MatchNormal{"Check Priority 1\n(Normal Forwarding)"}
    
    MatchNormal -->|"Match: in_port, eth_dst"| ActionForward["✅ Action: OUTPUT to Port\nLegitimate Packet Delivered to h3!"]
    MatchNormal -->|"No Match (New MAC/IP)"| MatchMiss{"Priority 0\n(Table-Miss Rule)"}
    
    MatchMiss -->|"Match: All (*)"| ActionController["📬 Action: CONTROLLER\nSend OFPPacketIn to Ryu for MAC learning"]
```

## 7. Component Responsibilities

| Component | File Path | Role |
|---|---|---|
| Ryu App | `controller/simple_monitor.py` | Core SDN logic, OF polling every 1.5s, triggering state updates. |
| Mitigation | `controller/mitigation.py` | Installs DROP rules (priority=65535, idle=300s, no hard timeout); OVS flow-removal events clear expired blocked rows. |
| Flask API | `backend_api/app.py` | Exposes REST endpoints serving data from IPC state. |
| State | `backend_api/shared_state.json` | Runtime-generated IPC state shared with Flask under a file lock. |
| React UI | `src/App.tsx` | Visualizes state, handles smooth 48-point charts and threats table. |

*Last Updated: 2026-10-28*
