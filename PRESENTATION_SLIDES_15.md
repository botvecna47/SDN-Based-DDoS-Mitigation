# SDN-Based DDoS Detection & Mitigation: 15-Slide Presentation Deck

> **Presentation File:** [`SDN_DDoS_ML_Pipeline_Presentation.pptx`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/SDN_DDoS_ML_Pipeline_Presentation.pptx)  
> **Format:** 16:9 Widescreen | Enterprise Dark Theme (Navy `#0F172A`, Cyan `#0EA5E9`, Emerald `#10B981`)  
> **Target Audience:** SDN Engineers, Security Architects, Machine Learning Practitioners

---

## Slide 1: Title Slide
- **Title:** SDN-Based DDoS Detection & Mitigation
- **Subtitle:** Autonomous Machine Learning Pipeline, Sequence Modeling & Real-Time OpenFlow Mitigation
- **Pill Badge:** Research & Deployment
- **Key Metadata:**
  - **Dataset:** UNB CIC-DDoS2019 (11 DDoS attack categories, 207,444 processed flows)
  - **Models Evaluated:** Logistic Regression, Decision Tree, Random Forest, XGBoost, 2-Layer LSTM
  - **Target Controller:** Ryu SDN OpenFlow 1.3 Controller | **SLA:** $< 5.0$ ms / packet
- **Speaker Notes:** Introduce the project scope: building a machine learning defense pipeline directly integrated with an SDN controller to detect and block DDoS attacks with sub-millisecond decision latency.

---

## Slide 2: Executive Summary & Project Objectives
- **Left Panel (The SDN Security Challenge):**
  - **Control Plane Saturation:** DDoS floods overwhelm the OpenFlow channel and controller CPU via rapid `Packet-In` events.
  - **Multi-Vector Diversity:** Attackers combine reflection floods (DNS, NTP, SNMP, TFTP) with protocol floods (SYN, UDP-lag).
  - **Strict Real-Time SLA:** SDN switches require flow routing decisions in $< 5.0$ ms to prevent line-rate buffer drops.
  - **Zero False-Drop Tolerance:** Legitimate enterprise traffic must not be dropped ($\text{FPR} < 0.1\%$).
- **Right Panel (Core Technical Objectives):**
  - **Automated Ingestion:** Stream, clean, deduplicate, and balance 11 categories into 22 optimized Parquet splits.
  - **Statistical Feature Selection:** Reduce 81 raw flow dimensions to 28 features via ANOVA $F$-test without data leakage.
  - **Dual-Paradigm Modeling:** Train 4 multi-threaded tabular algorithms alongside a 3D temporal sequence LSTM on GPU.
  - **Ryu Controller Deployment:** Package the optimal model into a sub-millisecond `predict_packet()` function.

---

## Slide 3: System Architecture & Hardware Optimization Profile
- **Column 1 (Local Hardware Profile):**
  - **Host RAM:** 16 GB DDR4/DDR5
  - **RAM Optimization:** Chunked streaming (50k rows) + `float32`/`int32` downcasting saving $50\%$ memory footprint.
  - **GPU Accelerator:** NVIDIA RTX 5050 (8GB VRAM, Blackwell Architecture)
  - **VRAM Optimization:** Dynamic memory growth + 256 mini-batching prevents CUDA OOM errors.
  - **CPU Multiprocessing:** `n_jobs=-1` configured across all tabular estimators.
- **Column 2 (ML Pipeline Stages):**
  - **Phase 1:** 22 balanced Parquet splits + ANOVA $F$-test feature selection (top 28 features).
  - **Phase 2:** Multi-threaded tabular training (LR, DT, RF, XGBoost).
  - **Phase 3:** 3D sliding temporal reshape + 2-layer LSTM on RTX 5050.
  - **Phase 4:** Unified evaluation, latency profiling, FPR calculation, blinded test, and 6 visual diagnostic figures.
  - **Phase 5:** Serialized `.joblib`/`.keras` weights + standalone `predict.py`.
- **Column 3 (SDN Control Plane Integration):**
  - **Ryu Controller:** OpenFlow 1.3 asynchronous event-driven architecture.
  - **Telemetry Extractor:** Extracts bidirectional metrics from `OFPFlowStatsReply` events.
  - **Fast-Path Inference:** In-memory cached scaler and model classifies in $< 0.6$ ms.
  - **Automated Mitigation:** Installs prioritized OpenFlow Drop rules (`OFPFlowMod`) to isolate attackers at the switch level.

---

