# SDLC Execution Plan
## SDN-Based DDoS Detection and Mitigation System

---

## Phase Overview

| Phase | Weeks | Milestone Target | Sprint Goal |
|---|---|---|---|
| **Phase 1** | 1-4 | **45%** | Environment alive, traffic flowing, data being logged, UI skeleton ready |
| **Phase 2** | 5-8 | **70%** | Detection working, API serving data, dashboard showing live state |
| **Phase 3** | 9-12 | **100%** | Autonomous ML-driven mitigation, polished demo, benchmarks recorded |

---

## PHASE 1: Environment & Baseline (Weeks 1-4)
### Target: 45% Complete

### Sprint Goal
By the end of Week 4, **ALL** of the following must be simultaneously true:
- `sudo python3 topo.py` creates the Mininet network and connects to Ryu with no errors
- Ryu console shows `OFPStateChange` with `s1` handshake
- `legit_traffic.sh` runs and the CSV file grows with 100-300 PPS rows every second
- `localhost:5173` shows React app with animated mock chart

---

### Installation Checklist

#### Lead — Backend & ML Engineer (Windows / Linux)

| Software | Command to Install | How to Verify |
|---|---|---|
| Python 3.8+ | System package manager or python.org | `python3 --version` -> 3.8.x or higher |
| Virtual environment | `python3 -m venv venv` | Directory `venv/` created |
| Ryu SDN Framework | `pip install ryu` | `ryu-manager --version` |
| Scikit-Learn | `pip install scikit-learn` | `python3 -c "import sklearn; print(sklearn.__version__)"` |
| Pandas | `pip install pandas` | `python3 -c "import pandas"` |
| NumPy | `pip install numpy` | `python3 -c "import numpy"` |
| Joblib | `pip install joblib` | `python3 -c "import joblib"` |
| Flask | `pip install flask` | `python3 -c "import flask"` |
| Flask-CORS | `pip install flask-cors` | `python3 -c "import flask_cors"` |
| Jupyter Notebook | `pip install jupyter` | `jupyter notebook --version` |

#### Friend 1 — Network & Traffic Engineer (Ubuntu VM)

| Software | Command to Install | How to Verify |
|---|---|---|
| Ubuntu 20.04 / 22.04 LTS | VirtualBox -> New VM | `lsb_release -a` |
| Mininet | `sudo apt install mininet -y` | `sudo mn --version` |
| Open vSwitch | `sudo apt install openvswitch-switch -y` | `ovs-vsctl --version` |
| hping3 | `sudo apt install hping3 -y` | `hping3 --version` |
| iperf | `sudo apt install iperf -y` | `iperf --version` |
| Python 3 | Pre-installed | `python3 --version` |

#### Friend 2 — Frontend & QA Engineer (Any OS)

| Software | Command to Install | How to Verify |
|---|---|---|
| Node.js 18+ | nodejs.org -> LTS installer | `node --version` -> v18.x or higher |
| npm | Comes with Node.js | `npm --version` |
| VS Code | code.visualstudio.com | Launch and confirm version |
| Postman | postman.com/downloads | Launch and create a workspace |
| Vite + React | `npm create vite@latest dashboard -- --template react` | `npm run dev` -> `localhost:5173` loads |
| Tailwind CSS | `npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p` | Styled blank page at `localhost:5173` |
| Recharts | `npm install recharts` | `node -e "require('recharts')"` |
| Axios | `npm install axios` | `node -e "require('axios')"` |

---

### Week-by-Week Breakdown — Phase 1

#### Week 1

| Member | Tasks |
|---|---|
| **Lead** | Create Python venv; install all packages; run `ryu-manager ryu.app.simple_switch_13`; draft `API_SCHEMA.md` and share with Friend 2 |
| **Friend 1** | Install Ubuntu VM; install Mininet, OVS, hping3, iperf; run `sudo mn --test pingall` |
| **Friend 2** | Scaffold Vite+React project; install Tailwind; read `API_SCHEMA.md`; create `mockData.json` |

#### Week 2

