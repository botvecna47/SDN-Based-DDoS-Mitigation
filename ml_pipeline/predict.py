"""
predict.py - Real-Time SDN Inference Module for Ryu SDN Controller
Directly integrable into Ryu Controller event handlers (e.g., _flow_stats_reply_handler).
Processes a raw network packet/flow, transforms via ANOVA pipeline, and returns
the classification in < 5ms.
"""

import os
import json
import time
import warnings
import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exported_models")

_LOADED = False
_BEST_MODEL = None
_SCALER = None
_SELECTOR = None
_ALL_FEATURES = None
_SELECTED_FEATURES = None
_METADATA = None


def _load_inference_artifacts():
    """Loads model, scaler, and selector once into global memory cache for sub-millisecond inference."""
    global _LOADED, _BEST_MODEL, _SCALER, _SELECTOR, _ALL_FEATURES, _SELECTED_FEATURES, _METADATA

    if _LOADED:
        return

    scaler_path = os.path.join(MODELS_DIR, "scaler.joblib")
    selector_path = os.path.join(MODELS_DIR, "anova_selector.joblib")
    model_path = os.path.join(MODELS_DIR, "best_sdn_model.joblib")
    selected_features_path = os.path.join(MODELS_DIR, "selected_features.json")
    metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")

    # Fallback to random forest if best_sdn_model hasn't been written yet
    if not os.path.exists(model_path):
        model_path = os.path.join(MODELS_DIR, "random_forest.joblib")

    if not os.path.exists(scaler_path) or not os.path.exists(selector_path):
        raise FileNotFoundError(
            "Inference artifacts not found in 'exported_models/'. Run the ML training pipeline first."
        )

    _SCALER = joblib.load(scaler_path)
    _SELECTOR = joblib.load(selector_path)
    _BEST_MODEL = joblib.load(model_path)

    if os.path.exists(selected_features_path):
        with open(selected_features_path, "r") as f:
            _SELECTED_FEATURES = json.load(f)

    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            _METADATA = json.load(f)

    _ALL_FEATURES = getattr(_SCALER, "feature_names_in_", None)
    _LOADED = True


def predict_packet(packet_data) -> dict:
    """
    Classifies a raw network packet/flow in under 5 milliseconds for Ryu SDN Controller integration.

    Parameters:
        packet_data: dict, list, numpy array, or pandas Series containing raw flow features.

    Returns:
        dict:
          - "is_ddos": bool (True if attack, False if benign)
          - "label": str ("ATTACK" or "BENIGN")
          - "confidence": float (prediction probability score [0.0 - 1.0])
          - "latency_ms": float (execution time in milliseconds)
          - "action": str ("DROP" or "FORWARD")
    """
    start_time = time.perf_counter()

    if not _LOADED:
        _load_inference_artifacts()

    # Preprocess input into a 2D feature matrix
    if isinstance(packet_data, dict):
        if _ALL_FEATURES is not None:
            row = np.array([float(packet_data.get(feat, 0.0)) for feat in _ALL_FEATURES], dtype=np.float32).reshape(1, -1)
        elif _SELECTED_FEATURES is not None and all(f in packet_data for f in _SELECTED_FEATURES):
            row = np.array([float(packet_data[f]) for f in _SELECTED_FEATURES], dtype=np.float32).reshape(1, -1)
            prob = float(_BEST_MODEL.predict_proba(row)[0, 1]) if hasattr(_BEST_MODEL, "predict_proba") else float(_BEST_MODEL.predict(row)[0])
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            is_ddos = prob >= 0.5
            return {
                "is_ddos": is_ddos,
                "label": "ATTACK" if is_ddos else "BENIGN",
                "confidence": round(prob if is_ddos else 1.0 - prob, 4),
                "latency_ms": round(latency_ms, 3),
                "action": "DROP" if is_ddos else "FORWARD",
            }
        else:
            row = np.array(list(packet_data.values()), dtype=np.float32).reshape(1, -1)

    elif isinstance(packet_data, (list, tuple)):
        row = np.array(packet_data, dtype=np.float32).reshape(1, -1)

    elif isinstance(packet_data, np.ndarray):
        row = packet_data.astype(np.float32).reshape(1, -1) if packet_data.ndim == 1 else packet_data.astype(np.float32)

    elif isinstance(packet_data, (pd.Series, pd.DataFrame)):
        row = packet_data.values.astype(np.float32).reshape(1, -1) if packet_data.ndim == 1 else packet_data.values.astype(np.float32)

    else:
        raise ValueError(f"Unsupported packet_data type: {type(packet_data)}")

    row = np.nan_to_num(row, nan=0.0, posinf=1e6, neginf=-1e6)

    # Transform through ANOVA pipeline
    if row.shape[1] == _SCALER.n_features_in_:
        scaled_row = _SCALER.transform(row)
        selected_row = _SELECTOR.transform(scaled_row)
    elif row.shape[1] == _SELECTOR.k:
        selected_row = row
    else:
        raise ValueError(
            f"Expected {getattr(_SCALER, 'n_features_in_', 81)} raw features or {_SELECTOR.k} ANOVA features, got {row.shape[1]}"
        )

    # Perform inference
    if hasattr(_BEST_MODEL, "predict_proba"):
        prob = float(_BEST_MODEL.predict_proba(selected_row)[0, 1])
    else:
        prob = float(_BEST_MODEL.predict(selected_row)[0])

    is_ddos = prob >= 0.5
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    return {
        "is_ddos": is_ddos,
        "label": "ATTACK" if is_ddos else "BENIGN",
        "confidence": round(prob if is_ddos else 1.0 - prob, 4),
        "latency_ms": round(latency_ms, 3),
        "action": "DROP" if is_ddos else "FORWARD",
    }


if __name__ == "__main__":
    print("Testing predict_packet latency and throughput for Ryu SDN Controller integration...")
    try:
        _load_inference_artifacts()
        n_features = getattr(_SCALER, "n_features_in_", 28)
        dummy_packet = np.random.rand(n_features).astype(np.float32)

        for _ in range(20):
            _ = predict_packet(dummy_packet)

        latencies = []
        for _ in range(500):
            res = predict_packet(dummy_packet)
            latencies.append(res["latency_ms"])

        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)

        print(f"\n[BENCHMARK RESULTS]")
        print(f"Sample Prediction : {res}")
        print(f"Average Latency   : {avg_latency:.3f} ms / packet")
        print(f"99th Percentile   : {p99_latency:.3f} ms / packet")
        print(f"SLA Compliance    : {'PASSED (< 5.0ms)' if p99_latency < 5.0 else 'FAILED'}")

    except Exception as e:
        print(f"Inference test notice: {e}")
