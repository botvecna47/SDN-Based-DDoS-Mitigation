# Product Requirements Document
## SDN-Based DDoS Detection and Mitigation System

---

| Field        | Details                                      |
|--------------|----------------------------------------------|
| **Version**  | 1.0                                          |
| **Date**     | September 24, 2026                           |
| **Team**     | 3-Member Student Team                        |
| **Status**   | Draft                                        |
| **Reviewers**| Team Lead, Project Supervisor                |

---

## 1. Problem Statement

A Distributed Denial-of-Service (DDoS) attack floods a target server with an overwhelming volume of network traffic — often millions of packets per second — rendering it unable to respond to legitimate users. Traditional firewall rules are static and manually configured, meaning that by the time a human operator identifies an attack and applies a block rule, significant damage has already been done: services are disrupted, users are locked out, and reputation damage accumulates. Worse, the block is applied too far downstream, at the server's own network interface, after the congestion has already propagated through the network.

We need a **smart traffic cop** that lives in the network itself. This system must continuously watch all traffic flows, decide in near-real-time whether a flow is malicious or legitimate using a trained machine-learning model, and automatically push drop rules directly to the SDN switch — blocking the attack at the data plane before a single malicious packet ever reaches the server. The entire detect-and-mitigate loop must close in under 3 seconds, with no human in the loop.

**Real-world impact of the problem:**
- Average DDoS attack causes **$218,000/hour** in downtime for enterprises (Corero 2022 report).
- 47% of DDoS attacks last less than 10 minutes — too fast for human-driven mitigation.
- Traditional mitigation solutions (commercial scrubbing centres) cost thousands of dollars per month, making them inaccessible for small organisations.
- SDN-based automatic mitigation can reduce reaction time from minutes to seconds, dramatically reducing blast radius.

---

## 2. Solution Overview

The system is built as a 5-layer stack, each layer with a well-defined responsibility:

**Layer 1 — Virtual Network (Mininet / Open vSwitch):** Mininet emulates a realistic network topology consisting of three hosts and one software switch (OVS). Host `h1` (10.0.0.1) simulates legitimate traffic, host `h2` (10.0.0.2) simulates an attacker firing a high-rate flood, and host `h3` (10.0.0.3) acts as the victim server. Open vSwitch provides a full OpenFlow 1.3-capable data plane that can receive and enforce flow modification instructions from the controller. This layer makes the entire experiment reproducible on a single Ubuntu VM with no physical hardware.

**Layer 2 — Control Layer (Ryu SDN Controller):** The Ryu controller runs as an OpenFlow 1.3 controller, maintaining persistent connections to all switches in the topology. Every 1–2 seconds it proactively sends `OFPFlowStatsRequest` messages to the switch and collects per-flow statistics (packet counts, byte counts, durations). This layer acts as the network's "nervous system," providing a real-time telemetry feed of everything happening on the wire. When the Intelligence Layer signals an attack, Ryu immediately pushes an `OFPFlowMod` with a maximum-priority drop action to the switch, cutting off the attack source at line rate.

**Layer 3 — Intelligence Layer (ML Random Forest):** A scikit-learn `RandomForestClassifier`, pre-trained on labelled flow data, sits inside the Ryu controller process. For every flow record collected from the switch, the model receives four derived features — packets-per-second (PPS), bytes-per-second (BPS), flow duration, and raw packet count — and returns a binary label: `0` for Normal or `1` for DDoS. Random Forest was chosen for its high accuracy on tabular network-flow data, resistance to overfitting on small datasets, and sub-millisecond inference latency, all of which are essential for real-time operation.

**Layer 4 — API Layer (Flask REST):** A lightweight Flask application serves as the bridge between the controller's internal state and the outside world. It exposes two endpoints: `GET /api/network-stats` (live PPS, active flow count, blocked IP count, controller uptime) and `GET /api/blocked-ips` (timestamped list of every IP that has been blocked, with the reason and PPS at detection time). Flask-CORS is configured to allow requests from the React development server (`http://localhost:5173`). This layer decouples the UI completely from the controller internals.

**Layer 5 — Presentation Layer (React Dashboard):** A React 18 single-page application provides the human-facing view of the system. It polls both Flask endpoints every second and renders a rolling 30-second PPS line chart (via Recharts), a colour-coded status badge (`NORMAL` / `UNDER_ATTACK` / `MITIGATING`), and a live blocked-IP table. The dashboard requires zero backend code knowledge to operate — a non-technical network admin can watch the entire attack-detect-mitigate cycle play out in real time from a browser tab.

---

## 3. User Personas

### Persona A — Network Administrator / Developer

| Attribute      | Detail                                                                 |
|----------------|------------------------------------------------------------------------|
| **Name**       | Priya (or any team member during demo)                                 |
| **Role**       | Human operator monitoring the system                                   |
| **Goals**      | See current network health at a glance; review which IPs are blocked; confirm that legitimate traffic is unaffected |
| **Pain Points**| Doesn't want to read raw controller logs; needs a clean, real-time UI  |
| **Actions**    | Opens the React dashboard in a browser; watches the PPS chart; inspects the blocked-IP table after an attack |

### Persona B — The Autonomous System (Non-Human Actor)

