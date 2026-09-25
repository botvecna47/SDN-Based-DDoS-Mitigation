# Software Requirements Specification
## SDN-Based DDoS Detection and Mitigation System

---

| Field        | Details                                       |
|--------------|-----------------------------------------------|
| **Version**  | 1.0                                           |
| **Date**     | September 24, 2026                            |
| **Team**     | 3-Member Student Team                         |
| **Status**   | Draft                                         |
| **Based On** | PRD v1.0                                      |

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the complete functional and non-functional requirements for the SDN-Based DDoS Detection and Mitigation System. It serves as the authoritative technical reference for the 3-member development team during design, implementation, testing, and demonstration of the system. Every requirement is uniquely identified and traceable to the Product Requirements Document (PRD v1.0).

### 1.2 Scope

The system ingests per-flow network statistics from an OpenFlow-enabled virtual switch (Open vSwitch), classifies each flow using a pre-trained Random Forest model, and autonomously pushes drop rules back to the switch when a DDoS attack is detected. A Flask REST API exposes live system state, and a React dashboard visualises it in real time. The scope covers all software components running on a single Ubuntu 20.04/22.04 VM using Mininet for network emulation.

### 1.3 Definitions and Acronyms

| Term / Acronym | Definition |
|----------------|------------|
| **SDN** | Software-Defined Networking — architecture that decouples the network control plane from the data plane |
| **OVS** | Open vSwitch — an open-source, OpenFlow-capable virtual switch used inside Mininet |
| **OFP** | OpenFlow Protocol — the standardised southbound interface between an SDN controller and data-plane switches |
| **PPS** | Packets Per Second — a measure of flow throughput at the packet level |
| **BPS** | Bytes Per Second — a measure of flow throughput at the byte level |
| **DDoS** | Distributed Denial-of-Service — a flood attack originating from one or more sources targeting a victim server |
| **ML** | Machine Learning — specifically, a scikit-learn Random Forest binary classifier in this system |
| **API** | Application Programming Interface — here, the Flask HTTP REST interface |
| **CORS** | Cross-Origin Resource Sharing — HTTP headers allowing the React app at port 5173 to call Flask at port 5000 |

### 1.4 References

- PRD v1.0 — *SDN-Based DDoS Detection and Mitigation System*
- OpenFlow 1.3 Specification — Open Networking Foundation
- Ryu SDN Framework Documentation — https://ryu-sdr.readthedocs.io
- Mininet Documentation — https://mininet.org/api
- scikit-learn RandomForestClassifier — https://scikit-learn.org/stable/modules/ensemble.html
- React 18 Documentation — https://react.dev
- Flask Documentation — https://flask.palletsprojects.com

---

## 2. System Overview

### 2.1 Component Diagram (Text Representation)

```
+------------------------------------------------------------------+
|                        Ubuntu 20.04/22.04 VM                     |
|                                                                   |
|  +-------------------------------------------------------------+  |
|  |                    Mininet Emulation                         |  |
|  |                                                              |  |
|  |   h1 (10.0.0.1) --+                                         |  |
|  |   [Legit Traffic]  |                                         |  |
|  |                    +---- s1 (OVS Switch) ---- h3             |  |
|  |   h2 (10.0.0.2) --+     [OpenFlow 1.3]   (10.0.0.3)        |  |
|  |   [Attacker]              |                [Server]          |  |
|  +---------------------------|---------------------------------+  |
|                              | OpenFlow / TCP 6653               |
|                  +-----------v--------------+                    |
|                  |   Ryu SDN Controller     |                    |
|                  |  +--------------------+  |                    |
|                  |  |  Flow Collector    |  |                    |
|                  |  |  (OFPFlowStats)    |  |                    |
|                  |  +--------+-----------+  |                    |
|                  |           |               |                    |
|                  |  +--------v-----------+  |                    |
|                  |  |  ML Classifier     |  |                    |
|                  |  | (RandomForest)     |  |                    |
|                  |  +--------+-----------+  |                    |
|                  |           | DDoS?         |                    |
|                  |  +--------v-----------+  |                    |
|                  |  |  OFPFlowMod DROP   |  |                    |
|                  |  |  (priority 65535)  |  |                    |
|                  |  +--------------------+  |                    |
|                  |  +--------------------+  |                    |
|                  |  |  In-Memory State   |  |                    |
|                  |  |  (blocked_ips,     |  |                    |
|                  |  |   live_stats)      |  |                    |
|                  |  +--------+-----------+  |                    |
|                  +-----------|---------------+                    |
|                              | HTTP / localhost:5000              |
|                  +-----------v--------------+                    |
|                  |   Flask REST API         |                    |
|                  |  /api/network-stats      |                    |
|                  |  /api/blocked-ips        |                    |
|                  +-----------+--------------+                    |
|                              | HTTP polling / localhost:5173      |
|                  +-----------v--------------+                    |
|                  |   React Dashboard        |                    |
|                  |  (Vite + Recharts)       |                    |
|                  +--------------------------+                    |
+------------------------------------------------------------------+
```