| Member | Tasks |
|---|---|
| **Lead** | Implement `OFPFlowStatsRequest` polling loop; print raw stats every ~1.5 seconds |
| **Friend 1** | Write `topo.py` (h1, h2, h3, s1 -> remote controller `127.0.0.1:6653`); run topology; confirm `h1 ping h3` works |
| **Friend 2** | Build three empty card components: `TrafficLineChart`, `SystemHealthBadge`, `BlockedIPsTable` |

#### Week 3

| Member | Tasks |
|---|---|
| **Lead** | Build CSV logger: `timestamp, src_ip, dst_ip, packet_count, byte_count, duration_sec, pps, bps` |
| **Friend 1** | Write `legit_traffic.sh` using `iperf` client on `h1` -> `h3`; verify steady baseline PPS |
| **Friend 2** | Integrate Recharts into `TrafficLineChart`; wire `setInterval` mock data every 1 second |

#### Week 4

| Member | Tasks |
|---|---|
| **Lead** | Coordinate data capture session; ensure CSV captures both normal and attack rows |
| **Friend 1** | Write and run `attack_traffic.sh` (`hping3 --flood --udp -p 80 10.0.0.3`); spike PPS >20,000 |
| **Friend 2** | Build `BlockedIPsTable` with `DROPPED` badges; build all three `SystemHealthBadge` states with hardcoded data |

---

### Phase 1 Integration Checkpoint (End of Week 4)

Run this sequence **together** on a call or in person:

1. **Friend 1 runs:** `sudo python3 topo.py`
2. **Lead confirms:** Ryu console shows `OFPStateChange` for switch `s1`
3. **Friend 1 runs:** `legit_traffic.sh` from `h1`
4. **Lead confirms:** CSV file (`traffic_log.csv`) is growing with new rows containing 100-300 PPS values
5. **Friend 1 runs:** `attack_traffic.sh` briefly from `h2`
6. **Lead confirms:** CSV rows spike to >20,000 PPS
7. **Friend 2 demonstrates:** `localhost:5173` shows animated chart with mock data; all three components visible
8. **Lead shares:** `API_SCHEMA.md` is complete and confirmed with Friend 2

Checkpoint passes when all 8 items confirmed.

---

### Phase 1 — Common Blockers & Solutions

| Blocker | Likely Cause | Solution |
|---|---|---|
| Ryu does not find `s1` | Controller IP in `topo.py` is wrong | Confirm Ryu and Mininet are on same machine; check `127.0.0.1:6653` in `topo.py` |
| OpenFlow version mismatch | `topo.py` using OFP 1.0, Ryu app uses 1.3 | Add `protocols=OpenFlow13` in `topo.py`; import `ofproto_v1_3` in Ryu app |
| React app not starting | Node.js version too old | Run `node --version`; install Node 18+ from nodejs.org |
| hping3 not flooding | Missing `sudo` | Run `sudo hping3 --flood ...` inside Mininet `h2` context |
| CSV not growing | Logger thread not started | Ensure polling thread is launched with `hub.spawn()` or `threading.Thread` |
| `mn --test pingall` fails | OVS not running | Run `sudo service openvswitch-switch start` |

---

## PHASE 2: Detection, API & Integration (Weeks 5-8)
### Target: 70% Complete

### Sprint Goal
By the end of Week 8, **ALL** of the following must be simultaneously true:
- Run `attack_traffic.sh` -> within **3 seconds** Ryu logs `"DDoS Detected"` and drop rule is installed
- `curl localhost:5000/api/network-stats` returns JSON with `"status": "UNDER_ATTACK"`
- `localhost:5173` chart spikes red automatically without page refresh
- `GET /api/blocked-ips` returns `h2`'s IP in the array
- `h1` can still `ping h3` while `h2` is blocked (< 5% packet loss)

---

### Week-by-Week Breakdown — Phase 2

#### Week 5

| Member | Tasks |
|---|---|
| **Lead** | Label CSV dataset (0=Normal, 1=DDoS); load into Jupyter; plot EDA histograms; check class balance |
| **Friend 1** | Run extended data collection sessions (aim: >=10,000 total labeled rows) |
| **Friend 2** | Replace `setInterval` mock with Axios polling `GET /api/network-stats`; wire `SystemHealthBadge` to `status` field |

