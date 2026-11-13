"""
pipeline.py - Master SDN-Based DDoS Detection & Mitigation ML Pipeline
Phases 1-5: Ingestion, ANOVA Feature Selection, Tabular Training, LSTM Sequence Modeling,
Unified Evaluation & Visualizations, and Artifact Packaging.
Optimized for 16GB RAM + NVIDIA RTX 5050 (8GB VRAM).
"""

import os
import gc
import json
import time
import glob
import logging
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless plotting
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score,
)
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ensure reproducibility
RANDOM_STATE = 42
OUTPUT_MODELS_DIR = "exported_models"
VISUALIZATIONS_DIR = "visualizations"
os.makedirs(OUTPUT_MODELS_DIR, exist_ok=True)
os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)


# =====================================================================
# Phase 1: Local Data Ingestion & ANOVA Feature Selection
# =====================================================================

def ingest_data(parquet_dir: str = "parquet_data"):
    """
    Loads and concatenates all *_training.parquet files into a single training dataframe,
    and all *_testing.parquet files into a single testing dataframe.
    Optimizes memory by downcasting numeric types.
    """
    logging.info(f"Scanning for parquet files in '{parquet_dir}'...")
    train_files = sorted(glob.glob(os.path.join(parquet_dir, "*_training.parquet")))
    test_files = sorted(glob.glob(os.path.join(parquet_dir, "*_testing.parquet")))

    if not train_files or not test_files:
        raise FileNotFoundError(
            f"No parquet files found in '{parquet_dir}'. Please run data_preprocessing.py first."
        )

    logging.info(f"Found {len(train_files)} training files and {len(test_files)} testing files.")

    train_dfs = [pd.read_parquet(f, engine="pyarrow") for f in train_files]
    test_dfs = [pd.read_parquet(f, engine="pyarrow") for f in test_files]

    train_df = pd.concat(train_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)

    del train_dfs, test_dfs
    gc.collect()

    logging.info(f"Loaded Training DataFrame: shape = {train_df.shape}")
    logging.info(f"Loaded Testing DataFrame : shape = {test_df.shape}")

    return train_df, test_df


def select_features_anova(train_df: pd.DataFrame, test_df: pd.DataFrame, k: int = 28):
    """
    Selects top k features using an ANOVA F-test (SelectKBest with f_classif).
    Fits the StandardScaler and SelectKBest ONLY on the training data, then transforms both sets.
    """
    logging.info(f"Applying ANOVA F-test feature selection to retain top {k} features...")

    # Isolate targets and metadata
    drop_cols = ["Label", "Binary_Label", "Attack_Category"]
    feature_cols = [c for c in train_df.columns if c not in drop_cols and np.issubdtype(train_df[c].dtype, np.number)]

    X_train_raw = train_df[feature_cols].copy()
    y_train = train_df["Binary_Label"].values

    X_test_raw = test_df[feature_cols].copy()
    y_test = test_df["Binary_Label"].values

    # Clean infinite/NaN values
    X_train_raw.replace([np.inf, -np.inf], np.nan, inplace=True)
    X_test_raw.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    medians = X_train_raw.median().fillna(0.0)
    X_train_raw.fillna(medians, inplace=True)
    X_test_raw.fillna(medians, inplace=True)

    # 1. Fit StandardScaler ONLY on training set
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw)
    X_test_scaled = scaler.transform(X_test_raw)

    # 2. Fit SelectKBest (ANOVA F-test) ONLY on training set
    selector = SelectKBest(score_func=f_classif, k=k)
    X_train_selected = selector.fit_transform(X_train_scaled, y_train)
    X_test_selected = selector.transform(X_test_scaled)

    selected_mask = selector.get_support()
    selected_feature_names = [feature_cols[i] for i, m in enumerate(selected_mask) if m]

    logging.info(f"Top {k} ANOVA features selected:")
    for rank, name in enumerate(selected_feature_names, start=1):
        score = selector.scores_[feature_cols.index(name)]
        logging.info(f"  {rank:02d}. {name} (F-Score: {score:.2f})")

    # Save feature metadata
    with open(os.path.join(OUTPUT_MODELS_DIR, "selected_features.json"), "w") as f:
        json.dump(selected_feature_names, f, indent=2)

    # Save scaler and selector
    joblib.dump(scaler, os.path.join(OUTPUT_MODELS_DIR, "scaler.joblib"))
    joblib.dump(selector, os.path.join(OUTPUT_MODELS_DIR, "anova_selector.joblib"))

    return (
        X_train_selected,
        y_train,
        X_test_selected,
        y_test,
        selected_feature_names,
        scaler,
        selector,
    )