### 2.2 Data Flow Summary

1. **h2 launches a flood attack** — packets hit s1 at high PPS.
2. **Ryu polls s1** via `OFPFlowStatsRequest` every 1–2 seconds — receives `OFPFlowStatsReply`.
3. **Flow Collector** computes per-flow PPS, BPS, duration, and packet count.
4. **ML Classifier** runs `model.predict()` on the derived features — returns `1` (DDoS) for the h2 flow.
5. **Ryu pushes `OFPFlowMod`** with `priority=65535`, `match={ipv4_src: 10.0.0.2}`, `actions=[]` (DROP) to s1.
6. **s1 enforces the rule** at line rate — all subsequent h2 packets are silently dropped at the switch.
7. **Controller updates in-memory state**: adds h2 to the blocked-IP list, updates PPS counters.
8. **Flask endpoints** serve the updated state to any polling client.
9. **React dashboard** re-renders chart, status badge, and blocked-IP table within 1 second.

---

## 3. Functional Requirements

| ID | Requirement | Priority | Details |
|----|-------------|----------|---------|
| **FR-001** | Mininet Topology | MUST | The system shall instantiate a Mininet topology with exactly three hosts and one switch: **h1** (IP: `10.0.0.1`, role: legitimate traffic source), **h2** (IP: `10.0.0.2`, role: attacker), **h3** (IP: `10.0.0.3`, role: victim server), **s1** (Open vSwitch, OpenFlow 1.3). The Ryu controller shall be reachable at `127.0.0.1:6653`. |
| **FR-002** | Flow Statistics Collection | MUST | The Ryu controller shall send an `OFPFlowStatsRequest` to switch `s1` at a configurable interval of **1–2 seconds**. It shall parse the resulting `OFPFlowStatsReply` and extract per-flow counters: `packet_count`, `byte_count`, `duration_sec`, `duration_nsec`, source IP (`ipv4_src`), and destination IP (`ipv4_dst`). |
| **FR-003** | CSV Flow Logger | MUST | The controller shall append each collected flow record to a CSV file. The CSV shall contain the following columns in order: `timestamp`, `src_ip`, `dst_ip`, `packet_count`, `byte_count`, `duration_sec`, `pps` (computed), `bps` (computed), `label` (integer, added offline during training data preparation — `0` = Normal, `1` = DDoS). |
| **FR-004** | ML-Based Attack Classification | MUST | For every flow record received, the controller shall pass the feature vector `[pps, bps, duration_sec, packet_count]` to a pre-loaded `RandomForestClassifier` (scikit-learn). The model shall return label `0` (Normal) or `1` (DDoS) within **5 ms** per inference call. The model file shall be loaded from disk at controller startup using `joblib.load()`. |
| **FR-005** | Automatic Drop Rule Insertion | MUST | Upon classification of a flow as DDoS (`label=1`), the Ryu controller shall immediately construct and send an `OFPFlowMod` message to `s1` with the following parameters: `priority=65535`, `match=OFPMatch(eth_type=0x0800, ipv4_src=<attacker_ip>)`, `actions=[]` (empty action list = DROP), `hard_timeout=0`, `idle_timeout=0` (permanent rule). The rule shall be installed within **3 seconds** of the first malicious packet being detected. |
| **FR-006** | Network Stats API Endpoint | MUST | The Flask application shall expose `GET /api/network-stats`. The endpoint shall return HTTP 200 with a JSON body conforming to the schema defined in Section 5.1. Fields include: `status`, `current_pps`, `active_flows`, `normal_baseline_pps`, `blocked_count`, `timestamp`, `controller_uptime_sec`. |
| **FR-007** | Blocked IPs API Endpoint | MUST | The Flask application shall expose `GET /api/blocked-ips`. The endpoint shall return HTTP 200 with a JSON array conforming to the schema defined in Section 5.2. Each element includes: `ip`, `blocked_at`, `reason`, `packets_dropped`, `pps_at_detection`. |
| **FR-008** | CORS Configuration | MUST | The Flask application shall enable CORS for all routes, permitting requests from the origin `http://localhost:5173`. No other external origin shall be whitelisted in the initial version. |
| **FR-009** | React Polling | MUST | The React dashboard shall poll both `GET /api/network-stats` and `GET /api/blocked-ips` independently, each on a **1-second interval** using `setInterval`. Polling shall continue in the background regardless of UI interaction. |
| **FR-010** | Rolling 30-Second PPS Chart | MUST | The dashboard shall render a line chart displaying the `current_pps` value over a rolling window of the last **30 data points** (approximately 30 seconds of history). Data points older than 30 seconds shall be evicted from the chart buffer. The chart shall use the Recharts library. |
| **FR-011** | Status Badge | MUST | The dashboard shall display a status badge whose colour and label reflect the current `status` field from `/api/network-stats`: **green NORMAL** when no attack is active, **pulsing red UNDER_ATTACK** when the ML classifier is actively detecting DDoS, **yellow MITIGATING** when a drop rule has been pushed but traffic is still above the normal baseline. |
| **FR-012** | Blocked IPs Table | MUST | The dashboard shall render a table of all blocked IPs returned by `/api/blocked-ips`. Each row shall display: IP address, blocked-at timestamp (human-readable), reason string, and a **DROPPED** badge. The table shall update on every poll cycle. |
| **FR-013** | Controller Offline Toast | SHOULD | When the React dashboard fails to reach either API endpoint (network error or HTTP 5xx), it shall display a non-blocking toast notification reading "Controller Offline" or equivalent. The UI shall not crash or display an error boundary. Polling shall automatically resume when the endpoint becomes available again. |
| **FR-014** | Attack Traffic Generator Script | MUST | The project shall include an `attack_traffic.sh` shell script that, when executed on `h2` inside Mininet, generates a packet flood targeting `h3` (10.0.0.3) using `hping3 --flood`. The script shall produce a sustained rate of **> 20,000 PPS**. |
| **FR-015** | Legitimate Traffic Generator Script | MUST | The project shall include a `legit_traffic.sh` shell script that, when executed on `h1` inside Mininet, generates normal traffic to `h3` using `iperf` or `curl`. The script shall produce a sustained rate of **100–300 PPS**, representative of a real user workload. |