#### Week 6

| Member | Tasks |
|---|---|
| **Lead** | Train `RandomForestClassifier`; tune hyperparameters; export `detector.joblib`; validate metrics |
| **Friend 1** | Continue data collection; test additional attack vectors (SYN flood, ICMP flood) |
| **Friend 2** | Handle API-not-running state gracefully; add "Controller Offline" placeholder state |

#### Week 7

| Member | Tasks |
|---|---|
| **Lead** | Implement `OFPFlowMod` drop rule method; manually test it; build Flask API with `/api/network-stats` and `/api/blocked-ips`; add CORS |
| **Friend 1** | Run attack; wait for drop rule; validate with `ovs-ofctl dump-flows s1`; measure `h1` packet loss |
| **Friend 2** | Wire `BlockedIPsTable` to `GET /api/blocked-ips`; limit chart buffer to last 30 points |

#### Week 8

| Member | Tasks |
|---|---|
| **Lead** | Wire Flask API to shared state from Ryu thread; test all endpoints with Postman |
| **Friend 1** | Formally measure mitigation time; document packet loss results |
| **Friend 2** | Add pulsing red header on `UNDER_ATTACK`; add Controller Offline toast with auto-retry |

---

### ML Evaluation Checklist

Run these evaluations in Jupyter Notebook before proceeding to Phase 3:

| Metric | Minimum Threshold | Actual (fill in) | Pass? |
|---|---|---|---|
| Classification Accuracy | >= 95% | | [ ] |
| Precision | >= 93% | | [ ] |
| Recall | >= 97% | | [ ] |
| F1-Score | >= 95% | | [ ] |
| False Positive Rate | < 2% | | [ ] |
| Confusion Matrix | Printed with actual numbers | | [ ] |
| Inference Time (single predict) | < 5ms (use `timeit`) | | [ ] |

**How to measure inference time:**
```python
import timeit
import numpy as np

sample_features = np.array([[...]])  # one row of features
time_ms = timeit.timeit(lambda: model.predict(sample_features), number=1000) / 1000 * 1000
print(f"Average inference: {time_ms:.3f} ms")
```

---

### API Testing Checklist

Test every item using Postman or `curl` before declaring API complete:

| Test | Expected Result | Pass? |
|---|---|---|
| `GET /api/network-stats` returns HTTP 200 | Status code = 200 | [ ] |
| Response has `timestamp` field | Valid ISO 8601 string | [ ] |
| Response has `src_ip` field | String (e.g., `"10.0.0.1"`) | [ ] |
| Response has `dst_ip` field | String | [ ] |
| Response has `pps` field | Number | [ ] |
| Response has `bps` field | Number | [ ] |
| Response has `packet_count` field | Number | [ ] |
| Response has `status` field | One of: `"NORMAL"`, `"UNDER_ATTACK"`, `"MITIGATING"` | [ ] |
| `GET /api/blocked-ips` returns HTTP 200 | Status code = 200 | [ ] |
| `/api/blocked-ips` returns **array** | `[...]` not `{...}` | [ ] |
| `/api/blocked-ips` returns `[]` when no IPs blocked | Empty array, not null | [ ] |
| CORS header present on both endpoints | `Access-Control-Allow-Origin: http://localhost:5173` | [ ] |
| `/api/blocked-ips` returns attacker IP during attack | `["10.0.0.2"]` | [ ] |

---

### Phase 2 Integration Checkpoint (End of Week 8)

Run this sequence together, all three members present:

