#!/usr/bin/env python3
"""
Random Forest DDoS Detection Model Trainer
===========================================
Trains a machine learning classifier on SDN flow metrics to detect DDoS attacks.
Saves the trained model to ml_pipeline/detector.joblib for Ryu controller inference.

Usage:
    python ml_pipeline/train.py
    python ml_pipeline/train.py --synthetic   # Force synthetic dataset generation
"""

import os
import sys
import time
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

ML_DIR = Path(__file__).resolve().parent
DATA_PROCESSED_CSV = ML_DIR / 'data' / 'processed' / 'labeled_dataset.csv'
MODEL_OUTPUT_PATH = ML_DIR / 'detector.joblib'
FEATURES = ['pps', 'bps', 'duration_sec', 'packet_count']

def generate_synthetic_dataset(num_samples=4000) -> pd.DataFrame:
    """
    Generates a realistic synthetic SDN traffic dataset modeling:
    - Normal legitimate traffic (h1 -> h3): 700-900 PPS, ~1 Mbps to 10 Mbps
    - Volumetric DDoS UDP flood (h2 -> h3): 15,000-30,000 PPS, high byte rates
    """
    print("Generating representative synthetic SDN flow dataset...")
    np.random.seed(42)
    n_normal = int(num_samples * 0.75)
    n_attack = num_samples - n_normal

    # Normal traffic: duration 1 to 300s, pps 600 to 1,200, avg packet ~1000-1470 bytes
    normal_duration = np.random.uniform(1.0, 300.0, n_normal)
    normal_pps = np.random.normal(820.0, 80.0, n_normal).clip(500.0, 1500.0)
    normal_bps = normal_pps * np.random.normal(1200.0, 150.0, n_normal) * 8.0
    normal_packets = (normal_pps * normal_duration).astype(int)

    # Attack traffic: duration 1 to 120s, pps 18,000 to 28,000, small to standard packets
    attack_duration = np.random.uniform(1.0, 120.0, n_attack)
    attack_pps = np.random.normal(23000.0, 2500.0, n_attack).clip(12000.0, 35000.0)
    attack_bps = attack_pps * np.random.normal(700.0, 100.0, n_attack) * 8.0
    attack_packets = (attack_pps * attack_duration).astype(int)

    df_normal = pd.DataFrame({
        'pps': normal_pps,
        'bps': normal_bps,
        'duration_sec': normal_duration,
        'packet_count': normal_packets,
        'label': 0
    })

    df_attack = pd.DataFrame({
        'pps': attack_pps,
        'bps': attack_bps,
        'duration_sec': attack_duration,
        'packet_count': attack_packets,
        'label': 1
    })

    df = pd.concat([df_normal, df_attack], ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
    DATA_PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PROCESSED_CSV, index=False)
    print(f"Synthetic dataset saved to {DATA_PROCESSED_CSV} ({len(df)} samples).")
    return df

def load_data(force_synthetic=False) -> pd.DataFrame:
    if force_synthetic or not DATA_PROCESSED_CSV.exists():
        if not force_synthetic:
            print(f"Processed dataset not found at {DATA_PROCESSED_CSV}.")
        return generate_synthetic_dataset()

    print(f"Loading labeled dataset from {DATA_PROCESSED_CSV}...")
    df = pd.read_csv(DATA_PROCESSED_CSV)
    missing = [f for f in FEATURES + ['label'] if f not in df.columns]
    if missing:
        print(f"Warning: Dataset missing required columns {missing}. Falling back to synthetic.")
        return generate_synthetic_dataset()
    return df

def main():
    parser = argparse.ArgumentParser(description="Train Random Forest DDoS Classifier for Ryu Controller")
    parser.add_argument('--synthetic', action='store_true', help="Force synthetic dataset generation")
    args = parser.parse_args()

    df = load_data(force_synthetic=args.synthetic)
    X = df[FEATURES]
    y = df['label'].astype(int)

    print(f"\nClass Distribution:\n{y.value_counts()}")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nTraining set: {len(X_train)} | Test set: {len(X_test)}")
    print("Training RandomForestClassifier(n_estimators=100)...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nEvaluation Results:\nAccuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, y_pred, target_names=['Normal (0)', 'DDoS (1)']))

    # Measure inference latency benchmark
    sample = X_test.iloc[:500]
    t0 = time.perf_counter()
    _ = clf.predict(sample)
    t1 = time.perf_counter()
    avg_latency_ms = ((t1 - t0) / 500.0) * 1000.0
    print(f"Average single-flow inference latency: {avg_latency_ms:.3f} ms")

    joblib.dump(clf, MODEL_OUTPUT_PATH)
    print(f"\nModel successfully saved to: {MODEL_OUTPUT_PATH}")
    print("Ryu controller will now automatically load this model upon next start/restart!")

if __name__ == '__main__':
    main()
