# SDN-Based DDoS Detection and Mitigation System

> **Academic Project | 3-Member Team | 12-Week Execution Plan**

A smart network defense system that detects volumetric DDoS attacks in real time and autonomously blocks them at the SDN switch edge — without dropping legitimate user traffic.

---

## Quick Navigation

| Document | Who Should Read It | What It Covers |
|---|---|---|
| `docs/PRD.md` | Everyone | Problem, solution, features, success metrics |
| `docs/SRS.md` | Everyone | All functional & non-functional requirements (FR-001 to FR-015) |
| `docs/ARCHITECTURE.md` | Everyone | System diagrams — component, sequence, data flow, state machine |
| `docs/API_SCHEMA.md` | Lead + Friend 2 | Exact JSON contract between Flask API and React dashboard |
| `docs/TEAM_PLAN.md` | Everyone | Who owns what, week-by-week tasks, acceptance criteria per member |
| `docs/SDLC_PHASES.md` | Everyone | 3-phase plan, integration checkpoints, testing checklists |
| `docs/DEMO_SCRIPT.md` | Everyone | Final presentation script, Q&A prep, backup plans |

---

## Team Structure

| Member | Role | Owns | Key Output |
|---|---|---|---|
| **You (Lead)** | Backend & ML Engineer | /controller/, /backend_api/, /ml_pipeline/ | Ryu controller + Flask API + trained detector.joblib |
| **Friend 1** | Network & Traffic Engineer | /network/ | topo.py, legit_traffic.sh, attack_traffic.sh |
| **Friend 2** | Frontend & QA Engineer | /dashboard/ | React dashboard + integration test results |

---

## Milestone Summary

| Phase | Weeks | Target | Definition of Done |
|---|---|---|---|
| Phase 1 | 1-4 | **45%** | Network alive, CSV logging data, React shows mock chart |
| Phase 2 | 5-8 | **70%** | ML detects attack, Flask API live, dashboard updates in real time |
| Phase 3 | 9-12 | **100%** | Autonomous ML inference, polished UI, benchmarks recorded, demo-ready |

---

## Critical Dependencies Between Members

```
Day 1:   Lead -> Friend 2   Deliver docs/API_SCHEMA.md (JSON contract)
Week 2:  Friend 1 -> Lead   Confirm topo.py connects to Ryu on port 6653
Week 4:  Friend 1 -> Lead   Run traffic scripts so CSV captures training data
Week 7:  Lead -> Friend 2   Flask API running on localhost:5000
Week 11: Friend 1 -> Friend 2   Run hping3 attack for UI stress testing
```

---

## Getting Started — First Action Per Member

### Lead (You):
```bash
python -m venv ryu-env
ryu-env\Scripts\activate
pip install ryu flask flask-cors scikit-learn pandas numpy joblib jupyter
ryu-manager ryu.app.simple_switch_13
```

### Friend 1 (Ubuntu VM):
```bash
sudo apt update && sudo apt install -y mininet openvswitch-switch hping3 iperf python3
sudo mn --test pingall
```

### Friend 2:
```bash
node --version   # Must be 18+
npm create vite@latest dashboard -- --template react
cd dashboard && npm install tailwindcss recharts axios
npm run dev      # Open localhost:5173
```

---

> **READ docs/TEAM_PLAN.md before writing any code.**
> It tells each member exactly what to build, in what order, and how to verify it works.

---

## 🚨 CRITICAL TEAM WARNINGS (READ BEFORE STARTING)

1. **The IP Address Trap:** If Friend 1 is using a Virtual Machine for Mininet, and Lead is running the Controller on the Host PC, Mininet **CANNOT** connect to `127.0.0.1`. The VM network adapter must be set to "Bridged", and Friend 1 must use the Lead's real IPv4 address (e.g., `192.168.x.x`) in the `topo.py` script.
2. **Data Labeling Coordination:** In Week 4, when logging the baseline CSV, the Controller doesn't know what an attack is yet. Friend 1 MUST record the exact clock time they run the attack script (e.g., "14:05:00 to 14:07:00") and give those times to the Lead. The Lead will use those timestamps to manually label the CSV (`1` for Attack, `0` for Normal) before training the ML model.
