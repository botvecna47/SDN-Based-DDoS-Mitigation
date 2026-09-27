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
import os
from datetime import datetime

INPUT_CSV = '../controller/traffic_dataset.csv'
OUTPUT_CSV = 'data/processed/labeled_dataset.csv'

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Could not find input file {INPUT_CSV}")
        return

    print("Loading dataset...")
    df = pd.read_csv(INPUT_CSV)
    
    if 'timestamp' not in df.columns:
        print("Error: 'timestamp' column not found in dataset")
        return
        
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
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

    attack_windows = []
    
    for i in range(1, num_sessions + 1):
        try:
            start_time_str = input(f"Attack session {i} start time (format: HH:MM:SS): ")
            end_time_str = input(f"Attack session {i} end time (format: HH:MM:SS): ")
            
            start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
            end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
            
            base_date = df['timestamp'].iloc[0].date()
            start_dt = datetime.combine(base_date, start_time)
            end_dt = datetime.combine(base_date, end_time)
            
            attack_windows.append((start_dt, end_dt))
        except ValueError:
            print("Invalid time format. Please use HH:MM:SS.")
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
            
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nLabeled dataset saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
