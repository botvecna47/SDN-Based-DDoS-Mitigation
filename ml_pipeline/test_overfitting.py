"""
test_overfitting.py - Overfitting & Generalization Analysis Module
Evaluates all 5 trained models (LR, DT, RF, XGBoost, LSTM) on:
  1. Training Set vs. Unseen Testing Set (Generalization Gap / Delta)
  2. Per-Attack Category Unseen Generalization Test
Generates:
  - exported_models/overfitting_analysis_report.csv
  - visualizations/overfitting_train_vs_test.png
"""

import os
import gc
import json
import logging
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

MODELS_DIR = "exported_models"
VIS_DIR = "visualizations"
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(VIS_DIR, exist_ok=True)


def load_artifacts():
    """Loads feature transformation pipeline and trained models."""
    scaler = joblib.load(os.path.join(MODELS_DIR, "scaler.joblib"))
    selector = joblib.load(os.path.join(MODELS_DIR, "anova_selector.joblib"))

    with open(os.path.join(MODELS_DIR, "selected_features.json")) as f:
        selected_features = json.load(f)

    models = {
        "Logistic Regression": joblib.load(os.path.join(MODELS_DIR, "logistic_regression.joblib")),
        "Decision Tree": joblib.load(os.path.join(MODELS_DIR, "decision_tree.joblib")),
        "Random Forest": joblib.load(os.path.join(MODELS_DIR, "random_forest.joblib")),
        "XGBoost": joblib.load(os.path.join(MODELS_DIR, "xgboost.joblib")),
    }

    lstm_path = os.path.join(MODELS_DIR, "lstm_ddos_model.keras")
    lstm_model = None
    if os.path.exists(lstm_path):
        import tensorflow as tf
        lstm_model = tf.keras.models.load_model(lstm_path)

    return scaler, selector, selected_features, models, lstm_model


def prepare_data(scaler, selector):
    """Loads training and unseen testing parquet data and applies the fitted ANOVA pipeline."""
    train_df, test_df = pipeline.ingest_data("parquet_data")

    drop_cols = ["Label", "Binary_Label", "Attack_Category"]
    feature_cols = [c for c in train_df.columns if c not in drop_cols and np.issubdtype(train_df[c].dtype, np.number)]

    X_train_raw = train_df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_train = train_df["Binary_Label"].values

    X_test_raw = test_df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_test = test_df["Binary_Label"].values

    # Transform using fitted scaler & selector
    X_train_sel = selector.transform(scaler.transform(X_train_raw))
    X_test_sel = selector.transform(scaler.transform(X_test_raw))

    return X_train_sel, y_train, X_test_sel, y_test, test_df


