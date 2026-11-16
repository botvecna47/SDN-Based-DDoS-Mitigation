# SDN DDoS Mitigation — Attack Emulation Guide

A comprehensive technical guide to generating, benchmarking, and demonstrating multiple Distributed Denial of Service (DDoS) attack vectors against the Software-Defined Networking (SDN) defense system.

---

## 1. Overview & Emulation Architecture

The defense system combines an **OpenFlow 1.3 Ryu Controller** with a **Tier-1 CIC-DDoS2019 Decision Tree** (28 ANOVA features). To thoroughly validate the machine learning engine, this guide details how to emulate **6 distinct attack vectors**:

| Attack Vector | Layer | Traffic Profile | Primary Detection Mechanism |
|:---|:---:|:---|:---|
| **1. Fast Volumetric UDP Flood** | L4 | 20,000–50,000 PPS, high bandwidth | High PPS/BPS, Packet Length variance, Inbound score |
| **2. TCP SYN Flood** | L4 | High-rate incomplete TCP handshakes | Flag count skew, ACK starvation, TCP window features |
| **3. Slowloris (Slow DoS)** | L7/L4 | Low rate (< 100 PPS), high connection duration | Flow Duration, Flow IAT Mean, Header trickling |
| **4. ICMP Ping Flood** | L3 | Maximum wire-speed ICMP Echo requests | High PPS, zero L4 ports, non-zero payload size |
| **5. Pulsing / Wave DDoS** | L4 | Alternating bursts (10s flood / 5s silence) | Dynamic state transitions, rate oscillations |
| **6. Distributed Multi-IP Botnet** | L3/L4 | Coordinated multi-source assault (h2, h4–h8) | Multi-flow classifier, per-source `OFPFlowMod` DROP rules |

---

## 2. Choosing Your Mininet Topology

Depending on whether you are doing a single-attacker demo or a full distributed botnet demo, select one of the two topologies:

### Option A: Standard 3-Host Topology (Fast Demo)
```bash
# Terminal 3 on Ubuntu VM:
sudo mn -c
sudo python3 network/topo.py
```
- **Hosts**: `h1` (Legitimate Client: `10.0.0.1`), `h2` (Attacker: `10.0.0.2`), `h3` (Server: `10.0.0.3`).

### Option B: 8-Host Botnet Topology (Multi-IP Botnet Demo)
```bash
# Terminal 3 on Ubuntu VM:
sudo mn -c
sudo python3 network/topo_botnet.py
```
- **Hosts**: 
  - `h1` (`10.0.0.1`): Legitimate Client
  - `h3` (`10.0.0.3`): Target Protected Server (HTTP Port 80 + iperf UDP Port 5001)
  - `h2`, `h4`, `h5`, `h6`, `h7`, `h8` (`10.0.0.2`–`10.0.0.8`): Distributed Botnet Nodes

---

## 3. Interactive Attack Launchpad

An interactive menu script is provided in `network/attack_menu.sh` to trigger any vector with a single keystroke:

```bash
# On Ubuntu VM (inside the Mininet namespace or directly on host):
bash network/attack_menu.sh
```

**Interactive Menu Options:**
```text
======================================================================
       SDN DDOS MITIGATION — ATTACK EMULATION LAUNCHPAD               
======================================================================
 Target Server : 10.0.0.3 (Host h3)
 Detection     : Tier-1 CIC-DDoS2019 Decision Tree (Ryu Controller)
======================================================================

Select an attack vector to launch:
  [1] Fast Volumetric UDP Flood       (hping3 --flood --udp -p 80)
  [2] TCP SYN Handshake Flood         (hping3 --flood -S -p 80)
  [3] Slowloris Low-and-Slow HTTP DoS (python3 slowloris.py 150 conns)
  [4] High-Rate ICMP Ping Flood       (hping3 --flood --icmp)
  [5] Dynamic Pulsing / Wave Attack   (10s ON / 5s OFF bursts)
  [6] Coordinated Multi-IP Botnet     (Launches h2, h4-h8 simultaneously)
  [7] Stop All Background Attacks
  [0] Exit
```

You can also launch any vector non-interactively by passing the number:
```bash
bash network/attack_menu.sh 1   # Immediately starts Volumetric UDP
bash network/attack_menu.sh 7   # Immediately stops all attacks
```

---

## 4. Manual Execution & Mininet CLI Commands

If you prefer to run attacks manually inside the Mininet CLI (`mininet>`), use the commands below:

### Vector 1: Fast Volumetric UDP Flood (High PPS)
Floods random UDP datagrams targeting port 80 to overwhelm the switch buffer and server link:
```bash
# Inside Mininet CLI:
mininet> h2 hping3 --flood --udp -p 80 10.0.0.3
```
*Expected Result*: Ingress traffic surges to 20,000+ PPS. Within 1.5 seconds, Ryu detects the anomaly, pushes a Priority 65535 DROP rule for `10.0.0.2`, and dropped traffic rises while forwarded traffic drops to 0.