---

## 4. Non-Functional Requirements

| ID | Category | Requirement | Target |
|----|----------|-------------|--------|
| **NFR-001** | **Performance — Detection Latency** | The total time from the first malicious packet entering `s1` to the insertion of the `OFPFlowMod` drop rule shall not exceed 3 seconds under all test conditions described in Section 7. | **< 3 seconds (p99)** |
| **NFR-002** | **Performance — API Response Time** | Both Flask API endpoints shall respond to GET requests within 100 ms under normal operating load (React polling at 1-second intervals). | **< 100 ms (p99)** |
| **NFR-003** | **Reliability — Controller Uptime** | The Ryu controller process shall not crash or require restart during a 30-minute continuous stress test consisting of high-rate attack traffic from `h2` and legitimate traffic from `h1`. | **0 unplanned restarts in 30 min** |
| **NFR-004** | **Accuracy — ML Classifier** | The deployed Random Forest model shall achieve a false positive rate (legitimate traffic classified as DDoS) of less than 2% on the held-out test split of the labelled flow dataset. | **FPR < 2%** |
| **NFR-005** | **Usability — Dashboard Responsiveness** | The React dashboard shall maintain a rendering frame rate of 60 FPS or higher during an active DDoS attack simulation, as measured by the Chrome DevTools Performance panel. No UI jank or freezing shall occur during the poll cycle or chart update. | **>= 60 FPS sustained** |
| **NFR-006** | **Maintainability — Code Quality** | All Python backend modules shall include inline docstrings for every function. The React codebase shall use functional components with TypeScript type annotations. A `README.md` shall provide complete setup and run instructions reproducible in under 15 minutes by a new team member. | **100% docstring coverage on public functions; TypeScript strict mode enabled** |