## Slide 4: Dataset Ingestion & 70/30 Parquet Splitting (Phase 1)
- **Left Panel (Data Cleaning & Noise Removal):**
  - **Metadata Noise Stripping:** Dropped non-generalizable identifiers (`Unnamed: 0`, `Flow ID`, `Source IP`, `Destination IP`, `Timestamp`, `SimillarHTTP`) to prevent overfitting.
  - **Mathematical Anomaly Imputation:** Replaced `+inf`/`-inf` and `NaN` flow rate errors with training column medians.
  - **Retransmission Deduplication:** Eliminated duplicated packet captures via `.drop_duplicates()`.
  - **Class Balancing:** Balanced `BENIGN` and `Attack` flows per category to eliminate majority class bias.
  - **Zero Data Leakage:** Scaler and selector fit strictly on the 70% training split.
- **Right Panel (22 Parquet Splits Table):**
  - Overall Split: **70% Training (145,207 flows)** vs. **30% Testing (62,237 flows)** across all 11 categories:
    `DNS`, `LDAP`, `MSSQL`, `NTP`, `NetBIOS`, `SNMP`, `SSDP`, `UDP`, `SYN`, `TFTP`, and `UDPLag`.

---

## Slide 5: Statistical Feature Selection via ANOVA F-Test (Phase 1)
- **Left Panel (Why ANOVA F-Test?):**
  - **Variance Analysis:** Evaluates variance-between-groups vs. variance-within-groups ($F$-score) to isolate statistically significant discriminators.
  - **Noise Elimination:** Prunes 53 uninformative counters, zero-variance bulk placeholders, and noisy metrics.
  - **SDN Latency Reduction:** Extracting 28 features instead of 81 slashes packet inspection time by $65\%$ in the controller.
- **Right Panel (Top 28 Selected Features):**
  - **Port & Protocol:** `Source Port`, `Destination Port`, `Protocol`
  - **Flow Rates:** `Flow Bytes/s`, `Flow Packets/s`, `Fwd Packets/s`, `Bwd IAT Total`
  - **Packet Length Stats:** `Fwd/Bwd Packet Length (Max, Min, Mean, Std)`, `Average Packet Size`, `Min Packet Length`, `Packet Length (Mean, Std)`
  - **TCP Flags & Handshake:** `RST Flag Count`, `URG Flag Count`, `CWE Flag Count`, `Fwd PSH Flags`
  - **TCP Window & Segments:** `Init_Win_bytes_forward`, `Init_Win_bytes_backward`, `Avg Fwd/Bwd Segment Size`
  - **Directional Vectors:** `Inbound`, `Down/Up Ratio`

---

## Slide 6: Tabular Model Development & Training (Phase 2)
- **Model Development Matrix:**

| Model Architecture | Algorithm Paradigm | Hyperparameters | Core Utilization | Role in SDN Project |
|---|---|---|---|---|
| **Logistic Regression** | Linear Classifier | `solver='lbfgs', max_iter=1000` | Multi-Threaded | Lightweight, ultra-fast baseline |
| **Decision Tree** | CART Greedy Splitting | `max_depth=8, min_samples_split=20` | Single Core | Interpretable rules & lowest latency |
| **Random Forest** | Bagged Ensemble (100 Trees) | `n_estimators=100, max_depth=16` | `n_jobs=-1` (All Cores) | Existing baseline ensemble for stability |
| **XGBoost** | Gradient Boosted Trees | `tree_method='hist', lr=0.1, n_est=100` | `n_jobs=-1` (All Cores) | State-of-the-art tabular classification |

- **Key Highlights:**
  - Multi-threaded execution across 145,207 training flows completed in under 2 minutes.
  - Explores linear, single-tree, ensemble, and boosted paradigms to evaluate the optimal trade-off between accuracy and latency.

---

