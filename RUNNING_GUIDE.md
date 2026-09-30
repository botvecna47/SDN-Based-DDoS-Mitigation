# 🛡️ SDN DDoS Mitigation — Running Guide

> **Last updated: 2026-09-30** — New Sentinel UI, automatic MAC bootstrapping, auto-recovery after attacks, and Flow Table API. Always `git pull` on Ubuntu before starting.

> **Save this file. Read it every time before you run the project.**

---

## 📋 Architecture Overview

| Component | Where it runs | What it does |
|-----------|--------------|--------------|
| **Mininet** | Ubuntu VM | Creates virtual network (h1, h2, h3, s1) |
| **Ryu Controller** | Ubuntu VM | The brain — collects flow stats, detects attacks |
| **Flask API** | Ubuntu VM | Serves live data to the React dashboard |
| **React Dashboard** | Windows | Visualises traffic, PPS chart, blocked IPs |

---

## ⚠️ Golden Rules (Read Before Every Session)

> [!IMPORTANT]
> **ALWAYS start in this exact order:** Ryu → Flask → Mininet → React
> Starting Mininet before Ryu = switch has no controller = 100% packet loss

> [!IMPORTANT]
> **ALWAYS run `sudo mn -c` before starting Mininet** if you ran it before in this session. Leftover OVS state causes silent failures.

> [!IMPORTANT]
> **ALWAYS activate the virtual environment** before running Ryu or Flask:
> `source ryu39_env/bin/activate`

---

## 🚀 Step-by-Step Launch Sequence

### 🔵 STEP 0 — One-Time Setup (Only if first time after cloning)

Run this inside your Ubuntu VM in the project folder:

```bash
# Install system tools
sudo add-apt-repository universe -y
sudo apt update
sudo apt install mininet openvswitch-switch hping3 iperf git -y

# Create Python 3.9 virtual environment (Ryu requires Python 3.9)
sudo apt install python3.9 python3.9-venv python3.9-distutils -y
python3.9 -m venv ryu39_env
source ryu39_env/bin/activate

# Downgrade setuptools so Ryu installs correctly, then install everything
pip install setuptools==59.6.0 wheel==0.37.1
pip install ryu flask flask-cors pandas scikit-learn filelock
pip install eventlet==0.30.2
```

---

### 🔵 STEP 1 — Pull Latest Code (Every Session)

Open a terminal in your Ubuntu VM inside the project folder and run:

```bash
git pull
```

---

### 🔴 STEP 2 — Start Ryu Controller (Ubuntu Terminal 1)

```bash
source ryu39_env/bin/activate
ryu-manager controller/simple_monitor.py
```

**✅ Wait for this message before continuing:**
```
Ryu is running
```

> [!NOTE]
> You will also see `detector.joblib not found — using threshold fallback (pps > 10000)`.
> This is **completely normal** for the 50% demo. The controller still works perfectly.

---

### 🟡 STEP 3 — Start Flask API (Ubuntu Terminal 2)

Open a **new terminal tab** in your Ubuntu VM:

```bash
cd SDN-Based-DDoS-Mitigation
source ryu39_env/bin/activate
cd backend_api
python3 app.py
```

**✅ Wait for this message before continuing:**
```
* Running on http://0.0.0.0:5000
* Running on http://192.168.x.x:5000
```

---

### 🟢 STEP 4 — Start Mininet Network (Ubuntu Terminal 3)

Open a **third terminal tab** in your Ubuntu VM. **First, clean any leftover state:**

```bash
sudo mn -c
```

Then start the network:

```bash
cd SDN-Based-DDoS-Mitigation
sudo python3 network/topo.py
```

**✅ Immediately check Terminal 1 (Ryu). You MUST see:**
```
Registering datapath: 0000000000000001
```
If you do NOT see this, Ryu and the switch are not connected — stop and restart from Step 2.

---

### 🔵 STEP 5 — Verify Network with pingall

At the `mininet>` prompt, type:

```bash
mininet> pingall
```

**✅ You MUST see:**
```
*** Results: 0% dropped
```

> [!CAUTION]
> If you see `100% dropped`, do NOT continue. Go back to Step 2 and do a full clean restart.
> Run `sudo mn -c` first, then restart Ryu, then Flask, then Mininet again.

---

### 🪟 STEP 6 — Start React Dashboard (Windows Terminal)

Open a terminal on your **Windows machine** inside the project folder:

```bash
cd dashboard
npm run dev
```

Open your browser to: **http://localhost:5173**

Click the **"Live Flask API"** button at the top right of the dashboard.

**✅ The yellow "Flask API Notice" warning should disappear**, confirming the connection to Ubuntu is live.

---

## 🎬 Running the Demonstration

### Act 1 — Normal Traffic (Baseline)