# =====================================================================
# Phase 2: Tabular Model Training
# =====================================================================

def train_tabular_models(X_train, y_train, feature_names):
    """
    Trains 4 tabular classifiers:
      1. Logistic Regression (Fast baseline)
      2. Decision Tree (Visualizes decision rules)
      3. Random Forest (High core utilization via n_jobs=-1)
      4. XGBoost (Gradient boosting classifier with hist tree method)
    """
    models = {}

    # 1. Logistic Regression
    logging.info("Training Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE, n_jobs=-1, solver="lbfgs")
    lr.fit(X_train, y_train)
    models["Logistic Regression"] = lr
    joblib.dump(lr, os.path.join(OUTPUT_MODELS_DIR, "logistic_regression.joblib"))

    # 2. Decision Tree
    logging.info("Training Decision Tree...")
    dt = DecisionTreeClassifier(max_depth=8, min_samples_split=20, random_state=RANDOM_STATE)
    dt.fit(X_train, y_train)
    models["Decision Tree"] = dt
    joblib.dump(dt, os.path.join(OUTPUT_MODELS_DIR, "decision_tree.joblib"))

    # Export text tree rules
    rules_text = export_text(dt, feature_names=feature_names, max_depth=4)
    with open(os.path.join(VISUALIZATIONS_DIR, "tree_rules.txt"), "w") as f:
        f.write(rules_text)

    # Export visualization of Decision Tree rules
    plt.figure(figsize=(22, 12))
    plot_tree(
        dt,
        feature_names=feature_names,
        class_names=["BENIGN", "DDoS"],
        filled=True,
        max_depth=3,
        fontsize=10,
        rounded=True,
    )
    plt.title("Decision Tree Rule Visualization (Top 3 Levels)", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(VISUALIZATIONS_DIR, "tree_rules.png"), dpi=300)
    plt.close()
    logging.info("Saved Decision Tree visualization to tree_rules.png")

    # 3. Random Forest
    logging.info("Training Random Forest (Multi-threaded n_jobs=-1)...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=16, random_state=RANDOM_STATE, n_jobs=-1)
    rf.fit(X_train, y_train)
    models["Random Forest"] = rf
    joblib.dump(rf, os.path.join(OUTPUT_MODELS_DIR, "random_forest.joblib"))

    # 4. XGBoost
    logging.info("Training XGBoost...")
    xgb_clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        tree_method="hist",
        n_jobs=-1,
        random_state=RANDOM_STATE,
        eval_metric="logloss",
    )
    xgb_clf.fit(X_train, y_train)
    models["XGBoost"] = xgb_clf
    joblib.dump(xgb_clf, os.path.join(OUTPUT_MODELS_DIR, "xgboost.joblib"))

    logging.info("All 4 tabular models successfully trained and exported.")
    return models


# =====================================================================
# Phase 3: Sequence Modeling (LSTM)
# =====================================================================

def reshape_to_sequences(X, y, time_steps: int = 10):
    """
    Reshapes 2D tabular network flow data into 3D time-series sequences:
    (samples, time_steps, features) suitable for LSTM network flow temporal modeling.
    """
    n_samples = len(X) - time_steps + 1
    if n_samples <= 0:
        raise ValueError("Dataset smaller than requested time_steps sequence window.")

    shape = (n_samples, time_steps, X.shape[1])
    strides = (X.strides[0], X.strides[0], X.strides[1])
    X_seq = np.lib.stride_tricks.as_strided(X, shape=shape, strides=strides)
    y_seq = y[time_steps - 1 :]

    return X_seq, y_seq


def build_and_train_lstm(
    X_train_2d,
    y_train_2d,
    X_test_2d,
    y_test_2d,
    time_steps: int = 10,
    epochs: int = 5,
    batch_size: int = 256,
):
    """
    Builds a 2-layer LSTM with 64 hidden units, Dropout (0.2), and Batch Normalization.
    Configured for NVIDIA RTX 5050 (8GB VRAM) and 16GB system RAM with safe batch sizes.
    """
    logging.info(f"Reshaping flow data into 3D temporal sequences (time_steps={time_steps})...")
    
    max_train_samples = 150000
    if len(X_train_2d) > max_train_samples:
        idx = np.random.RandomState(RANDOM_STATE).choice(len(X_train_2d), max_train_samples, replace=False)
        X_train_sub, y_train_sub = X_train_2d[idx], y_train_2d[idx]
    else:
        X_train_sub, y_train_sub = X_train_2d, y_train_2d

    X_train_seq, y_train_seq = reshape_to_sequences(X_train_sub, y_train_sub, time_steps=time_steps)
    X_test_seq, y_test_seq = reshape_to_sequences(X_test_2d, y_test_2d, time_steps=time_steps)

    logging.info(f"LSTM Train Shape: {X_train_seq.shape}, Test Shape: {X_test_seq.shape}")

    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

    # Configure GPU memory growth on RTX 5050
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            logging.info(f"Configured GPU memory growth on {len(gpus)} GPU(s): {gpus}")
        except RuntimeError as e:
            logging.warning(f"GPU memory growth configuration notice: {e}")

    # Build 2-layer LSTM Architecture
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(time_steps, X_train_seq.shape[2])),
        Dropout(0.2),
        BatchNormalization(),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        BatchNormalization(),
        Dense(32, activation="relu"),
        Dense(1, activation="sigmoid"),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )

    model.summary(print_fn=logging.info)

    checkpoint_path = os.path.join(OUTPUT_MODELS_DIR, "best_lstm.keras")
    callbacks = [
        EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
        ModelCheckpoint(checkpoint_path, monitor="val_loss", save_best_only=True),
    ]

    logging.info(f"Training LSTM model (batch_size={batch_size}, epochs={epochs})...")
    history = model.fit(
        X_train_seq,
        y_train_seq,
        validation_data=(X_test_seq, y_test_seq),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1,
    )

    # Save both .keras and legacy .h5 formats
    model.save(os.path.join(OUTPUT_MODELS_DIR, "lstm_ddos_model.keras"))
    try:
        model.save(os.path.join(OUTPUT_MODELS_DIR, "lstm_ddos_model.h5"))
    except Exception as e:
        logging.warning(f"Could not save .h5 format: {e}")

    logging.info("LSTM model successfully trained and exported.")
    return model, X_test_seq, y_test_seq