## Slide 7: Decision Tree Rule Extraction & Logic (Phase 2)
- **Visual Artifact:** Embedded [`tree_rules.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/tree_rules.png)
- **Domain Logic Extracted by CART:**
  - **Root Split (`Inbound <= -0.64`):** Isolates external reflective DDoS traffic arriving from reflector hosts vs. internal benign traffic.
  - **Destination & Source Port:** Detects service-port reflection (DNS 53, NTP 123, TFTP 69, MSSQL 1433) and ephemeral target floods.
  - **Min Packet Length & Flow Bytes/s:** Identifies amplification packet payloads with uniform burst sizes.
  - **Init_Win_bytes_backward:** Detects spoofed floods where victims cannot establish TCP 3-way handshakes.
  - **Auditable Security:** White-box decision boundaries allow network operators to verify ML decisions against network physics.

---

## Slide 8: Deep Sequence Modeling: 2-Layer LSTM on RTX 5050 (Phase 3)
- **Left Panel (Architecture & Tensor Reshaping):**
  - **3D Tensor Reshaping:** Sliding window converting 2D flows to `(samples, 10 time_steps, 28 features)`.
  - **Layer 1:** `LSTM(64 units, return_sequences=True)` + `Dropout(0.2)` + `BatchNormalization()`
  - **Layer 2:** `LSTM(64 units, return_sequences=False)` + `Dropout(0.2)` + `BatchNormalization()`
  - **Dense Head:** `Dense(32, activation='relu')` $\to$ `Dense(1, activation='sigmoid')`
  - **Loss & Optimizer:** Binary cross-entropy with Adam optimizer (`lr=0.001`).
- **Right Panel (GPU Acceleration & Memory Management):**
  - **NVIDIA RTX 5050 (8GB VRAM):** Blackwell Tensor Cores utilized via dynamic GPU memory growth.
  - **Mini-Batching (Batch Size 256):** Prevents OOM crashes while sustaining high tensor throughput.
  - **Callbacks:** `EarlyStopping(patience=3)` restored best weights; `ModelCheckpoint` saved `best_lstm.keras`.
  - **Dual Export:** Exported both modern `.keras` and legacy `.h5` formats.

---

## Slide 9: Comprehensive Model Evaluation Matrix (Phase 4)
- **Visual Artifact:** Embedded [`testing_evaluation_matrix.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/testing_evaluation_matrix.png)
- **Testing Performance Matrix (62,237 Unseen Test Flows):**

| Model | Accuracy | Precision | Recall | Macro F1 | Weighted F1 | False Positive Rate (FPR) | Latency (ms/packet) | SDN SLA Status |
|---|---|---|---|---|---|---|---|---|
| **Decision Tree (Selected Best)** | **99.99%** | **99.99%** | **99.99%** | **99.99%** | **99.99%** | **0.02%** | **0.142 ms** | **PASSED (< 5ms)** |
| **XGBoost** | 99.99% | 99.99% | 99.99% | 99.99% | 99.99% | 0.02% | 0.525 ms | **PASSED (< 5ms)** |
| **Random Forest** | 99.99% | 99.99% | 99.99% | 99.99% | 99.99% | 0.006% | 36.87 ms | Slower than SLA |
| **LSTM (Neural)** | 99.87% | 99.86% | 99.97% | 99.84% | 99.87% | 0.38% | 91.64 ms | Slower than SLA |
| **Logistic Regression** | 98.90% | 99.46% | 99.04% | 98.62% | 98.91% | 1.45% | 0.175 ms | **PASSED (< 5ms)** |

- **Key Takeaways:**
  - Decision Tree and XGBoost deliver state-of-the-art accuracy ($99.99\%$) with an FPR of $0.02\%$.
  - Decision Tree executes in **$0.142$ ms**, making it the clear choice for line-rate OpenFlow deployment.

---

## Slide 10: Confusion Matrices for All Models (Phase 4)
- **Visual Artifact:** Embedded [`confusion_matrices_all_models.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/confusion_matrices_all_models.png)
- **Diagnostic Insights:**
  - **Near-Zero False Alarms:** Decision Tree and XGBoost misclassified fewer than 15 benign packets out of 62,237 test packets.
  - **Near-Zero False Negatives:** Malicious volumetric floods were intercepted immediately (Recall $> 99.99\%$).
  - **Linear Baseline Limitations:** Logistic Regression produced a $1.45\%$ FPR, demonstrating that linear hyperplanes cannot capture complex DDoS dynamics.

---

## Slide 11: Per-Attack Category Performance Breakdown (Phase 4)
- **Visual Artifact:** Embedded [`confusion_matrices_per_attack.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/confusion_matrices_per_attack.png)
- **11 Attack Vectors Verified:**
  - **Reflection Vectors:** $100.0\%$ detection on DNS, NTP, SNMP, MSSQL, SSDP, and TFTP.
  - **Direct Floods:** $100.0\%$ detection on SYN, UDP, and UDP-lag volumetric floods.
  - **Complex Vectors:** $> 99.8\%$ precision on LDAP and NetBIOS attacks.
  - **Unified Security:** A single trained model protects against both application-layer reflection and transport-layer flooding.

---

