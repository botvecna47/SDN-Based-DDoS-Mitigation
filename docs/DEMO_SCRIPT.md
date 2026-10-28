# Demo Script

A structured guide for presenting the SDN DDoS Mitigation project.

## 1. Pre-Demo Setup
Ensure all components are running before presenting.

1. **Terminal 1 (Ryu, Ubuntu VM):**
   ```bash
   source ryu39_env/bin/activate
   ryu-manager controller/simple_monitor.py
   ```
2. **Terminal 2 (Flask, Ubuntu VM):**
   ```bash
   source ryu39_env/bin/activate
   cd backend_api
   python3 app.py
   ```
3. **Terminal 3 (Mininet, Ubuntu VM):**
   ```bash
   sudo mn -c
   sudo python3 network/topo.py
   ```
4. **Terminal 4 (React, Windows Host):**
   ```powershell
   cd "DDoS Mitigation"
   npm run dev
   ```

## 2. Window Layout

Organize your screen to maximize visibility of system interactions:
```text
+-------------------------+-------------------------+
| [Ryu Terminal]          | [Sentinel Dashboard]    |
| Showing stat polling    | Showing live chart      |
| and detection logs      | http://localhost:5173   |
+-------------------------+-------------------------+
| [Mininet CLI]           | [Flask API]             |
| Ready for hping3        | Showing GET requests    |
+-------------------------+-------------------------+
```

## 3. Act 1: Baseline (2 min)
**Action:** Show the dashboard and Mininet CLI.
**Talk Track:** "Welcome to our SDN DDoS defense project. We have an emulated Mininet topology with OVS and Ryu. Notice our dashboard is green ('operational'). Legitimate traffic is flowing steadily."

## 4. Act 2: Attack Launch (1 min)
**Action:** In Mininet CLI, run:
```bash
mininet> xterm h2
# In h2 xterm:
sudo hping3 --flood --udp -p 80 10.0.0.3
```
**Talk Track:** "I'm now launching a UDP flood attack from node h2 towards our server at h3."

## 5. Act 3: Autonomous Defense (1 min)
**Action:** Point to the dashboard changing state and the Ryu terminal output. Show the installed OpenFlow rule:
```bash
# In Mininet CLI:
mininet> sh ovs-ofctl dump-flows s1
```
**Talk Track:** "Within a few statistics cycles, Ryu detects the PPS threshold breach (>10k) when the fallback is active. A high-priority DROP rule (65535) is pushed to OVS. The dashboard shows the attacker's blocked-flow counters while h1's legitimate traffic continues."

## 6. Act 4: Recovery (1 min)
**Action:** Stop the `hping3` command in `h2` xterm.
**Talk Track:** "Once the attack halts, dropped PPS falls back to zero and the network status returns to operational. The attacker remains in the blocked table until the switch's idle-timeout removes the rule after five minutes without matching traffic."

## 7. Bonus: Flow Table Inspection
**Action:** In an Ubuntu terminal, run:
```bash
curl http://192.168.8.147:5000/api/flow-table
```
**Talk Track:** "We also have an API to inspect live OpenFlow rules, cleanly categorizing allowed flows vs blocked flows."

## 8. Q&A

**Q: Are you using machine learning?**
A: We have designed an ML pipeline with a RandomForestClassifier. Currently, the controller uses a robust fallback threshold (PPS > 10,000) while the model `detector.joblib` completes training.

**Q: How do the frontend and backend communicate?**
A: Ryu writes to a `shared_state.json` file securely using a filelock. The Flask API reads this file and serves it to the React app via a single REST endpoint `/api/network-stats` every 1 second.

**Q: Why 1.5 seconds for polling?**
A: It offers a balance between rapid detection and keeping switch control plane overhead low.

**Q: How does the switch know to drop traffic?**
A: Ryu installs an `OFPFlowMod` rule with priority 65535, matching the attacker's IP and instructing the switch to DROP.

**Q: Is the dashboard real-time?**
A: Yes, it fetches state every 1 second using native `fetch` and maintains a 48-second rolling window.

**Q: What version of Python is required?**
A: Python 3.9 in the `ryu39_env` virtual environment for Ryu compatibility.

**Q: Are cross-origin requests handled?**
A: Yes, Flask is configured with `CORS(origins="*")` to permit the React dev server to communicate easily.

**Q: What triggers a recovery?**
A: The status returns to operational when traffic falls below 5,000 PPS; the blocked record stays until the switch confirms that its idle-timeout removed the rule.

## 9. Backup Plans
- **Mininet crashes:** `sudo mn -c` to clean up and restart.
- **Dashboard fails:** Reload the page; verify `.env` IP matches the Ubuntu VM.
- **Ryu fails:** Restart the `simple_monitor.py` script; verify `ryu39_env` is active.
- **ML fails:** The code has a fallback to the PPS threshold built-in natively.

*Last Updated: 2026-10-09*