1. **Lead starts:** `ryu-manager /controller/ddos_controller.py`
2. **Lead starts:** `python3 /backend_api/app.py` (Flask on port 5000)
3. **Friend 2 opens:** `localhost:5173` — confirms chart is live with real data
4. **Friend 1 starts:** `sudo python3 topo.py` — confirms `s1` connects to Ryu
5. **Friend 1 runs:** `legit_traffic.sh` for 60 seconds — dashboard shows `NORMAL` state
6. **Friend 1 runs:** `attack_traffic.sh` from `h2`
7. **Everyone observes:**
   - Ryu console logs `"DDoS Detected -- blocking 10.0.0.2"` within 3 seconds
   - `curl localhost:5000/api/network-stats` returns `"status": "UNDER_ATTACK"`
   - Dashboard chart spikes red; `SystemHealthBadge` shows `UNDER_ATTACK`
   - `BlockedIPsTable` shows `10.0.0.2` with red `DROPPED` badge
8. **Friend 1 stops attack** — observes recovery
9. **Friend 1 runs:** `ping -c 20 10.0.0.3` from `h1` during attack — confirms < 5% packet loss

Checkpoint passes when all 9 steps verified.

---

### Phase 2 — Common Blockers & Solutions

| Blocker | Likely Cause | Solution |
|---|---|---|
| Model accuracy < 95% | Too few training rows or class imbalance | Collect more data; use SMOTE for imbalance; tune `n_estimators` |
| Flask and Ryu not sharing state | Running in separate processes | Use `threading.Thread` for Flask inside Ryu; share a `dict` with a `threading.Lock` |
| CORS error in browser console | CORS not configured or wrong origin | `CORS(app, origins=["http://localhost:5173"])` |
| Drop rule not appearing in `ovs-ofctl` | `OFPFlowMod` priority too low | Set `priority=100` to override default forwarding rules |
| Dashboard not updating in real-time | Axios polling interval too long | Reduce to 1000ms; check network tab for request failures |
| `h1` still losing packets after drop rule | Drop rule matches wrong field | Confirm `match.ipv4_src` is set to `h2`'s IP, not `h1`'s |

---

## PHASE 3: ML Integration & Final Polish (Weeks 9-12)
### Target: 100% Complete

### Sprint Goal
**Full autonomy** — attack starts, system detects, blocks, and recovers — all without any manual command. System is demo-ready with benchmarks documented.

---

### Week-by-Week Breakdown — Phase 3

#### Week 9

| Member | Tasks |
|---|---|
| **Lead** | Load `detector.joblib` at Ryu startup; wire `model.predict()` to drop rule in polling loop; test autonomous detection |
| **Friend 1** | Test all three attack vectors (UDP, SYN, ICMP) for autonomous detection; record detection times |
| **Friend 2** | Add pulsing red header animation on `UNDER_ATTACK`; implement green recovery animation; add exponential-backoff auto-retry |

#### Week 10

| Member | Tasks |
|---|---|
| **Lead** | Full end-to-end cycle testing: attack -> detect -> block -> UI update -> recovery; fix race conditions |
| **Friend 1** | Test detection under mixed traffic (legit + attack simultaneously); validate `h1` not impacted |
| **Friend 2** | Final QA: test API disconnect scenario; verify 30-point chart buffer limit; remove all debug `console.log` |

#### Week 11

| Member | Tasks |
|---|---|
| **Lead** | 30-minute stability test (see formal plan below) |
| **Friend 1** | Formal network benchmarking (see formal plan below) |
| **Friend 2** | Dashboard stress test + Postman schema validation (see formal plan below) |

#### Week 12

| Member | Tasks |
|---|---|
| **Lead** | Finalize `README.md`, `requirements.txt`; commit `detector.joblib`; rehearse demo twice |
| **Friend 1** | Commit `benchmarks/network_results.csv`; rehearse demo orchestration; snapshot VM |
| **Friend 2** | Final polish (responsive layout, remove debug code); commit Postman collection; record backup demo video |

---

### Week 11: Formal Testing Plan

#### A. Controller Stability Test — Lead

**Duration:** 30 minutes continuous
**Setup:** Run Ryu + Flask under synthetic traffic load
**Measurements to log every 5 minutes:**

| Measurement | Tool | Target |
|---|---|---|
| Memory usage (RSS) | `psutil` or `top` | Stable (no leak) |
| CPU usage | `top` | < 30% average |
| Active thread count | `threading.active_count()` | Stable |
| Exception count | Try/except counter in code | 0 |
| Inference calls made | Counter in polling loop | Incrementing |