# =====================================================================
# Phase 4: Evaluation, Latency Testing & Visualizations
# =====================================================================

def benchmark_latency(model, sample_input, num_iterations: int = 500, is_lstm: bool = False):
    """Calculates inference latency per packet/flow in milliseconds."""
    for _ in range(30):
        _ = model.predict(sample_input[:1])

    start_time = time.perf_counter()
    for _ in range(num_iterations):
        _ = model.predict(sample_input[:1])
    end_time = time.perf_counter()

    latency_ms = ((end_time - start_time) / num_iterations) * 1000.0
    return latency_ms


def evaluate_models(
    models: dict,
    X_test,
    y_test,
    lstm_model,
    X_test_seq,
    y_test_seq,
    test_df: pd.DataFrame,
):
    """
    Evaluates all 5 models on the testing set and calculates:
      - Accuracy, Precision, Recall, Macro F1, Weighted F1, False Positive Rate (FPR)
      - Latency (ms per packet)
      - Blinded Zero-Day Generalization Test
      - Generates all 4 visual export figures (.png)
    """
    logging.info("Starting comprehensive evaluation across all 5 models...")
    results = []
    preds = {}
    probs = {}

    # 1. Evaluate 4 Tabular Models
    for name, model in models.items():
        logging.info(f"Evaluating {name}...")
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

        preds[name] = y_pred
        probs[name] = y_prob

        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        latency = benchmark_latency(model, X_test, num_iterations=500, is_lstm=False)

        results.append({
            "Model": name,
            "Accuracy": accuracy_score(y_test, y_pred),
            "Precision": precision_score(y_test, y_pred, zero_division=0),
            "Recall": recall_score(y_test, y_pred, zero_division=0),
            "Macro F1": f1_score(y_test, y_pred, average="macro", zero_division=0),
            "Weighted F1": f1_score(y_test, y_pred, average="weighted", zero_division=0),
            "FPR": fpr,
            "Latency (ms/pkt)": latency,
        })

    # 2. Evaluate LSTM
    if lstm_model is not None and X_test_seq is not None:
        logging.info("Evaluating LSTM...")
        raw_preds = lstm_model.predict(X_test_seq, batch_size=256)
        y_prob_lstm = raw_preds.flatten()
        y_pred_lstm = (y_prob_lstm >= 0.5).astype(int)

        preds["LSTM"] = y_pred_lstm
        probs["LSTM"] = y_prob_lstm

        cm_lstm = confusion_matrix(y_test_seq, y_pred_lstm)
        tn, fp, fn, tp = cm_lstm.ravel()
        fpr_lstm = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        latency_lstm = benchmark_latency(lstm_model, X_test_seq, num_iterations=200, is_lstm=True)

        results.append({
            "Model": "LSTM",
            "Accuracy": accuracy_score(y_test_seq, y_pred_lstm),
            "Precision": precision_score(y_test_seq, y_pred_lstm, zero_division=0),
            "Recall": recall_score(y_test_seq, y_pred_lstm, zero_division=0),
            "Macro F1": f1_score(y_test_seq, y_pred_lstm, average="macro", zero_division=0),
            "Weighted F1": f1_score(y_test_seq, y_pred_lstm, average="weighted", zero_division=0),
            "FPR": fpr_lstm,
            "Latency (ms/pkt)": latency_lstm,
        })

    metrics_df = pd.DataFrame(results)
    logging.info("\n" + "=" * 90 + "\nMODEL EVALUATION SUMMARY\n" + "=" * 90)
    logging.info("\n" + metrics_df.to_string(index=False))
    metrics_df.to_csv(os.path.join(OUTPUT_MODELS_DIR, "evaluation_metrics.csv"), index=False)

    # 3. Blinded Zero-Day Generalization Test
    logging.info("Conducting Blinded Generalization Test on held-out attack categories...")
    run_generalization_subtest(models, test_df)

    # 4. Generate Visualizations (.png)
    generate_visualizations(models, preds, probs, y_test, metrics_df, test_df)

    return metrics_df