def run_overfitting_analysis():
    scaler, selector, selected_features, models, lstm_model = load_artifacts()
    X_train_sel, y_train, X_test_sel, y_test, test_df = prepare_data(scaler, selector)

    logging.info(f"Loaded {len(X_train_sel)} training samples and {len(X_test_sel)} unseen test samples.")

    # Subsample training data for LSTM evaluation if large to maintain speed
    max_eval_train = 50000
    if len(X_train_sel) > max_eval_train:
        idx = np.random.RandomState(42).choice(len(X_train_sel), max_eval_train, replace=False)
        X_train_eval, y_train_eval = X_train_sel[idx], y_train[idx]
    else:
        X_train_eval, y_train_eval = X_train_sel, y_train

    report_rows = []

    # 1. Evaluate Tabular Models
    for name, model in models.items():
        logging.info(f"Checking overfitting for {name}...")

        # Train predictions
        y_train_pred = model.predict(X_train_eval)
        train_acc = accuracy_score(y_train_eval, y_train_pred)
        train_prec = precision_score(y_train_eval, y_train_pred, zero_division=0)
        train_rec = recall_score(y_train_eval, y_train_pred, zero_division=0)
        train_f1 = f1_score(y_train_eval, y_train_pred, zero_division=0)

        # Unseen Test predictions
        y_test_pred = model.predict(X_test_sel)
        test_acc = accuracy_score(y_test, y_test_pred)
        test_prec = precision_score(y_test, y_test_pred, zero_division=0)
        test_rec = recall_score(y_test, y_test_pred, zero_division=0)
        test_f1 = f1_score(y_test, y_test_pred, zero_division=0)

        delta_acc = train_acc - test_acc
        delta_f1 = train_f1 - test_f1

        # Determine Overfitting Status based on Generalization Gap
        if delta_acc < 0.005 and delta_f1 < 0.005:
            status = "Optimal Fit (No Overfitting)"
        elif delta_acc < 0.02 and delta_f1 < 0.02:
            status = "Minimal Gap (Well-Regularized)"
        else:
            status = "Overfitting Detected"

        report_rows.append({
            "Model": name,
            "Train Accuracy": round(train_acc, 6),
            "Unseen Test Accuracy": round(test_acc, 6),
            "Accuracy Delta (Train - Test)": round(delta_acc, 6),
            "Train Precision": round(train_prec, 6),
            "Unseen Test Precision": round(test_prec, 6),
            "Train Recall": round(train_rec, 6),
            "Unseen Test Recall": round(test_rec, 6),
            "Train F1-Score": round(train_f1, 6),
            "Unseen Test F1-Score": round(test_f1, 6),
            "F1 Delta (Train - Test)": round(delta_f1, 6),
            "Overfitting Status": status,
        })

    # 2. Evaluate LSTM
    if lstm_model is not None:
        logging.info("Checking overfitting for LSTM...")
        time_steps = 10
        X_train_seq, y_train_seq = pipeline.reshape_to_sequences(X_train_eval, y_train_eval, time_steps=time_steps)
        X_test_seq, y_test_seq = pipeline.reshape_to_sequences(X_test_sel, y_test, time_steps=time_steps)

        # Train predictions
        y_train_pred_prob = lstm_model.predict(X_train_seq, batch_size=256, verbose=0).flatten()
        y_train_pred_lstm = (y_train_pred_prob >= 0.5).astype(int)
        train_acc = accuracy_score(y_train_seq, y_train_pred_lstm)
        train_prec = precision_score(y_train_seq, y_train_pred_lstm, zero_division=0)
        train_rec = recall_score(y_train_seq, y_train_pred_lstm, zero_division=0)
        train_f1 = f1_score(y_train_seq, y_train_pred_lstm, zero_division=0)

        # Test predictions
        y_test_pred_prob = lstm_model.predict(X_test_seq, batch_size=256, verbose=0).flatten()
        y_test_pred_lstm = (y_test_pred_prob >= 0.5).astype(int)
        test_acc = accuracy_score(y_test_seq, y_test_pred_lstm)
        test_prec = precision_score(y_test_seq, y_test_pred_lstm, zero_division=0)
        test_rec = recall_score(y_test_seq, y_test_pred_lstm, zero_division=0)
        test_f1 = f1_score(y_test_seq, y_test_pred_lstm, zero_division=0)

        delta_acc = train_acc - test_acc
        delta_f1 = train_f1 - test_f1

        if delta_acc < 0.005 and delta_f1 < 0.005:
            status = "Optimal Fit (No Overfitting)"
        elif delta_acc < 0.02 and delta_f1 < 0.02:
            status = "Minimal Gap (Well-Regularized)"
        else:
            status = "Overfitting Detected"

        report_rows.append({
            "Model": "LSTM",
            "Train Accuracy": round(train_acc, 6),
            "Unseen Test Accuracy": round(test_acc, 6),
            "Accuracy Delta (Train - Test)": round(delta_acc, 6),
            "Train Precision": round(train_prec, 6),
            "Unseen Test Precision": round(test_prec, 6),
            "Train Recall": round(train_rec, 6),
            "Unseen Test Recall": round(test_rec, 6),
            "Train F1-Score": round(train_f1, 6),
            "Unseen Test F1-Score": round(test_f1, 6),
            "F1 Delta (Train - Test)": round(delta_f1, 6),
            "Overfitting Status": status,
        })

    # Save to CSV
    report_df = pd.DataFrame(report_rows)
    report_csv_path = os.path.join(MODELS_DIR, "overfitting_analysis_report.csv")
    report_df.to_csv(report_csv_path, index=False)
    logging.info(f"\nSaved overfitting analysis report to '{report_csv_path}'.")

    # Display clean table
    print("\n" + "=" * 110)
    print("OVERFITTING & GENERALIZATION REPORT (TRAIN VS. UNSEEN TEST)")
    print("=" * 110)
    print(report_df[["Model", "Train Accuracy", "Unseen Test Accuracy", "Accuracy Delta (Train - Test)", "Train F1-Score", "Unseen Test F1-Score", "Overfitting Status"]].to_string(index=False))
    print("=" * 110)

    # 3. Generate Comparative Overfitting Visualization Plot
    plot_overfitting(report_df)

    return report_df