**Pass Criteria:** Zero crashes; zero unhandled exceptions; memory usage within 10% of baseline over 30 minutes.

---

#### B. ML Performance Evaluation — Lead

Run on held-out test set (never seen during training):

| Metric | Tool | Record |
|---|---|---|
| Full confusion matrix | `sklearn.metrics.confusion_matrix` | TP / FP / TN / FN values |
| Accuracy | `accuracy_score` | % |
| Precision | `precision_score` | % |
| Recall | `recall_score` | % |
| F1-Score | `f1_score` | % |
| Per-class inference latency | `timeit` x 1000 samples | ms |

Export results to `benchmarks/ml_evaluation.txt`.

---

#### C. Network Resilience Test — Friend 1

**Run 3 formal attack runs, each with a clean Mininet restart:**

For each run, record:

| Measurement | Method | Target |
|---|---|---|
| Time: attack start -> drop rule installed | Timestamp `attack_traffic.sh` launch; timestamp `ovs-ofctl` shows rule | < 3 seconds |
| `h1` packet loss during attack | `ping -c 100 10.0.0.3` from h1 during attack | < 5% |
| Throughput (h3 before attack) | `iperf -s h3` + `iperf -c 10.0.0.3 h1` | Baseline established |
| Throughput (h3 during attack) | Same `iperf` while hping3 runs | Documented |

Export to `benchmarks/network_results.csv`:
```
run_number,attack_type,detection_time_sec,h1_packet_loss_pct,h3_throughput_before_mbps,h3_throughput_during_mbps
```

---

#### D. Dashboard Stress Test — Friend 2

**During live hping3 flood, with DevTools Performance tab recording:**

| Test | Method | Target |
|---|---|---|
| Frame rate (FPS) | Chrome DevTools -> Performance tab | >= 60 FPS maintained |
| White-screen crash | Watch during 5-minute flood | None |
| Memory growth | Chrome DevTools -> Memory tab | No significant heap growth |
| API disconnect handling | Kill Flask mid-session, observe | Toast appears, auto-retry starts |
| Reconnect handling | Restart Flask, observe | Dashboard resumes without refresh |

**Postman Schema Validation Collection** (all must pass):

```
GET /api/network-stats
  - Status: 200
  - Body has: timestamp (string), src_ip (string), dst_ip (string),
              pps (number), bps (number), packet_count (number), status (string)
  - status in ["NORMAL", "UNDER_ATTACK", "MITIGATING"]

GET /api/blocked-ips
  - Status: 200
  - Body is: array (not object)
  - Body is [] when no attack running

CORS Headers
  - Access-Control-Allow-Origin: http://localhost:5173
```

---

### Week 12: Closing Checklist

Complete every item before demo day:

- [ ] All code pushed to shared GitHub repo
- [ ] `README.md` covers: project overview, architecture diagram, setup steps for all 3 members, how to run demo
- [ ] Folder structure matches: `/network`, `/controller`, `/backend_api`, `/ml_pipeline`, `/dashboard`
- [ ] `requirements.txt` complete for all Python components (`pip freeze > requirements.txt`)
- [ ] `package.json` complete for React (`npm install` must produce working build)
- [ ] `detector.joblib` committed to repo (or add `.gitignore` exception with comment)
- [ ] `benchmarks/network_results.csv` committed with >=3 runs per attack vector
- [ ] `benchmarks/ml_evaluation.txt` committed with full confusion matrix and metrics
- [ ] Final report sections drafted (abstract, architecture, results, conclusion)
- [ ] Demo rehearsal done **at least twice** — once with full attack sequence, once aborting and recovering
- [ ] Backup plan documented (see `DEMO_SCRIPT.md`)
- [ ] VM snapshot taken after final successful test (Friend 1)
- [ ] Pre-recorded backup demo video ready (Friend 2)
- [ ] All team members know their speaking lines for demo

---

> **Weekly Standup Template (15 min, every Monday):**
> 1. What did you finish last week? (Acceptance criteria met?)
> 2. What are you doing this week?
> 3. What do you need from a teammate to proceed?