At the `mininet>` prompt in Ubuntu Terminal 3:

```bash
mininet> h1 bash network/legit_traffic.sh
```

**What you should see on the Windows dashboard:**
- The blue line on the chart draws steady traffic (~800 PPS)
- System status shows **"Normal Operation"** with a green dot
- Total Ingress shows a non-zero PPS value

---

### Act 2 — Launch the DDoS Attack

At the `mininet>` prompt, open a terminal for the attacker:

```bash
mininet> xterm h2
```

A small black terminal window will appear. Type inside it:

```bash
sudo hping3 --flood --udp -p 80 10.0.0.3
```

**What you should see on the Windows dashboard:**
- The blue line **spikes past 8,000 PPS** (the orange detection threshold line)
- Status changes to **"Under DDoS Attack"** with a red pulsing dot
- The attacker IP `10.0.0.2` appears in the **Blocked IPs** table

---

### Act 3 — Watch the Autonomous Defense

Within 3 seconds of the attack starting, **without any manual command:**

- Ryu prints: `DDoS Detected from 10.0.0.2! Pushing drop rule...`
- The OpenFlow DROP rule is installed at Priority 65535
- Traffic from `10.0.0.2` is blocked at the switch level

**The proof:** The legitimate iperf traffic from h1 continues running perfectly.

---

### Act 4 — Stop the Attack (Recovery)

Press `Ctrl+C` inside the xterm h2 window to stop hping3.

**What you should see:**
- The blue line drops back to the baseline (~800 PPS)
- Status returns to **"Normal Operation"**
- `10.0.0.2` remains in the blocked table (the idle_timeout is 300 seconds)

---

## 🛑 Shutdown (End of Session)

1. Press `Ctrl+C` in the xterm h2 window (if attack is running)
2. Type `exit` at the `mininet>` prompt in Terminal 3
3. Press `Ctrl+C` in Terminal 2 (Flask)
4. Press `Ctrl+C` in Terminal 1 (Ryu)
5. Run cleanup: `sudo mn -c`
6. Press `Ctrl+C` in your Windows terminal (React)

---

## 🔧 Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `pingall` shows 100% dropped | Ryu and switch out of sync | `sudo mn -c`, restart Ryu first, then Mininet |
| Dashboard shows "Failed to Fetch" | Wrong VM IP in config.js | Run `hostname -I` in Ubuntu, update `src/api/config.js` BASE_URL |
| Total Ingress shows 0 pps | MAC learning not done | Run `pingall` first, then `legit_traffic.sh` |
| `ryu-manager` command not found | Virtual env not activated | Run `source ryu39_env/bin/activate` |
| `ModuleNotFoundError: filelock` | Library missing | Run `pip install filelock` inside activated venv |
| `AttributeError: collections.MutableMapping` | Wrong Python version | Make sure you used `python3.9 -m venv ryu39_env` |
| `ImportError: cannot import ALREADY_HANDLED` | Wrong eventlet version | Run `pip install eventlet==0.30.2` |
| `xterm h2` window doesn't open | No display server in VM | In VMware, ensure you are using a full Desktop install, not a server install |
| Chart not updating in Live mode | Not clicked "Live Flask API" | Click the green "Live Flask API" toggle in the dashboard header |

---

## 📡 Network Reference

| Host | IP | MAC | Role |
|------|----|-----|------|
| h1 | `10.0.0.1` | `00:00:00:00:00:01` | Legitimate User |
| h2 | `10.0.0.2` | `00:00:00:00:00:02` | Attacker |
| h3 | `10.0.0.3` | `00:00:00:00:00:03` | Web Server |
| s1 | — | — | OVS Switch |
| Ryu | `127.0.0.1:6653` | — | SDN Controller |
| Flask | `0.0.0.0:5000` | — | REST API |
| React | `localhost:5173` | — | Dashboard |

---

## 🔑 Quick Reference — Key Commands

```bash
# Check Ubuntu VM IP (to put in config.js on Windows)
hostname -I

# Activate Python environment (run before Ryu and Flask every time)
source ryu39_env/bin/activate

# Clean Mininet state (run before starting Mininet)
sudo mn -c

# Start Ryu
ryu-manager controller/simple_monitor.py

# Start Flask (from inside backend_api folder)
python3 app.py

# Start Mininet
sudo python3 network/topo.py

# Test all hosts can communicate
mininet> pingall

# Start legitimate traffic from h1
mininet> h1 bash network/legit_traffic.sh

# Open attacker terminal
mininet> xterm h2

# Launch DDoS attack (run inside xterm h2)
sudo hping3 --flood --udp -p 80 10.0.0.3

# Check active OpenFlow rules in switch
mininet> sh ovs-ofctl dump-flows s1
```
