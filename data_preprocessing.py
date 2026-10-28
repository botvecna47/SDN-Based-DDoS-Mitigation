"""
data_preprocessing.py - CIC-DDoS2019 Dataset Preprocessor
Converts 11 raw CSV attack files into 22 balanced, deduplicated Parquet files:
  <Category>_training.parquet and <Category>_testing.parquet (70/30 split)
Optimized for 16GB RAM machines using chunked streaming and downcasting.
"""

import os
import gc
import re
import glob
import logging
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Mapping of file names to standardized attack category names
DATASET_FILES = {
    "DrDoS_DNS.csv": "DNS",
    "DrDoS_LDAP.csv": "LDAP",
    "DrDoS_MSSQL.csv": "MSSQL",
    "DrDoS_NTP.csv": "NTP",
    "DrDoS_NetBIOS.csv": "NetBIOS",
    "DrDoS_SNMP.csv": "SNMP",
    "DrDoS_SSDP.csv": "SSDP",
    "DrDoS_UDP.csv": "UDP",
    "Syn.csv": "SYN",
    "TFTP.csv": "TFTP",
    "UDPLag.csv": "UDPLag",
}

# Non-predictive identity columns to exclude
METADATA_COLUMNS = [
    "Unnamed: 0",
    "Flow ID",
    "Source IP",
    "Destination IP",
    "Timestamp",
    "SimillarHTTP",
]


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Strips column names, removes metadata columns, and handles infinite/NaN values."""
    df.columns = df.columns.str.strip()

    # Drop metadata columns if present
    drop_cols = [c for c in METADATA_COLUMNS if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # Clean non-numeric anomalies in numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    
    # Fill remaining NaNs with column median
    for col in numeric_cols:
        if df[col].isna().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(0.0 if np.isnan(median_val) else median_val)

    # Downcast floats to float32 and ints to int32 to conserve 50% RAM
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = df[col].astype(np.float32)
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = df[col].astype(np.int32)

    return df


def process_single_csv(
    csv_path: str,
    category_name: str,
    output_dir: str,
    max_samples_per_class: int = 30000,
    test_size: float = 0.30,
    random_state: int = 42,
    chunk_size: int = 50000,
):
    """
    Streams a large CSV file in chunks, extracts BENIGN and Attack records,
    balances them, deduplicates, and splits into training and testing Parquet files.
    """
    train_parquet = os.path.join(output_dir, f"{category_name}_training.parquet")
    test_parquet = os.path.join(output_dir, f"{category_name}_testing.parquet")

    if os.path.exists(train_parquet) and os.path.exists(test_parquet):
        logging.info(f"Parquet files for {category_name} already exist. Skipping.")
        return train_parquet, test_parquet

    logging.info(f"Processing '{csv_path}' for category '{category_name}'...")

    benign_chunks = []
    attack_chunks = []
    benign_count = 0
    attack_count = 0

    try:
        # Read in chunks to prevent 16GB RAM exhaustion on 9GB+ files like TFTP
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
            chunk = clean_dataframe(chunk)

            if "Label" not in chunk.columns:
                continue

            benign = chunk[chunk["Label"].astype(str).str.upper() == "BENIGN"]
            attack = chunk[chunk["Label"].astype(str).str.upper() != "BENIGN"]

            if len(benign) > 0 and benign_count < max_samples_per_class:
                needed = max_samples_per_class - benign_count
                benign_chunks.append(benign.iloc[:needed])
                benign_count += len(benign.iloc[:needed])

            if len(attack) > 0 and attack_count < max_samples_per_class:
                needed = max_samples_per_class - attack_count
                attack_chunks.append(attack.iloc[:needed])
                attack_count += len(attack.iloc[:needed])

            if benign_count >= max_samples_per_class and attack_count >= max_samples_per_class:
                break

    except Exception as e:
        logging.error(f"Error reading {csv_path}: {e}")
        return None, None

    if not attack_chunks:
        logging.warning(f"No attack data extracted for {category_name}.")
        return None, None

    attack_df = pd.concat(attack_chunks, ignore_index=True)
    benign_df = pd.concat(benign_chunks, ignore_index=True) if benign_chunks else pd.DataFrame(columns=attack_df.columns)

    logging.info(f"[{category_name}] Extracted {len(attack_df)} attack rows and {len(benign_df)} benign rows.")

    # Balance benign and attack counts if enough benign exists
    if len(benign_df) > 0 and len(benign_df) < len(attack_df):
        target_attack_len = min(len(attack_df), max(len(benign_df) * 3, 10000))
        attack_df = attack_df.sample(n=target_attack_len, random_state=random_state)
    elif len(benign_df) >= len(attack_df):
        benign_df = benign_df.sample(n=len(attack_df), random_state=random_state)

    combined_df = pd.concat([benign_df, attack_df], ignore_index=True)
    
    # Deduplicate rows
    initial_len = len(combined_df)
    combined_df = combined_df.drop_duplicates()
    logging.info(f"[{category_name}] Deduplicated {initial_len - len(combined_df)} rows. Current count: {len(combined_df)}")

    # Standardize Attack Category tag and binary target
    combined_df["Attack_Category"] = category_name
    combined_df["Binary_Label"] = (combined_df["Label"].astype(str).str.upper() != "BENIGN").astype(np.int32)

    # Stratified 70/30 split
    stratify_col = combined_df["Binary_Label"] if combined_df["Binary_Label"].nunique() > 1 else None
    train_df, test_df = train_test_split(
        combined_df,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_col,
    )

    # Save to Parquet
    os.makedirs(output_dir, exist_ok=True)
    train_df.to_parquet(train_parquet, index=False, engine="pyarrow", compression="snappy")
    test_df.to_parquet(test_parquet, index=False, engine="pyarrow", compression="snappy")

    logging.info(f"[{category_name}] Saved: {train_parquet} ({len(train_df)} rows), {test_parquet} ({len(test_df)} rows)")

    del combined_df, train_df, test_df, attack_df, benign_df
    gc.collect()

    return train_parquet, test_parquet


def prepare_all_parquet(
    datasets_dir: str = "Datasets",
    output_dir: str = "parquet_data",
    max_samples_per_class: int = 30000,
):
    """Iterates through all 11 dataset files and generates the 22 Parquet files."""
    os.makedirs(output_dir, exist_ok=True)
    created_files = []

    for filename, category in DATASET_FILES.items():
        csv_path = os.path.join(datasets_dir, filename)
        if not os.path.exists(csv_path):
            logging.warning(f"File not found: {csv_path}. Skipping.")
            continue

        train_p, test_p = process_single_csv(
            csv_path=csv_path,
            category_name=category,
            output_dir=output_dir,
            max_samples_per_class=max_samples_per_class,
        )
        if train_p and test_p:
            created_files.extend([train_p, test_p])

    logging.info(f"Preprocessing completed. Total {len(created_files)} Parquet files generated in '{output_dir}'.")
    return created_files


if __name__ == "__main__":
    prepare_all_parquet()
