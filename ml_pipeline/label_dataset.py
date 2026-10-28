#!/usr/bin/env python3
"""
Data Labeling Script
====================
Run this script AFTER you have collected traffic_dataset.csv from the controller.
It will ask you for the start and end times of each attack session,
then automatically label those rows as 1 (DDoS) and everything else as 0 (Normal).

Usage:
    python label_dataset.py
"""

import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

ML_PIPELINE_DIR = Path(__file__).resolve().parent
INPUT_CSV = ML_PIPELINE_DIR.parent / 'controller' / 'traffic_dataset.csv'
OUTPUT_CSV = ML_PIPELINE_DIR / 'data' / 'processed' / 'labeled_dataset.csv'

def main():
    if not INPUT_CSV.exists():
        print(f"Error: Could not find input file {INPUT_CSV}")
        return

    print("Loading dataset...")
    df = pd.read_csv(INPUT_CSV)
    
    if 'timestamp' not in df.columns:
        print("Error: 'timestamp' column not found in dataset")
        return
        
    if pd.api.types.is_numeric_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True, errors='coerce')
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.dropna(subset=['timestamp'])
    if df.empty:
        print("Error: No valid timestamps were found in the traffic dataset")
        return
    
    print(f"\nDataFrame Shape: {df.shape}")
    print("\nHead(5):")
    print(df.head(5))
    print(f"\nMin Timestamp: {df['timestamp'].min()}")
    print(f"Max Timestamp: {df['timestamp'].max()}")

    try:
        num_sessions = int(input("\nHow many attack sessions did you run? (e.g. 3): "))
    except ValueError:
        print("Invalid input for number of sessions. Must be an integer.")
        return
    if num_sessions < 1:
        print("Enter at least one attack session.")
        return

    attack_windows = []
    
    for i in range(1, num_sessions + 1):
        try:
            start_time_str = input(f"Attack session {i} start time (UTC, YYYY-MM-DD HH:MM:SS): ")
            end_time_str = input(f"Attack session {i} end time (UTC, YYYY-MM-DD HH:MM:SS): ")

            start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if end_dt < start_dt:
                print("Attack session end time must be at or after its start time.")
                return
            
            attack_windows.append((start_dt, end_dt))
        except ValueError:
            print("Invalid time format. Please use YYYY-MM-DD HH:MM:SS in UTC.")
            return

    df['label'] = 0

    for start_dt, end_dt in attack_windows:
        df.loc[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt), 'label'] = 1

    total_rows = len(df)
    attack_rows = df['label'].sum()
    normal_rows = total_rows - attack_rows
    
    print(f"\nTotal rows: {total_rows}")
    print(f"Normal rows: {normal_rows}")
    print(f"Attack rows: {attack_rows}")
    
    if attack_rows > 0 and total_rows > 0:
        attack_pct = (attack_rows / total_rows) * 100
        print(f"Attack Percentage: {attack_pct:.2f}%")
        if attack_pct < 10 or attack_pct > 50:
            print("WARNING: Distribution check - Attack rows are < 10% or > 50% of total.")
            print("Dataset is imbalanced and may produce a bad model.")
            
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nLabeled dataset saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