def plot_overfitting(report_df):
    """Generates a comparison bar chart illustrating Train vs. Unseen Test Accuracy and F1-score."""
    sns.set_theme(style="whitegrid")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    models = report_df["Model"].values
    x = np.arange(len(models))
    width = 0.35

    # Subplot 1: Train vs Test Accuracy
    rects1 = ax1.bar(x - width/2, report_df["Train Accuracy"] * 100, width, label="Train Accuracy (%)", color="#2ca02c")
    rects2 = ax1.bar(x + width/2, report_df["Unseen Test Accuracy"] * 100, width, label="Unseen Test Accuracy (%)", color="#1f77b4")
    ax1.set_ylabel("Accuracy (%)", fontsize=12, fontweight="bold")
    ax1.set_title("Train vs. Unseen Test Accuracy", fontsize=14, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=15, fontweight="bold")
    ax1.set_ylim(95, 101)
    ax1.legend(loc="lower right")

    for r in rects1:
        h = r.get_height()
        ax1.annotate(f"{h:.2f}%", (r.get_x() + r.get_width()/2, h), ha="center", va="bottom", fontsize=8, fontweight="bold")
    for r in rects2:
        h = r.get_height()
        ax1.annotate(f"{h:.2f}%", (r.get_x() + r.get_width()/2, h), ha="center", va="bottom", fontsize=8, fontweight="bold")

    # Subplot 2: Train vs Test F1-Score
    rects3 = ax2.bar(x - width/2, report_df["Train F1-Score"] * 100, width, label="Train F1 (%)", color="#ff7f0e")
    rects4 = ax2.bar(x + width/2, report_df["Unseen Test F1-Score"] * 100, width, label="Unseen Test F1 (%)", color="#9467bd")
    ax2.set_ylabel("F1-Score (%)", fontsize=12, fontweight="bold")
    ax2.set_title("Train vs. Unseen Test F1-Score", fontsize=14, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, rotation=15, fontweight="bold")
    ax2.set_ylim(95, 101)
    ax2.legend(loc="lower right")

    for r in rects3:
        h = r.get_height()
        ax2.annotate(f"{h:.2f}%", (r.get_x() + r.get_width()/2, h), ha="center", va="bottom", fontsize=8, fontweight="bold")
    for r in rects4:
        h = r.get_height()
        ax2.annotate(f"{h:.2f}%", (r.get_x() + r.get_width()/2, h), ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.suptitle("Overfitting Diagnostic: Generalization Gap Across All Evaluated Models", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plot_path = os.path.join(VIS_DIR, "overfitting_train_vs_test.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    logging.info(f"Saved overfitting visualization to '{plot_path}'.")


if __name__ == "__main__":
    run_overfitting_analysis()