---

### Vector 2: TCP SYN Flood (L4 Handshake Exhaustion)
Sends an uninterrupted stream of TCP SYN packets with randomized source ports without ever acknowledging the SYN-ACK:
```bash
# Inside Mininet CLI:
mininet> h2 hping3 --flood -S -p 80 10.0.0.3
```
*Expected Result*: Decision tree identifies abnormal TCP flag ratios (`SYN=1`, `ACK=0`) and classifies the flow as DDoS. Ryu blocks `10.0.0.2`.

---

### Vector 3: Slowloris Low-and-Slow HTTP DoS
Establishes 150 lingering TCP connections to `10.0.0.3:80` and trickles incomplete HTTP headers every 3 seconds:
```bash
# Inside Mininet CLI:
mininet> h2 python3 network/slowloris.py 10.0.0.3 80 150
```
*Expected Result*: PPS remains low (< 50 PPS), but connection duration and header intervals spike. The Decision tree flags the abnormal `Flow Duration` and `Min Packet Length` feature combination, blocking the slow attacker.

---

### Vector 4: ICMP Echo / Ping Flood
Floods raw ICMP echo request packets at wire-speed:
```bash
# Inside Mininet CLI:
mininet> h2 hping3 --flood --icmp 10.0.0.3
```
*Expected Result*: Feature mapper assigns missing L4 ports to standard ephemeral ports and detects the ICMP packet rate surge, installing the drop rule.

---

### Vector 5: Dynamic Pulsing / Wave Attack
Alternates between 10 seconds of aggressive flooding and 5 seconds of quiet recovery to test the controller's agility:
```bash
# Inside Mininet CLI:
mininet> h2 bash -c "while true; do timeout 10 hping3 --flood --udp -p 80 10.0.0.3; sleep 5; done"
```
*Expected Result*: The React dashboard chart displays periodic saw-tooth oscillations. The system status shifts between `UNDER_ATTACK` and `RECOVERED` dynamically.

---

### Vector 6: Coordinated Multi-IP Botnet Assault
Launches an attack across 6 botnet nodes simultaneously, hitting different ports and protocols:

```bash
# If using Option B (network/topo_botnet.py):
mininet> h2 hping3 --flood --udp -p 80 10.0.0.3 &
mininet> h4 hping3 --flood -S -p 80 10.0.0.3 &
mininet> h5 python3 network/slowloris.py 10.0.0.3 80 100 &
mininet> h6 hping3 --flood --icmp 10.0.0.3 &
mininet> h7 hping3 --flood --udp -p 8080 10.0.0.3 &
mininet> h8 hping3 --flood --udp -p 53 10.0.0.3 &
```

To stop all botnet nodes inside Mininet:
```bash
mininet> h2 pkill -f hping3; h4 pkill -f hping3; h6 pkill -f hping3; h7 pkill -f hping3; h8 pkill -f hping3; h5 pkill -f slowloris
```

*Expected Result*: The React dashboard **Threats Blocked** table dynamically enumerates all 6 attacker IP addresses (`10.0.0.2`, `10.0.0.4`, `10.0.0.5`, `10.0.0.6`, `10.0.0.7`, `10.0.0.8`) with individual drop statistics.

---

## 5. Verifying Legitimate User Protection During Attacks

While any of the above attacks are running, generate normal traffic from `h1` (`10.0.0.1`):

```bash
# In Mininet CLI:
mininet> h1 bash network/legit_traffic.sh
# Or test basic reachability:
mininet> h1 ping -c 5 10.0.0.3
mininet> h1 curl -s http://10.0.0.3
```

**Verification Criteria:**
1. **0% Packet Loss for h1**: `h1` receives 100% response rate from `h3`.
2. **0.0% False Positive Rate**: `10.0.0.1` is **never** added to the blocked threats list.
3. **Target Server Health**: Target server `h3` remains 100% responsive throughout the attack.

---

## 6. What to Look for on the React Dashboard

| UI Component | Normal State | During Active Attack | Post-Mitigation |
|:---|:---|:---|:---|
| **System Status Pill** | `Operational` (Green) | `Under Attack` (Red) | `Mitigating Threat` / `Operational` |
| **Current / Dropped PPS** | ~85 PPS / 0 Dropped | ~24,000+ PPS / ~23,900 Dropped | Rate falls to normal baseline |
| **Engine & Latency KPI** | `ML Active · 0.18 ms` | `ML Active · 0.18 ms` | `< 5.0 ms SLA` maintained |
| **Real-time SVG Chart** | Flat green line at bottom | Red drop spikes matching ingress | Dropped curve absorbs threat |
| **Blocked Threats Table** | Empty | Rows for each attacker IP with host labels | Persists until rule timeout |