---

## 5. Interface Requirements

### 5.1 `GET /api/network-stats` — Response Schema

**HTTP Method:** `GET`
**URL:** `http://localhost:5000/api/network-stats`
**Response Content-Type:** `application/json`
**Response HTTP Status:** `200 OK`

```json
{
  "status": "UNDER_ATTACK",
  "current_pps": 23847.5,
  "active_flows": 4,
  "normal_baseline_pps": 215.3,
  "blocked_count": 1,
  "timestamp": "2026-09-24T15:32:10.441Z",
  "controller_uptime_sec": 134
}
```

| Field | Type | Example Value | Description |
|-------|------|---------------|-------------|
| `status` | `string` | `"UNDER_ATTACK"` | One of: `"NORMAL"`, `"UNDER_ATTACK"`, `"MITIGATING"`. Derived from ML classification and current PPS levels. |
| `current_pps` | `number` (float) | `23847.5` | Aggregate packets-per-second across all active flows on `s1` at the last poll cycle. |
| `active_flows` | `number` (integer) | `4` | Total number of distinct flows currently tracked by the controller. |
| `normal_baseline_pps` | `number` (float) | `215.3` | Rolling average PPS measured during non-attack periods; used as the normal traffic baseline. |
| `blocked_count` | `number` (integer) | `1` | Total number of unique IP addresses that have been blocked since controller startup. |
| `timestamp` | `string` (ISO 8601) | `"2026-09-24T15:32:10.441Z"` | UTC timestamp of when this response was generated. |
| `controller_uptime_sec` | `number` (integer) | `134` | Seconds elapsed since the Ryu controller process started. |

---

### 5.2 `GET /api/blocked-ips` — Response Schema

**HTTP Method:** `GET`
**URL:** `http://localhost:5000/api/blocked-ips`
**Response Content-Type:** `application/json`
**Response HTTP Status:** `200 OK`

```json
[
  {
    "ip": "10.0.0.2",
    "blocked_at": "2026-09-24T15:32:07.112Z",
    "reason": "DDoS detected by ML classifier (RandomForest)",
    "packets_dropped": 47892,
    "pps_at_detection": 23581.0
  }
]
```

| Field | Type | Example Value | Description |
|-------|------|---------------|-------------|
| `ip` | `string` | `"10.0.0.2"` | IPv4 address of the blocked host. |
| `blocked_at` | `string` (ISO 8601) | `"2026-09-24T15:32:07.112Z"` | UTC timestamp of when the `OFPFlowMod` drop rule was pushed for this IP. |
| `reason` | `string` | `"DDoS detected by ML classifier (RandomForest)"` | Human-readable reason string for the block. |
| `packets_dropped` | `number` (integer) | `47892` | Running count of packets dropped by the OVS rule since the block was installed. Sourced from OFPFlowStatsReply for the drop rule. |
| `pps_at_detection` | `number` (float) | `23581.0` | The PPS of the offending flow at the exact moment the ML classifier returned label `1`. |

---

### 5.3 Error Responses

Both endpoints shall return the following body for internal server errors:

```json
{
  "error": "Internal server error",
  "message": "<exception message string>"
}
```

| HTTP Status | Condition |
|-------------|-----------|
| `200 OK` | Request processed successfully |
| `500 Internal Server Error` | Unhandled exception in the Flask route handler |

---

## 6. System Constraints

| Constraint | Specification |
|------------|---------------|
| **Python Version** | Python **3.8 or higher** is required for all backend components (Ryu app, Flask app, ML training scripts). |
| **React Version** | React **18.x** is required. The dashboard uses the `createRoot` API introduced in React 18. Vite (preferred) shall be used as the build tool. |
| **Operating System** | **Ubuntu 20.04 LTS or 22.04 LTS** (64-bit). Mininet and OVS have known compatibility issues on other distributions. The system is not tested on macOS or Windows. |
| **OpenFlow Version** | **OpenFlow 1.3** is the required protocol version. The Ryu app shall declare `OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]`. OFP 1.0/1.2 compatibility is not required. |
| **Ryu Version** | **Ryu 4.x** (latest stable). The `ryu.app.ofctl_rest` mixin may be used for auxiliary controller introspection. |
| **Scikit-Learn Version** | **scikit-learn 1.x**. The model serialisation format (joblib pickle) must be compatible between the training environment and the runtime environment. Both environments shall use the same scikit-learn major version. |
| **Node.js Version** | **Node.js 18.x or 20.x LTS** for the React development server and build toolchain. |
| **Network Emulator** | **Mininet 2.3.x** with OVS kernel module. The Mininet Python API (`from mininet.net import Mininet`) is used to define the topology programmatically. |