| Attribute      | Detail                                                                      |
|----------------|-----------------------------------------------------------------------------|
| **Name**       | The DDoS Mitigation Pipeline                                                |
| **Role**       | Automated detect-and-block actor                                            |
| **Goals**      | Continuously poll flow stats → classify each flow → push drop rules instantly when a DDoS is detected |
| **Pain Points**| Must operate with zero human latency; must not block legitimate traffic     |
| **Actions**    | Every 1–2s: collects stats → runs ML inference → (if attack) pushes `OFPFlowMod` → logs block event to Flask state |

---

## 4. Core Features (MoSCoW)

| Feature | Priority | Owner | Description |
|---------|----------|-------|-------------|
| Virtual network topology (Mininet h1/h2/h3/s1) | **MUST** | Team | Emulated 3-host, 1-switch topology running on a single Ubuntu VM via Mininet + OVS |
| Flow statistics collection (OFPFlowStatsRequest) | **MUST** | Team | Ryu controller polls OVS every 1–2s and aggregates per-flow counters |
| ML-based attack detection (Random Forest) | **MUST** | Team | Trained classifier runs inference on every collected flow; labels flows 0/1 |
| OpenFlow drop rules (OFPFlowMod, priority 65535) | **MUST** | Team | On DDoS detection, controller pushes a maximum-priority drop rule to OVS |
| Flask REST API (/api/network-stats, /api/blocked-ips) | **MUST** | Team | Two GET endpoints exposing live controller state as JSON |
| React dashboard with PPS chart and blocked-IP table | **MUST** | Team | Browser UI with live polling, chart, status badge, and blocked-IP list |
| Multi-vector detection (SYN flood, UDP flood, ICMP flood) | **SHOULD** | Team | Extend training data and feature set to handle multiple attack types |
| Rolling 30-second PPS chart with smooth animation | **SHOULD** | Team | Chart auto-scrolls and retains last 30 data points for trend visibility |
| Graceful "Controller Offline" handling in the UI | **SHOULD** | Team | Toast notification when Flask API is unreachable; UI does not crash |
| Rate-limiting rules instead of hard drops (for borderline flows) | **NICE TO HAVE** | Team | Push meter-based rate-limit rules for flows near the detection threshold |
| Benchmark CSV export from the dashboard | **NICE TO HAVE** | Team | One-click download of the attack-session stats for academic reporting |
| Alert email on DDoS detection | **NICE TO HAVE** | Team | Send an email via SMTP when the system transitions to UNDER_ATTACK state |

---

## 5. Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Detection latency (attack start to OFPFlowMod pushed) | **< 3 seconds** | Timestamp delta between first malicious packet and controller log entry showing block rule insertion |
| Attack traffic reduction post-mitigation | **> 95%** | Compare PPS on h3's interface before and after the drop rule is applied (Wireshark / iperf counters) |
| Legitimate user packet loss during active attack | **< 5%** | Run legit_traffic.sh concurrently with attack; measure h1-to-h3 throughput drop |
| ML false positive rate (legitimate traffic classified as DDoS) | **< 2%** | Evaluate classifier on held-out test set; compute FPR from confusion matrix |
| ML inference latency per flow | **< 5 ms** | Time model.predict() calls over 1,000 flows; record p99 latency |
| React dashboard render frame rate during traffic spike | **60 FPS** | Chrome DevTools Performance panel during active attack simulation |
| Ryu controller stability over 30-minute stress test | **0 crashes** | Run full attack scenario for 30 minutes; check controller process exit code |

---

## 6. Out of Scope

- **Real physical hardware** — the project runs exclusively on Mininet emulation; no physical switches or routers are in scope.
- **IPv6 traffic** — all flow matching and ML features are IPv4-only (`eth_type=0x0800`).
- **Dashboard authentication / authorisation** — the React UI is open (no login, no RBAC) in this academic prototype.
- **Multi-switch topologies** — only a single OVS switch (s1) is considered; spanning-tree or multi-path routing is out of scope.
- **Cloud or container deployment** — the system runs locally on a single Ubuntu VM; Docker, Kubernetes, or cloud providers are not targeted.
- **Persistent storage / database** — blocked-IP state is held in-memory in the Flask process; no SQL or NoSQL database is used.

---

## 7. Assumptions and Constraints

- **Single Ubuntu VM:** The entire stack (Mininet, Ryu, Flask, React) runs on one Ubuntu 20.04 or 22.04 virtual machine. No multi-node deployment is assumed.
- **Academic demo project:** This is a proof-of-concept for educational purposes, not a production-grade system. Reliability and security hardening requirements are relaxed accordingly.
- **Python 3.x runtime:** All backend components (Ryu, Flask, ML training/inference) target Python 3.8+. Python 2 is not supported.
- **Localhost-only networking:** Flask serves on `127.0.0.1:5000` and the React dev server on `localhost:5173`. No external network access is required or assumed.
- **Mininet emulation, not real hardware:** All bandwidth, latency, and PPS numbers are measured within the Mininet simulation environment. Results may differ from real physical deployments.
- **Pre-trained ML model:** The Random Forest model is trained offline on a labelled CSV dataset before the demo. Online/incremental learning is not in scope for v1.0.
- **Single attacker IP:** The attack simulation uses a single source IP (`10.0.0.2`). Multi-source distributed attacks are out of scope for the initial version.
- **Team size:** 3 student members with shared ownership of all components. No dedicated QA or DevOps role.
