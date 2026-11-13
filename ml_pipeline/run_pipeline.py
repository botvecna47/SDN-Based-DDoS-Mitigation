"""
run_pipeline.py - Master Orchestrator for SDN-Based DDoS Detection & Mitigation
Executes:
  1. Data Preprocessing (11 CSVs -> 22 Parquet files in parquet_data/)
  2. Phase 1: Ingestion & ANOVA F-test Feature Selection (Top 28 features)
  3. Phase 2: Tabular Model Training (LR, DT, RF, XGBoost)
  4. Phase 3: Sequence Modeling (2-layer LSTM on RTX 5050 GPU)
  5. Phase 4: Unified Evaluation, Latency Testing & Visualizations (.png)
  6. Phase 5: Packaging & Real-Time SDN Inference Verification (< 5ms)
"""

import os
import sys
import time
import logging

# Ensure project root is in python search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    start_total = time.time()
    logging.info("=" * 80)
    logging.info("STARTING SDN-BASED DDoS DETECTION & MITIGATION PIPELINE EXECUTION")
    logging.info("=" * 80)

    # -------------------------------------------------------------
    # Step 1: Preprocessing 11 CSVs into 22 Parquet Files
    # -------------------------------------------------------------
    import data_preprocessing
    logging.info("\n>>> [STEP 1] Generating 22 Balanced, Deduplicated Parquet Files...")
    parquet_files = data_preprocessing.prepare_all_parquet(
        datasets_dir="Datasets",
        output_dir="parquet_data",
        max_samples_per_class=30000,  # Fast, optimal balance for local training & 16GB RAM
    )
    logging.info(f"[STEP 1 COMPLETE] {len(parquet_files)} Parquet files ready.")

    # -------------------------------------------------------------
    # Step 2: Phase 1 Ingestion & ANOVA Feature Selection
    # -------------------------------------------------------------
    import pipeline
    logging.info("\n>>> [STEP 2] Phase 1: Ingesting Data & ANOVA F-test Feature Selection (Top 28)...")
    train_df, test_df = pipeline.ingest_data(parquet_dir="parquet_data")
    (
        X_train_selected,
        y_train,
        X_test_selected,
        y_test,
        selected_features,
        scaler,
        selector,
    ) = pipeline.select_features_anova(train_df, test_df, k=28)
    logging.info(f"[STEP 2 COMPLETE] Selected {len(selected_features)} features.")

    # -------------------------------------------------------------
    # Step 3: Phase 2 Tabular Model Training
    # -------------------------------------------------------------
    logging.info("\n>>> [STEP 3] Phase 2: Training 4 Tabular Models (LR, DT, RF, XGBoost)...")
    tabular_models = pipeline.train_tabular_models(X_train_selected, y_train, selected_features)
    logging.info("[STEP 3 COMPLETE] Tabular models trained and decision tree visualized.")

    # -------------------------------------------------------------
    # Step 4: Phase 3 Sequence Modeling (LSTM on RTX 5050)
    # -------------------------------------------------------------
    logging.info("\n>>> [STEP 4] Phase 3: Sequence Modeling (2-Layer LSTM on RTX 5050)...")
    lstm_model, X_test_seq, y_test_seq = pipeline.build_and_train_lstm(
        X_train_selected,
        y_train,
        X_test_selected,
        y_test,
        time_steps=10,
        epochs=5,
        batch_size=256,
    )
    logging.info("[STEP 4 COMPLETE] LSTM sequence model trained and exported.")

    # -------------------------------------------------------------
    # Step 5: Phase 4 Unified Evaluation, Latency & Visualizations
    # -------------------------------------------------------------
    logging.info("\n>>> [STEP 5] Phase 4: Unified Evaluation, Latency Profiling & Visualizations...")
    metrics_df = pipeline.evaluate_models(
        models=tabular_models,
        X_test=X_test_selected,
        y_test=y_test,
        lstm_model=lstm_model,
        X_test_seq=X_test_seq,
        y_test_seq=y_test_seq,
        test_df=test_df,
    )
    logging.info("[STEP 5 COMPLETE] Metrics calculated, latency profiled, and 4 PNG figures generated.")

    # -------------------------------------------------------------
    # Step 6: Phase 5 Packaging & predict.py Verification
    # -------------------------------------------------------------
    logging.info("\n>>> [STEP 6] Phase 5: Packaging Best Model & Testing SDN Inference (< 5ms)...")
    pipeline.package_best_model(metrics_df, tabular_models)

    # Validate predict.py
    import predict
    predict._load_inference_artifacts()
    dummy_input = X_test_selected[0]
    pred_res = predict.predict_packet(dummy_input)
    logging.info(f"Sample predict_packet() Output: {pred_res}")

    total_time = (time.time() - start_total) / 60.0
    logging.info("=" * 80)
    logging.info(f"ALL PHASES COMPLETED SUCCESSFULLY IN {total_time:.2f} MINUTES!")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()