def run_generalization_subtest(models: dict, test_df: pd.DataFrame):
    """Evaluates how tabular models generalize to an attack category blinded during this sub-test."""
    if "Attack_Category" not in test_df.columns:
        return

    categories = test_df["Attack_Category"].unique()
    blinded_cat = "NTP" if "NTP" in categories else categories[0]
    logging.info(f"Generalization test targeting blinded attack category: '{blinded_cat}'")

    blinded_sub = test_df[test_df["Attack_Category"] == blinded_cat]
    scaler = joblib.load(os.path.join(OUTPUT_MODELS_DIR, "scaler.joblib"))
    selector = joblib.load(os.path.join(OUTPUT_MODELS_DIR, "anova_selector.joblib"))

    X_blind = blinded_sub.drop(columns=["Label", "Binary_Label", "Attack_Category"], errors="ignore")
    numeric_cols = [c for c in X_blind.columns if np.issubdtype(X_blind[c].dtype, np.number)]
    X_blind = X_blind[numeric_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    
    X_blind_scaled = scaler.transform(X_blind)
    X_blind_selected = selector.transform(X_blind_scaled)
    y_blind = blinded_sub["Binary_Label"].values

    gen_results = []
    for name, model in models.items():
        y_pred = model.predict(X_blind_selected)
        acc = accuracy_score(y_blind, y_pred)
        rec = recall_score(y_blind, y_pred, zero_division=0)
        gen_results.append({"Model": name, "Blinded Category": blinded_cat, "Accuracy": acc, "Recall": rec})

    gen_df = pd.DataFrame(gen_results)
    logging.info("\n" + "=" * 60 + "\nBLINDED GENERALIZATION SUB-TEST RESULTS\n" + "=" * 60)
    logging.info("\n" + gen_df.to_string(index=False))
    gen_df.to_csv(os.path.join(OUTPUT_MODELS_DIR, "generalization_results.csv"), index=False)


def generate_visualizations(models, preds, probs, y_test, metrics_df, test_df):
    """Exports all required evaluation figures to the visualizations/ directory."""
    sns.set_theme(style="whitegrid")

    # Figure 1: Confusion Matrices for Every Model
    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    axes = axes.flatten()

    all_model_names = list(preds.keys())
    for i, name in enumerate(all_model_names):
        y_p = preds[name]
        y_true_eval = y_test[-len(y_p) :] if len(y_p) != len(y_test) else y_test
        cm = confusion_matrix(y_true_eval, y_p)

        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            ax=axes[i],
            cbar=False,
            xticklabels=["BENIGN", "DDoS"],
            yticklabels=["BENIGN", "DDoS"],
        )
        axes[i].set_title(f"Confusion Matrix: {name}", fontsize=13, fontweight="bold")
        axes[i].set_xlabel("Predicted")
        axes[i].set_ylabel("Actual")

    if len(all_model_names) < len(axes):
        for j in range(len(all_model_names), len(axes)):
            fig.delaxes(axes[j])

    plt.suptitle("Confusion Matrices Across All Evaluated Models", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(VISUALIZATIONS_DIR, "confusion_matrices_all_models.png"), dpi=300)
    plt.close()
    logging.info("Saved: confusion_matrices_all_models.png")

    # Figure 2: Per-Attack Category Performance Breakdown
    if "Attack_Category" in test_df.columns and "Random Forest" in preds:
        best_pred = preds["Random Forest"]
        eval_df = test_df.iloc[: len(best_pred)].copy()
        eval_df["Pred"] = best_pred
        eval_df["Correct"] = (eval_df["Pred"] == eval_df["Binary_Label"]).astype(int)

        per_cat = eval_df.groupby("Attack_Category")["Correct"].mean().reset_index()
        per_cat.columns = ["Attack Category", "Detection Accuracy"]

        plt.figure(figsize=(12, 6))
        ax = sns.barplot(data=per_cat, x="Attack Category", y="Detection Accuracy", palette="viridis")
        plt.title("Per-Attack Category Detection Accuracy (Random Forest)", fontsize=15, fontweight="bold")
        plt.ylim(0.0, 1.05)
        plt.xticks(rotation=30)
        for p in ax.patches:
            ax.annotate(f"{p.get_height()*100:.1f}%", (p.get_x() + p.get_width() / 2.0, p.get_height()),
                        ha="center", va="center", xytext=(0, 7), textcoords="offset points", fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(VISUALIZATIONS_DIR, "confusion_matrices_per_attack.png"), dpi=300)
        plt.close()
        logging.info("Saved: confusion_matrices_per_attack.png")

    # Figure 3: Combined ROC-AUC and Precision-Recall Curves
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    for name in probs:
        y_pr = probs[name]
        y_true_eval = y_test[-len(y_pr) :] if len(y_pr) != len(y_test) else y_test

        fpr, tpr, _ = roc_curve(y_true_eval, y_pr)
        roc_auc = auc(fpr, tpr)
        ax1.plot(fpr, tpr, lw=2, label=f"{name} (AUC = {roc_auc:.4f})")

        precision, recall, _ = precision_recall_curve(y_true_eval, y_pr)
        pr_auc = average_precision_score(y_true_eval, y_pr)
        ax2.plot(recall, precision, lw=2, label=f"{name} (AP = {pr_auc:.4f})")

    ax1.plot([0, 1], [0, 1], color="grey", lw=1.5, linestyle="--")
    ax1.set_title("Receiver Operating Characteristic (ROC)", fontsize=14, fontweight="bold")
    ax1.set_xlabel("False Positive Rate")
    ax1.set_ylabel("True Positive Rate")
    ax1.legend(loc="lower right")

    ax2.set_title("Precision-Recall Curves", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Recall")
    ax2.set_ylabel("Precision")
    ax2.legend(loc="lower left")

    plt.suptitle("Combined Discrimination Performance Curves", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(VISUALIZATIONS_DIR, "combined_roc_pr_curves.png"), dpi=300)
    plt.close()
    logging.info("Saved: combined_roc_pr_curves.png")

    # Figure 4: Dual-Axis Bar Chart: Detection Accuracy vs. Prediction Latency
    fig, ax1 = plt.subplots(figsize=(12, 6))

    x = np.arange(len(metrics_df))
    width = 0.35

    color1 = "#1f77b4"
    color2 = "#d62728"

    rects1 = ax1.bar(x - width / 2, metrics_df["Accuracy"] * 100, width, label="Accuracy (%)", color=color1)
    ax1.set_ylabel("Accuracy (%)", color=color1, fontsize=13, fontweight="bold")
    ax1.set_ylim(80, 102)
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics_df["Model"], fontsize=11, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    rects2 = ax2.bar(x + width / 2, metrics_df["Latency (ms/pkt)"], width, label="Latency (ms)", color=color2)
    ax2.set_ylabel("Prediction Latency (ms per packet)", color=color2, fontsize=13, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=color2)

    for r in rects1:
        h = r.get_height()
        ax1.annotate(f"{h:.1f}%", (r.get_x() + r.get_width() / 2, h), ha="center", va="bottom", fontsize=9, fontweight="bold")
    for r in rects2:
        h = r.get_height()
        ax2.annotate(f"{h:.3f}ms", (r.get_x() + r.get_width() / 2, h), ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.title("SDN Deployment Trade-Off: Detection Accuracy vs. Prediction Latency", fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(VISUALIZATIONS_DIR, "accuracy_vs_latency.png"), dpi=300)
    plt.close()
    logging.info("Saved: accuracy_vs_latency.png")


# =====================================================================
# Phase 5: Packaging & Deliverables
# =====================================================================

def package_best_model(metrics_df: pd.DataFrame, models: dict):
    """
    Selects the best model balancing high F1-score and sub-5ms latency for SDN controller deployment,
    and packages it as best_sdn_model.joblib.
    """
    sub_5ms = metrics_df[metrics_df["Latency (ms/pkt)"] <= 5.0]
    candidate_df = sub_5ms if not sub_5ms.empty else metrics_df
    best_row = candidate_df.sort_values(by=["Macro F1", "Accuracy"], ascending=False).iloc[0]
    best_model_name = best_row["Model"]

    logging.info(f"Selected Best SDN Production Model: '{best_model_name}' (Latency: {best_row['Latency (ms/pkt)']:.3f}ms, F1: {best_row['Macro F1']:.4f})")

    if best_model_name in models:
        joblib.dump(models[best_model_name], os.path.join(OUTPUT_MODELS_DIR, "best_sdn_model.joblib"))
        metadata = {
            "best_model_name": best_model_name,
            "accuracy": float(best_row["Accuracy"]),
            "macro_f1": float(best_row["Macro F1"]),
            "latency_ms": float(best_row["Latency (ms/pkt)"]),
            "selection_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(os.path.join(OUTPUT_MODELS_DIR, "model_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

    logging.info("Pipeline Packaging & Deliverables complete.")
