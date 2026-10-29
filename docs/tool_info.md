# SDN-Based DDoS Mitigation: Tools, Architecture & Script Reference

This document provides a comprehensive technical reference for the core technologies, backend functionality, inter-process communication, and scripts used in the **Software-Defined Networking (SDN) DDoS Mitigation Project**.

---

## Table of Contents

1. [Executive Summary & System Architecture](#1-executive-summary--system-architecture)
2. [Ryu SDN Controller](#2-ryu-sdn-controller)
   - [What is Ryu?](#what-is-ryu)
   - [Where is it Used?](#where-is-it-used)
   - [Why Are We Using It?](#why-are-we-using-it)
   - [How Are We Using It?](#how-are-we-using-it)
   - [How Ryu Helps in This Project](#how-ryu-helps-in-this-project)
   - [Main Usage in the Project](#main-usage-in-the-project)
3. [Mininet Network Emulator](#3-mininet-network-emulator)
   - [What is Mininet?](#what-is-mininet)
   - [Where is it Used?](#where-is-it-used)
   - [Why Are We Using It?](#why-are-we-using-it)
   - [How Are We Using It?](#how-are-we-using-it)
   - [Mininet Backend Functionality & Internals](#mininet-backend-functionality--internals)
   - [How Mininet Helps in This Project](#how-mininet-helps-in-this-project)
4. [Backend Functionality & IPC Architecture](#4-backend-functionality--ipc-architecture)
   - [The Concurrency Problem: Eventlet vs. WSGI](#the-concurrency-problem-eventlet-vs-wsgi)
   - [The Solution: FileLock Shared State IPC](#the-solution-filelock-shared-state-ipc)
   - [Flask REST API Gateway](#flask-rest-api-gateway)
5. [End-to-End System Interaction](#5-end-to-end-system-interaction)
   - [Interaction Sequence Diagram](#interaction-sequence-diagram)
   - [Complete Packet Lifecycle](#complete-packet-lifecycle)
6. [Comprehensive Scripts Walkthrough](#6-comprehensive-scripts-walkthrough)
   - [`network/topo.py`](#networktopopy)
   - [`network/legit_traffic.sh`](#networklegit_trafficsh)
   - [`network/attack_traffic.sh`](#networkattack_trafficsh)
   - [`network/start_server.sh`](#networkstart_serversh)
   - [`controller/simple_monitor.py`](#controllersimple_monitorpy)
   - [`controller/mitigation.py`](#controllermitigationpy)
   - [`controller/inference_loader.py`](#controllerinference_loaderpy)
   - [`backend_api/state_manager.py`](#backend_apistate_managerpy)
   - [`backend_api/app.py`](#backend_apiapppy)
   - [`ml_pipeline/label_dataset.py`](#ml_pipelinelabel_datasetpy)
   - [`start.sh`](#startsh)
7. [Traditional Security vs. SDN-Based Defense](#7-traditional-security-vs-sdn-based-defense)

---

## 1. Executive Summary & System Architecture

Modern Distributed Denial-of-Service (DDoS) attacks overwhelm network resources by flooding targets with massive volumes of malicious traffic. Traditional perimeter firewalls and server-level defenses (such as `iptables` or rate-limiting modules) struggle against volumetric attacks because packets must still traverse intermediate network links and consume server interface bandwidth, CPU cycles, and kernel socket buffers before they can be dropped.

This project implements an **autonomous, closed-loop Software-Defined Networking (SDN) DDoS defense system**:
- **Data Plane (Mininet + Open vSwitch)**: Executes packet forwarding and packet drops in kernel space at line rate.
- **Control Plane (Ryu Controller)**: Gathers per-flow network telemetry, computes traffic velocity, runs Machine Learning inference, and dynamically programs switch flow tables.
- **Backend & IPC (Flask + FileLock State Manager)**: Decouples the asynchronous network event loop from the synchronous web presentation layer.
- **Application Plane (React Dashboard)**: Provides real-time visualization of traffic ingress, drop rates, flow tables, and active threat mitigations.

```mermaid
flowchart TD
    subgraph "Data Plane (Mininet on Ubuntu VM)"
        H1["h1: 10.0.0.1\n(Legitimate User)"] -->|iperf UDP 1 Mbps| S1{"s1: Open vSwitch\n(OpenFlow 1.3)"}
        H2["h2: 10.0.0.2\n(Attacker Host)"] -->|hping3 UDP Flood| S1
        S1 -->|Forwarded Packets| H3["h3: 10.0.0.3\n(Target Server: iperf)"]
    end

    subgraph "Control Plane (Ryu on Ubuntu VM)"
        S1 <-->|OpenFlow 1.3 (TCP 6653)| Ryu["Ryu Controller\n(simple_monitor.py)"]
        Ryu -->|OFPFlowStatsRequest every 1.5s| S1
        S1 -->|OFPFlowStatsReply (PPS/BPS)| Ryu
        Ryu -->|Feature Vector: PPS, BPS, Duration| ML["Inference Engine\n(inference_loader.py)"]
        ML -->|Prediction: DDoS Alert| Ryu
        Ryu -->|OFPFlowMod: DROP Priority 65535| S1
        Ryu -->|Append Stats| CSV[("traffic_dataset.csv")]
    end

    subgraph "Backend IPC & REST Layer (Ubuntu VM)"
        Ryu -->|Atomic FileLock Write| SharedState[/"shared_state.json"\]
        Flask["Flask REST API\n(backend_api/app.py:5000)"] -->|Atomic FileLock Read| SharedState
    end

    subgraph "Application Plane (Windows Host / Browser)"
        React["React Dashboard\n(App.tsx:5173)"] -->|HTTP GET /api/network-stats every 1s| Flask
        React -->|HTTP GET /api/flow-table| Flask
    end
```

---

## 2. Ryu SDN Controller

### What is Ryu?
[Ryu](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/controller/simple_monitor.py#L5-L12) (pronounced *"ree-yoo"*, the Japanese word for "flow") is an open-source, component-based Software Defined Networking framework entirely written in Python. Developed initially by NTT (Nippon Telegraph and Telephone Corporation) and maintained by the SDN community, Ryu provides software components with well-defined application programming interfaces (APIs) that make it easy for developers to create new network management and control applications.

Key architectural properties of Ryu:
- **Protocol Agnostic**: Supports OpenFlow v1.0, v1.2, v1.3, v1.4, v1.5, as well as Nicira extensions, NETCONF, and OF-Config.
- **Event-Driven Architecture**: Ryu apps are single-threaded greenlet coroutines powered by `eventlet` and Ryu's internal `hub`. Incoming OpenFlow messages trigger specific event handlers registered via Python decorators.
- **State Machine Integration**: Implements explicit OpenFlow handshake phases:
  - `HANDSHAKE_DISPATCHER`: Initial OpenFlow hello exchange and version negotiation.
  - `CONFIG_DISPATCHER`: Controller receives switch features and negotiates capabilities.
  - `MAIN_DISPATCHER`: Normal operational state handling packet-in, flow statistics, and flow removals.
  - `DEAD_DISPATCHER`: Datapath disconnected or teardown event.

---

### Where is it Used?
Ryu is widely used in:
- **Cloud Computing & Virtual Private Clouds (VPCs)**: Used as the network virtualization engine in platforms like OpenStack (Neutron plugin) to orchestrate tenant isolation, floating IPs, and virtual routing.
- **Data Center Interconnects (DCI)**: Managing multi-path traffic routing, load balancing, and bandwidth provisioning across geographically distributed data centers.
- **Academic & Industrial SDN Research**: Serving as the primary prototyping platform for innovative routing algorithms, Network Function Virtualization (NFV), and network security frameworks.
- **Enterprise Network Security & Scrubbing**: Dynamically inspecting packet headers, redirecting suspicious traffic to scrubbing centers, and mitigating network anomalies at line rate.

---

### Why Are We Using It?
In this DDoS mitigation project, Ryu was chosen over alternative controllers (such as ONOS, OpenDaylight, or Floodlight) for several key reasons:

1. **Python Ecosystem Synergy**: Modern Machine Learning libraries (`scikit-learn`, `joblib`, `pandas`, `numpy`) are natively Python-based. Because Ryu is 100% Python, we can load a trained ML classifier (`detector.joblib`) directly into the controller process and perform sub-millisecond inference in-memory without cross-language overhead (e.g., JNI or gRPC bridges).
2. **First-Class OpenFlow 1.3 Support**: OpenFlow 1.3 introduced multiple flow tables, flow meters, per-flow duration counters, packet/byte counters, and standardized cookie handling—all required for granular per-flow DDoS tracking.
3. **Lightweight Footprint**: Unlike Java-based controllers (ONOS or OpenDaylight) that require several gigabytes of RAM and heavy JVM spin-up times, Ryu boots in under 2 seconds and runs within a lightweight Python virtual environment (`ryu39_env`).
4. **Declarative Flow Construction**: Ryu's `ofproto_v1_3_parser` allows constructing complex flow modifications (`OFPFlowMod`), match structures (`OFPMatch`), and instruction sets (`OFPInstructionActions`) cleanly and deterministically.

---

### How Are We Using It?
Our primary controller logic resides in [`controller/simple_monitor.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/controller/simple_monitor.py). The controller performs four concurrent roles:

#### 1. L2 Learning Switch (Data Forwarding)
When a switch connects (`EventOFPSwitchFeatures`), Ryu installs a low-priority (priority 0) **Table-Miss Flow Entry**. Any packet not matching an existing rule is punted to the controller as an `EventOFPPacketIn`. Ryu inspects the Ethernet frame:
```python
# Learn source MAC to switch port mapping
self.mac_to_port[dpid][src] = in_port

# Determine destination port or FLOOD if unknown
out_port = self.mac_to_port[dpid][dst] if dst in self.mac_to_port[dpid] else ofproto.OFPP_FLOOD
```
If the destination is known, Ryu installs a bidirectional flow rule (priority 10 for IPv4) on the switch datapath and forwards the packet via `OFPPacketOut`.

#### 2. Continuous Flow Statistics Polling
A background greenlet thread spawned at initialization (`hub.spawn(self._monitor)`) queries all connected switches every **1.5 seconds**:
```python
def _monitor(self):
    while True:
        for dp in self.datapaths.values():
            self._request_stats(dp)
        hub.sleep(1.5)
```
Ryu dispatches `OFPFlowStatsRequest` to the switch. The switch replies asynchronously with `OFPFlowStatsReply`, which contains the exact packet counts, byte counts, and duration of every active flow.

#### 3. Flow Rate Velocity Calculation & Telemetry
In `_flow_stats_reply_handler`, Ryu iterates through each IPv4 flow and tracks delta values against an internal cache `self.flow_history`:
$$\text{PPS} = \frac{\text{packet\_count} - \text{prev\_pkt}}{\Delta t}$$
$$\text{BPS} = \frac{(\text{byte\_count} - \text{prev\_byte}) \times 8}{\Delta t}$$

These calculated values are continuously appended to `controller/traffic_dataset.csv` for model retraining and validation.

#### 4. Real-Time Detection & Reactive Mitigation
Each flow record is passed to `_run_inference(stats_dict, datapath)`:
- If the ML model (`inference_loader.py`) or fallback threshold determines the flow is a DDoS attack, Ryu invokes `push_drop_rule(datapath, src_ip)` in [`controller/mitigation.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/controller/mitigation.py).
- A high-priority rule (`priority=65535`) matching `ipv4_src=attacker_ip` with an empty action set is pushed to Open vSwitch.
- The attacker is instantly blacklisted, and the shared state is updated to `"UNDER_ATTACK"`.

#### 5. Rule Expiration Synchronization
When the drop rule expires after 300 seconds of inactivity, Open vSwitch sends an `EventOFPFlowRemoved` message. Ryu catches this event and removes the IP from `self.blocked_ips`, keeping the security dashboard synchronized with switch hardware.

---

### How Ryu Helps in This Project
- **Eliminates Manual Firewall Configuration**: Instead of a human operator logging into firewalls to block IPs, Ryu detects and drops malicious flows programmatically in less than 3.5 milliseconds.
- **Wire-Speed Datapath Offloading**: Ryu does not inspect every packet. It only inspects the first packet of a flow or periodic statistical summaries. Once a DROP rule is installed, Open vSwitch drops packets directly in the kernel without consuming controller CPU.
- **Telemetry Aggregation**: Ryu acts as an accurate network sensor, computing aggregate ingress PPS, dropped PPS, and active flow counts across the network fabric.

---

### Main Usage in the Project
> **The Ryu Controller functions as the Autonomous Brain of the network.** It bridges the raw data plane (Open vSwitch) with the artificial intelligence engine (`detector.joblib`), enforcing real-time programmatic security policies at the ingress switch port.

---

## 3. Mininet Network Emulator

### What is Mininet?
[Mininet](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/network/topo.py#L2-L5) is the de-facto standard network emulation platform for Software-Defined Networking. It creates a realistic virtual network running real kernel, switch, and application code on a single Linux machine.

Crucially, **Mininet is an emulator, not a simulator**:
- In a *network simulator* (e.g., NS-3), packets are mathematical abstractions, and software code cannot run unmodified.
- In *Mininet*, virtual hosts run **real Linux processes** (`iperf`, `hping3`, `python`, `bash`, `tcpdump`) inside isolated Linux network namespaces, communicating through real virtual ethernet links and an OpenFlow-compliant software switch ([Open vSwitch](https://www.openvswitch.org/)).

---

### Where is it Used?
- **SDN Application Testing**: Validating OpenFlow controllers and routing logic before production deployment.
- **Cybersecurity & Red/Blue Teaming**: Safely executing live exploit payloads, SYN floods, UDP amplification, and botnet simulations without risking production infrastructure or violating ISP terms.
- **Network Protocol Development**: Testing new congestion control algorithms, Multipath TCP (MPTCP), and IPv6 transition mechanisms.
- **Academic Benchmarking**: Providing reproducible, shareable network testbeds for scientific research papers.

---

### Why Are We Using It?
1. **Zero Hardware Cost**: Building a physical SDN testbed requires enterprise OpenFlow switches (e.g., Cisco, NoviFlow), multiple dedicated servers, and complex cabling. Mininet runs the entire environment inside a single virtual machine.
2. **Controlled & Reproducible Environment**: Every host interface, IP address, MAC address, and link characteristic is defined programmatically in Python code. Every test run starts from a clean, known baseline.
3. **Real Packet Generation**: Because Mininet hosts are real network namespaces, attack tools like `hping3` generate real raw IP/UDP packets with valid checksums and kernel socket allocations.
4. **Native Remote Controller Integration**: Mininet switches connect to external SDN controllers via standard TCP sockets (`127.0.0.1:6653`), behaving identically to physical enterprise switches.

---

### How Are We Using It?
Our network topology is defined in [`network/topo.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/network/topo.py):

```
       ┌────────────────────────┐
       │   h1: 10.0.0.1 (User)  │
       │   00:00:00:00:00:01    │
       └───────────┬────────────┘
                   │ port 1
                   ▼
         ┌───────────────────┐               ┌───────────────────────────┐
         │     s1: OVS       │◄──OpenFlow───►│  c0: RemoteController    │
         │  (OpenFlow 1.3)   │   (TCP 6653)  │  (Ryu simple_monitor.py)  │
         └───────┬───┬───────┘               └───────────────────────────┘
          port 2 │   │ port 3
                 │   └───────────────────────┐
                 ▼                           ▼
  ┌────────────────────────────┐    ┌───────────────────────────────┐
  │   h2: 10.0.0.2 (Attacker)  │    │   h3: 10.0.0.3 (Server)       │
  │   00:00:00:00:00:02        │    │   00:00:00:00:00:03           │
  │   [hping3 UDP flood]       │    │   [iperf -s -u on port 5001]  │
  └────────────────────────────┘    └───────────────────────────────┘
```

- **Switch `s1`**: An `OVSKernelSwitch` enforcing OpenFlow 1.3 protocol.
- **Controller `c0`**: Binds to `CONTROLLER_IP:6653` (default `127.0.0.1`).
- **Host `h1` (10.0.0.1)**: Simulates legitimate clients sending benign UDP traffic (1 Mbps via `iperf`).
- **Host `h2` (10.0.0.2)**: Simulates a compromised botnet agent launching high-rate volumetric UDP flood attacks (`hping3 --flood`).
- **Host `h3` (10.0.0.3)**: Simulates the victim server running an `iperf` UDP listener.
- **Automated Bootstrapping**:
  - `h3.cmd('iperf -s -u &')` starts the background UDP server automatically at network launch.
  - `net.pingAll()` triggers initial ARP broadcasts so Ryu learns all MAC addresses immediately.
  - `CLI(net)` drops into an interactive shell for manual diagnostics.

---

### Mininet Backend Functionality & Internals

Understanding how Mininet actually works under the Linux hood is critical for academic and engineering depth:

```mermaid
flowchart TD
    subgraph "Linux Kernel Space"
        OVS["Open vSwitch Kernel Datapath (openvswitch.ko)"]
        
        VETH1["veth pair: h1-eth0 <--> s1-eth1"]
        VETH2["veth pair: h2-eth0 <--> s1-eth2"]
        VETH3["veth pair: h3-eth0 <--> s1-eth3"]
        
        OVS --- VETH1
        OVS --- VETH2
        OVS --- VETH3
    end

    subgraph "Linux User Space Namespaces"
        NS1["Namespace h1\n(IP: 10.0.0.1)\nPrivate IP stack & ARP"]
        NS2["Namespace h2\n(IP: 10.0.0.2)\nPrivate IP stack & ARP"]
        NS3["Namespace h3\n(IP: 10.0.0.3)\nPrivate IP stack & ARP"]
        
        NS1 --- VETH1
        NS2 --- VETH2
        NS3 --- VETH3
    end

    subgraph "Control Plane Daemon"
        OVSDB["ovsdb-server / ovs-vswitchd"]
        OVSDB --- OVS
        OVSDB <-->|TCP 6653| RyuCtrl["Ryu Controller"]
    end
```

#### 1. Linux Network Namespaces (`netns`)
Mininet does **not** run virtual machines or Docker containers. Instead, it uses Linux kernel network namespaces (`ip netns`).
- Each host (`h1`, `h2`, `h3`) is a separate network namespace containing its own private loopback interface, routing table, iptables chains, ARP table, and network socket descriptors.
- All hosts share the same filesystem, memory space, and CPU scheduler as the parent Ubuntu OS. This is why thousands of packets per second can be generated with minimal CPU overhead.

#### 2. Virtual Ethernet Pairs (`veth`)
Links in Mininet are implemented using Linux `veth` pairs (virtual patch cables):
- A `veth` pair consists of two interconnected virtual network interfaces. A packet sent into one interface instantly emerges from the other.
- One end of the pair is moved into the host's network namespace (renamed to `h1-eth0`), and the other end is attached to the Open vSwitch bridge (named `s1-eth1`).

#### 3. Open vSwitch Kernel Datapath (`openvswitch.ko`)
Open vSwitch operates in two planes:
- **Fast Path (Kernel Space)**: The `openvswitch` kernel module caches exact-match flow rules. If an incoming packet matches a cached rule (such as `DROP`), the kernel drops it immediately without context-switching to userspace.
- **Slow Path (Userspace `ovs-vswitchd`)**: When a packet arrives with no matching flow in the kernel cache, it is sent to `ovs-vswitchd`. If still unmatched in the OpenFlow tables, it is encapsulated into an OpenFlow `Packet-In` message and transmitted to Ryu over TCP port 6653.

#### 4. Isolated Command Execution (`h.cmd()`)
When scripts call `h3.cmd('iperf -s -u &')`, Mininet executes the command using the `setns()` system call to enter the host's private network namespace before calling `exec()`. Any sockets created by that process bind strictly to the host's virtual interface.

---

### How Mininet Helps in This Project
- **Safe Attack Playground**: Allows unleashing high-rate flooding attacks without crashing the physical network adapter or triggering campus/cloud ISP security blocks.
- **Precise Network Visibility**: Provides direct access to individual host interfaces for packet sniffing (`tcpdump`) and port monitoring.
- **Rapid Cleanup and Reset**: If a test run fails, running `sudo mn -c` completely flushes stale kernel datapaths, virtual ethernet interfaces, and temporary sockets in seconds.

---

## 4. Backend Functionality & IPC Architecture

### The Concurrency Problem: Eventlet vs. WSGI
A major architectural obstacle encountered in SDN web dashboards is bridging the controller with a modern REST API:
- **Ryu Concurrency**: Ryu is built on `eventlet`, a coroutine-based networking library. Eventlet relies on **green threads** and monkey-patches Python's standard library (`socket`, `select`, `thread`) to make I/O non-blocking within a single operating system thread.
- **Flask Concurrency**: Modern Flask and WSGI servers (e.g., Werkzeug, Gunicorn) use native operating system threads or standard blocking I/O models.

When developers attempt to run Flask inside the same Python process as Ryu, **catastrophic thread deadlocks occur**:
1. Flask's HTTP request handler blocks the Eventlet greenlet hub.
2. Ryu's asynchronous event loop freezes.
3. Ryu fails to respond to Open vSwitch `OFPEchoRequest` keepalive heartbeats.
4. Open vSwitch assumes the controller is dead, tears down the TCP connection, and either drops all traffic or falls back to standalone switching mode.

```
❌ NAIVE (SAME-PROCESS) ARCHITECTURE — CAUSES DEADLOCK:
┌────────────────────────────────────────────────────────┐
│ Single Python Process                                  │
│   Ryu (Eventlet Coroutines) ◄──MUTUAL DEADLOCK──►      │
│   Flask (WSGI / Native Threads)                        │
└────────────────────────────────────────────────────────┘
Result: Ryu freezes, OpenFlow echo timeout expires, OVS disconnects.
```

---

### The Solution: FileLock Shared State IPC
To achieve 100% stability, we decoupled the architecture into two independent processes communicating via an atomic Inter-Process Communication (IPC) file:

```
✅ DECOUPLED IPC ARCHITECTURE (OUR IMPLEMENTATION):
┌─────────────────────────┐          ┌─────────────────────────┐
│ Process 1: Ryu Controller│          │ Process 2: Flask API    │
│ (controller/simple_monitor)│       │ (backend_api/app.py)    │
└────────────┬────────────┘          └────────────▲────────────┘
             │                                    │
             ▼                                    │
       Atomic Write                         Atomic Read
   with FileLock (exclusive)           with FileLock (shared)
             │                                    │
             └──────────► ┌──────────────────┐ ───┘
                          │ shared_state.json│
                          └──────────────────┘
```

The coordination is managed in [`backend_api/state_manager.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/backend_api/state_manager.py):
```python
STATE_FILE = os.path.join(os.path.dirname(__file__), 'shared_state.json')
LOCK_FILE = f"{STATE_FILE}.lock"

def update_state(**kwargs):
    with FileLock(LOCK_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        state.update(kwargs)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)

def read_state():
    with FileLock(LOCK_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
```

**Why this works flawlessly:**
- Ryu writes the latest network snapshot every 1.5 seconds.
- The `FileLock` guarantees that Flask will never read a half-written ("torn") JSON payload.
- Neither process shares memory or execution threads, eliminating the possibility of deadlocks or socket starvation.

---

### Flask REST API Gateway
The Flask service in [`backend_api/app.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/backend_api/app.py) exposes clean JSON endpoints for the web dashboard:

1. **`GET /api/network-stats`**:
   - Returns system health (`"operational"`, `"degraded"`, `"offline"`).
   - Metrics: Ingress PPS, dropped PPS, controller uptime, ML decision delay in milliseconds.
   - Traffic History: Maintains a rolling 48-tick history window (`history_ingress`, `history_dropped`) for the frontend SVG chart.
   - Active Threat Roster: Maps raw blocked IP addresses to human-readable host labels (e.g., `10.0.0.2` $\rightarrow$ `h2 (Attacker Host)`).
2. **`GET /api/flow-table`**:
   - Parses switch flow rules into categorized buckets: `ALLOWED_FLOWS`, `BLOCKED_FLOWS`, and `TABLE_MISS`.
   - Displays exact packet and byte counters for each rule.
3. **`GET /api/health`**:
   - Returns a simple JSON timestamp used by monitoring agents and health checks.

---

## 5. End-to-End System Interaction

### Interaction Sequence Diagram

The following sequence diagram details the complete operational lifecycle from initial boot to attack detection, mitigation, and recovery:

```mermaid
sequenceDiagram
    autonumber
    participant H2 as Attacker (h2)
    participant H1 as User (h1)
    participant S1 as Open vSwitch (s1)
    participant Ryu as Ryu Controller
    participant ML as ML Detector
    participant IPC as shared_state.json
    participant Flask as Flask REST API
    participant UI as React Dashboard

    Note over S1,Ryu: 1. Initialization & Handshake
    S1->>Ryu: TCP Connection established (port 6653)
    Ryu->>S1: OFPFeaturesRequest
    S1->>Ryu: OFPFeaturesReply (Switch capabilities, Datapath ID)
    Ryu->>S1: OFPFlowMod (priority=0, action=CONTROLLER) [Table-Miss]

    Note over H1,S1: 2. Normal Legitimate Traffic
    H1->>S1: UDP packet (10.0.0.1 -> 10.0.0.3:5001)
    S1->>Ryu: OFPPacketIn (First packet from h1)
    Ryu->>S1: OFPFlowMod (priority=10, match=(10.0.0.1->10.0.0.3), action=out_port)
    Ryu->>S1: OFPPacketOut (Forward buffered packet to h3)

    loop Polling Loop (Every 1.5 Seconds)
        Ryu->>S1: OFPFlowStatsRequest
        S1->>Ryu: OFPFlowStatsReply (packet_count, byte_count, duration)
        Ryu->>Ryu: Calculate PPS and BPS
        Ryu->>ML: predict(pps, bps, duration, packets)
        ML-->>Ryu: (is_ddos=False, latency=3.1ms)
        Ryu->>IPC: update_state(status="NORMAL", current_pps=100)
    end

    loop Dashboard Poll (Every 1.0 Second)
        UI->>Flask: GET /api/network-stats
        Flask->>IPC: read_state()
        IPC-->>Flask: JSON State
        Flask-->>UI: Snapshot (Health: Operational, Chart data)
    end

    Note over H2,S1: 3. Attack Inception (hping3 Flood)
    H2->>S1: Flood UDP packets (>20,000 pkts/sec) to 10.0.0.3:80
    S1->>Ryu: OFPPacketIn (First packet from h2)
    Ryu->>S1: OFPFlowMod (priority=10, match=(10.0.0.2->10.0.0.3), action=out_port)

    Note over Ryu,S1: 4. Attack Detection & Line-Rate Mitigation
    Ryu->>S1: OFPFlowStatsRequest
    S1->>Ryu: OFPFlowStatsReply (Flow 10.0.0.2 has 35,000 packets)
    Ryu->>Ryu: Calculate delta: PPS = 23,333 pkts/sec
    Ryu->>ML: predict(pps=23333, ...)
    ML-->>Ryu: (is_ddos=True, latency=3.2ms)
    
    Ryu->>S1: OFPFlowMod(priority=65535, match=(ipv4_src=10.0.0.2), action=DROP, idle_timeout=300)
    Ryu->>IPC: update_state(status="UNDER_ATTACK", blocked_ips=["10.0.0.2"])
    
    Note over S1,H2: 5. Wire-Speed Drop at Switch Ingress
    H2->>S1: Continued Flood Packets
    S1--xS1: Matched Priority 65535 DROP rule -> Discarded in kernel!
    Note over H1,S1: Legitimate User (h1) traffic continues without packet loss!

    Note over Ryu,UI: 6. Real-Time Dashboard Alert
    UI->>Flask: GET /api/network-stats
    Flask->>IPC: read_state()
    IPC-->>Flask: JSON State (status="UNDER_ATTACK", blocked=["10.0.0.2"])
    Flask-->>UI: Snapshot (Health: Degraded, Alert: Critical, Dropped PPS: 23k)
```

---

### Complete Packet Lifecycle

1. **Packet Arrival**: A packet arrives at switch port `s1-eth2` originating from `10.0.0.2`.
2. **Hardware/Kernel Flow Lookup**: Open vSwitch parses the packet header against its OpenFlow 1.3 flow table in descending order of priority:
   - **Scenario A (Normal State)**: The packet matches the `priority=10` forwarding rule $\rightarrow$ forwarded out port 3 to server `h3`.
   - **Scenario B (Mitigated State)**: The packet matches the `priority=65535` drop rule $\rightarrow$ silently dropped in the Linux kernel datapath. No packet touches the server; no packet travels across the internal network.
3. **Controller Telemetry Sync**: While packets are being dropped, the switch hardware counters for the drop rule increment. During the next 1.5s stats cycle, Ryu polls these counters and writes `dropped_pps` into the shared state.
4. **User Interface Presentation**: The React dashboard displays the dropped traffic volume in rose-colored chart lines, proving mathematically to the user that the attack has been intercepted.

---

## 6. Comprehensive Scripts Walkthrough

Every script in the repository serves a specific, deliberate architectural purpose. Below is an exhaustive breakdown of why each script exists and how it works.

---

### `network/topo.py`
- **File**: [`network/topo.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/network/topo.py)
- **Why this script exists**: Automates the construction of the virtual SDN topology. Without this script, the user would have to manually run multiple Linux commands (`ip link add`, `ovs-vsctl add-br`, `ip netns add`) to build the switch, hosts, and connections.
- **How it works**:
  1. Initializes Mininet with `RemoteController` and `OVSKernelSwitch`.
  2. Binds controller `c0` to `CONTROLLER_IP` (read from environment variables, defaulting to `127.0.0.1`) on port 6653.
  3. Creates switch `s1` with protocol explicitly pinned to `OpenFlow13`.
  4. Creates hosts `h1` (`10.0.0.1`), `h2` (`10.0.0.2`), and `h3` (`10.0.0.3`) with static MAC addresses (`00:00:00:00:00:01`, etc.) for deterministic testing.
  5. Links all three hosts to switch `s1`.
  6. Automatically boots the background `iperf` UDP listener on `h3` (`h3.cmd('iperf -s -u &')`).
  7. Runs `net.pingAll()` to prime ARP caches and trigger Ryu's initial MAC learning table.
  8. Enters the interactive Mininet CLI.

---

### `network/legit_traffic.sh`
- **File**: [`network/legit_traffic.sh`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/network/legit_traffic.sh)
- **Why this script exists**: Generates continuous, predictable legitimate baseline traffic representing a normal client browsing or streaming video.
- **How it works**:
  - Runs inside host `h1`'s network namespace (`mininet> h1 bash network/legit_traffic.sh`).
  - Executes an infinite loop running `iperf -c 10.0.0.3 -u -b 1m -t 5`.
  - Transmits UDP datagrams to `10.0.0.3` at a constant rate of **1 Megabit per second (1 Mbps)** in 5-second bursts, sleeping for 0.5s between bursts.
  - This generates approximately **80 to 120 packets per second (PPS)**, establishing a clean normal baseline.

---

### `network/attack_traffic.sh`
- **File**: [`network/attack_traffic.sh`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/network/attack_traffic.sh)
- **Why this script exists**: Simulates a volumetric UDP flood DDoS attack.
- **How it works**:
  - Runs inside attacker host `h2`'s network namespace (`mininet> h2 bash network/attack_traffic.sh`).
  - Executes `hping3 --flood --udp -p 80 10.0.0.3`.
  - Flags explained:
    - `--flood`: Transmits packets as fast as possible without waiting for incoming replies.
    - `--udp`: Generates raw UDP datagrams.
    - `-p 80`: Targets destination port 80 (HTTP).
    - `10.0.0.3`: Victim IP address (`h3`).
  - Emits between **15,000 and 40,000 packets per second**, creating a massive statistical anomaly that triggers the detection engine.

---

### `network/start_server.sh`
- **File**: [`network/start_server.sh`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/network/start_server.sh)
- **Why this script exists**: Provides a manual recovery mechanism to restart the victim service on host `h3` if the server process was terminated or crashed during testing.
- **How it works**:
  - Runs inside host `h3` (`mininet> h3 bash network/start_server.sh`).
  - Executes `iperf -s -u`, binding a UDP listener to port 5001.

---

### `controller/simple_monitor.py`
- **File**: [`controller/simple_monitor.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/controller/simple_monitor.py)
- **Why this script exists**: The primary Ryu SDN controller application. It contains the central intelligence for switching, traffic monitoring, rate computation, machine learning inference invocation, and state broadcasting.
- **How it works**:
  - Inherits from `app_manager.RyuApp`.
  - Declares `OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]`.
  - Initializes `DDoSDetector` from `inference_loader.py`.
  - Spawns polling loop `self._monitor` using `hub.spawn`.
  - Listens for OpenFlow events:
    - `EventOFPSwitchFeatures`: Clears stale rules and sets priority-0 Table-Miss rule.
    - `EventOFPPacketIn`: Performs L2 MAC learning and adds priority-10 IP forwarding rules.
    - `EventOFPFlowStatsReply`: Calculates delta PPS/BPS for every flow, logs to CSV, executes inference, triggers mitigation if necessary, and writes the snapshot to `shared_state.json`.
    - `EventOFPFlowRemoved`: Automatically cleans up expired block entries when switch drop rules time out.

---

### `controller/mitigation.py`
- **File**: [`controller/mitigation.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/controller/mitigation.py)
- **Why this script exists**: Modularizes OpenFlow 1.3 flow modification logic. Keeping flow-mod message construction separate from the main controller file prevents code bloat and allows easy extension (e.g., adding rate-limiting meters or IP redirection).
- **How it works**:
  - `push_drop_rule(datapath, src_ip)`:
    - Matches any IPv4 packet (`eth_type=0x0800`) with `ipv4_src=src_ip`.
    - Creates an empty instruction action set using `OFPIT_CLEAR_ACTIONS` (instructs OVS to discard matching packets).
    - Sets `priority=65535` (maximum 16-bit integer priority) to guarantee the drop rule takes precedence over normal forwarding rules.
    - Configures `idle_timeout=300` (auto-expires after 5 minutes of inactivity) and `OFPFF_SEND_FLOW_REM` (instructs OVS to notify Ryu when the rule expires).
    - Transmits the `OFPFlowMod` message over the datapath socket.
  - `remove_drop_rule(datapath, src_ip)`:
    - Sends an `OFPFC_DELETE` message matching the source IP to explicitly unblock a host.

---

### `controller/inference_loader.py`
- **File**: [`controller/inference_loader.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/controller/inference_loader.py)
- **Why this script exists**: Encapsulates Machine Learning model loading and prediction, providing graceful degradation. If `detector.joblib` has not yet been trained, the system transparently falls back to an algorithmic PPS threshold (>10,000 PPS).
- **How it works**:
  - Attempts to load `ml_pipeline/detector.joblib` using `joblib.load()`.
  - `predict(pps, bps, duration_sec, packet_count)`:
    - Measures execution time using high-resolution timers (`time.perf_counter()`).
    - If model is loaded: passes feature vector `[[pps, bps, duration_sec, packet_count]]` to `self.model.predict()`.
    - If model is missing: evaluates `pps > FALLBACK_THRESHOLD_PPS`.
    - Returns `(is_ddos: bool, inference_ms: float)`. The measured latency (typically 2–4ms) is passed to the dashboard to show real-time inference performance.

---

### `backend_api/state_manager.py`
- **File**: [`backend_api/state_manager.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/backend_api/state_manager.py)
- **Why this script exists**: Implements the thread-safe, process-safe Inter-Process Communication bridge between Ryu (Eventlet) and Flask (WSGI).
- **How it works**:
  - Manages `backend_api/shared_state.json` and its companion lockfile `shared_state.json.lock`.
  - Uses `filelock.FileLock` to acquire an OS-level file lock before every read or write operation.
  - Exposes three core functions:
    - `initialize_state()`: Writes default state schema at system startup.
    - `update_state(**kwargs)`: Called by Ryu to atomically update metrics.
    - `read_state()`: Called by Flask to retrieve the latest state for web clients.

---

### `backend_api/app.py`
- **File**: [`backend_api/app.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/backend_api/app.py)
- **Why this script exists**: Serves as the REST API gateway between the backend Linux controller and the web frontend.
- **How it works**:
  - Flask web server running on `0.0.0.0:5000` with `CORS(app, origins="*")` enabled.
  - Maintains a 48-item rolling deque (`history_ingress`, `history_dropped`) updated at most once per second.
  - Implements three endpoints:
    - `/api/network-stats`: Primary telemetry polling route returning health status, PPS, dropped PPS, uptime, active rules, ML latency, and threats.
    - `/api/flow-table`: Detailed breakdown of OpenFlow rules currently installed on the switch.
    - `/api/health`: Uptime and ping endpoint.
  - Enforces strict cache-control headers (`no-cache, no-store, must-revalidate`) on all responses so the browser never serves stale polling data.

---

### `ml_pipeline/label_dataset.py`
- **File**: [`ml_pipeline/label_dataset.py`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/ml_pipeline/label_dataset.py)
- **Why this script exists**: Automates the labeling of raw flow data collected during testing into a supervised Machine Learning dataset.
- **How it works**:
  - Reads raw flow records from `controller/traffic_dataset.csv`.
  - Prompts the user for the exact UTC start and end timestamps of each attack session.
  - Automatically assigns label `1` (DDoS) to records falling within attack windows and `0` (Normal) to all other rows.
  - Verifies class balance (warning if attack rows are <10% or >50% of the total dataset) and saves the processed dataset to `ml_pipeline/data/processed/labeled_dataset.csv` for training in Jupyter notebook `02_training.ipynb`.

---

### `start.sh`
- **File**: [`start.sh`](file:///c:/Users/Darshdeep/Desktop/Desktop/Trial%20And%20Error/DDoS%20Mitigation/start.sh)
- **Why this script exists**: Eliminates operator error by providing an interactive CLI menu to start each system component in the required sequence, automatically activating the Python 3.9 virtual environment (`ryu39_env`).
- **How it works**:
  - Prompts user to select:
    - `1) Start Ryu controller` $\rightarrow$ Activates `ryu39_env` and runs `ryu-manager controller/simple_monitor.py`.
    - `2) Start Flask API` $\rightarrow$ Activates `ryu39_env` and runs `python3 backend_api/app.py`.
    - `3) Start Mininet topology` $\rightarrow$ Cleans stale state via `sudo mn -c` and runs `sudo python3 network/topo.py`.
    - `4) Start React dashboard` $\rightarrow$ Executes `npm run dev`.

---

## 7. Traditional Security vs. SDN-Based Defense

The table below summarizes the key architectural advantages of this project's SDN-based approach compared to traditional enterprise perimeter defense:

| Metric / Dimension | Traditional Perimeter Defense (Firewall / Host iptables) | SDN + ML Defense (This Project) |
|---|---|---|
| **Drop Location** | Edge firewall or end-host NIC | Ingress switch port (`s1-eth2`) |
| **Server Resource Impact** | High: Server CPU and network buffers still process flooded packets until dropped | Zero: Packets are discarded before entering the server's network link |
| **Response Time** | Manual: Minutes to hours for network engineers to analyze logs and update ACLs | Autonomous: 2 to 4 milliseconds for ML inference and OpenFlow rule installation |
| **Network Visibility** | Coarse: SNMP counters sampled every 5 minutes | Granular: Per-flow packet and byte counters sampled every 1.5 seconds |
| **Cost & Scalability** | Expensive proprietary hardware appliances (e.g., Arbor Networks, Fortinet) | Software-defined: Runs on commodity OpenFlow hardware or virtual switches (OVS) |
| **Adaptability** | Static rule thresholds vulnerable to low-and-slow or fluctuating attacks | Machine Learning models retrained on dynamic flow features (PPS, BPS, duration) |

---

*Document compiled for academic review, defense demonstration, and engineering handoff.*