## Slide 12: ROC-AUC & Precision-Recall Diagnostic Curves (Phase 4)
- **Visual Artifact:** Embedded [`combined_roc_pr_curves.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/combined_roc_pr_curves.png)
- **Discrimination Power:**
  - **ROC-AUC $\approx 1.000$:** Decision Tree, Random Forest, and XGBoost reach near-perfect Area Under the ROC Curve.
  - **Precision-Recall AP $\approx 1.000$:** Average Precision confirms zero degradation under realistic traffic balances.
  - **Threshold Stability:** Large margins of separation allow operators to adjust detection sensitivity without causing false drops.

---

## Slide 13: Overfitting & Generalization Test (Validation)
- **Visual Artifacts:** Embedded [`overfitting_diagnostic_matrix.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/overfitting_diagnostic_matrix.png) and [`overfitting_train_vs_test.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/overfitting_train_vs_test.png)
- **Overfitting Analysis Matrix (145k Train vs. 62k Test Flows):**

| Model | Train Accuracy | Unseen Test Accuracy | Accuracy Delta ($\text{Train} - \text{Test}$) | Train F1 | Unseen Test F1 | F1 Delta ($\text{Train} - \text{Test}$) | Overfitting Status |
|---|---|---|---|---|---|---|---|
| **Decision Tree** | 99.992% | **99.990%** | $+0.0016\%$ | 99.995% | **99.993%** | $+0.0011\%$ | **Optimal Fit (No Overfitting)** |
| **Random Forest** | 100.00% | **99.990%** | $+0.0096\%$ | 100.00% | **99.993%** | $+0.0066\%$ | **Optimal Fit (No Overfitting)** |
| **XGBoost** | 99.998% | **99.990%** | $+0.0076\%$ | 99.999% | **99.993%** | $+0.0052\%$ | **Optimal Fit (No Overfitting)** |
| **LSTM (Neural)** | 99.486% | **99.875%** | $-0.3887\%$ | 99.647% | **99.914%** | $-0.2674\%$ | **Optimal Fit (No Overfitting)** |
| **Logistic Regression** | 98.852% | **98.904%** | $-0.0522\%$ | 99.211% | **99.247%** | $-0.0360\%$ | **Optimal Fit (No Overfitting)** |

- **Blinded Zero-Day Test (NTP Completely Held Out):**
  - **Decision Tree:** $99.97\%$ Accuracy | $100.0\%$ Recall
  - **XGBoost:** $99.96\%$ Accuracy | $99.99\%$ Recall
  - **Random Forest:** $99.98\%$ Accuracy | $99.98\%$ Recall
  - **Conclusion:** Confirms true generalization against completely unseen zero-day DDoS attack categories.

---

## Slide 14: SDN Deployment Trade-Off: Accuracy vs. Latency (Phase 5)
- **Visual Artifact:** Embedded [`accuracy_vs_latency.png`](file:///g:/Tejas/Project/SDN-Based%20DDoS%20Detection%20&%20Mitigation/visualizations/accuracy_vs_latency.png)
- **Why Latency Dictates Model Selection:**
  - **The 5.0 ms SLA Constraint:** Flow-table rules must be installed before OpenFlow switch packet buffers overflow.
  - **Decision Tree ($0.142$ ms):** Provides a $35\times$ safety margin under high-packet-rate spikes.
  - **XGBoost ($0.525$ ms):** Viable secondary candidate with high robustness.
  - **Random Forest ($36.87$ ms) & LSTM ($91.64$ ms):** Cannot meet the real-time $< 5.0$ ms SLA despite high accuracy due to recursive tree lookups and sequential recurrence.
  - **Winning Model:** Decision Tree selected as `best_sdn_model.joblib`.

---

## Slide 15: Production Packaging & Ryu Controller Integration (Phase 5)
- **Left Panel (`predict.py` Module Verification):**
  - **Callable Function:** `predict_packet(packet_data)` accepts dicts, numpy arrays, or pandas Series.
  - **In-Memory Caching:** Pre-loads model and scaler once on controller startup.
  - **Measured Average Latency:** **$0.578$ ms / packet** (benchmarked over 500 packets).
  - **99th Percentile Latency:** **$0.649$ ms / packet** (zero latency spikes).
  - **Ryu Controller SLA:** **PASSED ($< 5.0$ ms)**.
  - **Output Contract:**
    ```python
    {
        "is_ddos": True,
        "label": "ATTACK",
        "confidence": 1.0,
        "latency_ms": 0.568,
        "action": "DROP"  # or "FORWARD"
    }
    ```
- **Right Panel (Ryu Controller OpenFlow Mitigation Architecture):**
  - **Event Hooking:** Placed in `EventOFPFlowStatsReply` and `EventOFPPacketIn` handlers.
  - **Autonomous Drop Rule:** Installs `OFPFlowMod` with `OFPIT_APPLY_ACTIONS` (empty action list = drop).
  - **Priority Override:** Priority 1000 overrides default forwarding for the offending flow match.
  - **Hard Timeout Expiry:** 60s hard timeout prevents stale flow table rule accumulation.
  - **Repository State:** All code and artifacts committed and pushed to `botvecna47/SDN-Based-DDoS-Mitigation` at branch `mlbranch`.