---

## 7. Testing Requirements

### 7.1 Unit Tests

| Component | What to Test | Pass Criterion |
|-----------|-------------|----------------|
| **ML Feature Extractor** | Given `packet_count=1000`, `byte_count=60000`, `duration_sec=5`, confirm PPS=200 and BPS=12000 are computed correctly. | Exact numerical equality |
| **ML Classifier** | Load the trained model; pass a known high-PPS flow (PPS > 10,000) and verify label = 1; pass a low-PPS flow (PPS < 500) and verify label = 0. | Correct label for both cases |
| **Flask /api/network-stats** | Use Flask test client (`app.test_client()`); assert HTTP 200; assert all 7 required fields are present in the response JSON; assert `status` is one of the three valid strings. | All assertions pass |
| **Flask /api/blocked-ips** | With one IP pre-populated in the blocked list, assert the endpoint returns a JSON array of length 1 with all 5 required fields; assert `blocked_at` is a valid ISO 8601 timestamp. | All assertions pass |
| **CORS Headers** | Send a preflight `OPTIONS` request with `Origin: http://localhost:5173`; assert `Access-Control-Allow-Origin` header is present in the response. | Header present and correct |

### 7.2 Integration Tests

| Scenario | Steps | Pass Criterion |
|----------|-------|----------------|
| **Full Detect-and-Block Loop** | 1. Start Mininet topology. 2. Start Ryu controller. 3. Run `attack_traffic.sh` on h2. 4. Wait up to 5 seconds. 5. Poll `GET /api/blocked-ips`. | IP `10.0.0.2` appears in the blocked list within 5 seconds of script start |
| **Legitimate Traffic Unaffected** | 1. Start all components. 2. Run `legit_traffic.sh` on h1. 3. Run `attack_traffic.sh` on h2. 4. After block rule is inserted, measure h1-to-h3 iperf throughput. | h1 throughput drop is < 5% compared to pre-attack baseline |
| **API-Dashboard Integration** | 1. Start Flask app. 2. Open dashboard in Chrome. 3. Trigger an attack. 4. Observe status badge and chart. | Badge transitions to `UNDER_ATTACK` within 2 seconds; chart PPS spike is visible; blocked-IP table populates |
| **Controller Restart Recovery** | 1. Start all components. 2. Kill and restart the Ryu controller process. 3. Observe dashboard. | Dashboard shows "Controller Offline" toast during downtime; recovers and resumes displaying data within 5 seconds of controller restart |

### 7.3 Performance Tests

| Test | Method | Pass Criterion |
|------|--------|----------------|
| **Detection Latency** | Use `tcpdump` on h3 to record first attack packet timestamp; cross-reference with controller log timestamp for OFPFlowMod insertion. Repeat 10 times and compute p99. | p99 latency < 3 seconds |
| **Attack Traffic Reduction** | With block rule active, use `ifconfig` or `bwm-ng` on h3 to measure incoming PPS. Compare to peak attack PPS. | Incoming PPS on h3 reduced by > 95% post-block |
| **ML Inference Throughput** | In isolation, call `model.predict()` in a loop for 1,000 feature vectors; measure total wall time. | < 5 ms per call on average; p99 < 10 ms |
| **30-Minute Stress Test** | Run attack + legitimate traffic simultaneously for 30 minutes. Monitor Ryu process (`ps`, `top`). | Zero controller crashes; memory usage does not grow unboundedly (no memory leak) |
| **Dashboard FPS** | Open Chrome DevTools Performance tab; record 30 seconds of active attack simulation. | Mean FPS >= 60; no frames below 30 FPS during chart update cycle |
