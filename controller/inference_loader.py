import os
import time
import logging

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

# PPS threshold used as fallback when detector.joblib is not yet trained (Phase 1 & 2)
THRESHOLD_FALLBACK = 10000

def load_model(model_path):
    """
    Loads the scikit-learn ML model from disk.
    Returns (model, True) if successful, (None, False) otherwise.
    """
    if not JOBLIB_AVAILABLE:
        logging.warning("joblib not installed. Cannot load ML model.")
        return None, False

    if not os.path.exists(model_path):
        logging.warning(
            f"detector.joblib not found at {model_path}. "
            f"Using PPS > {THRESHOLD_FALLBACK} threshold fallback — this is expected in Phase 1 & 2."
        )
        return None, False

    try:
        model = joblib.load(model_path)
        logging.info(f"ML model loaded from {model_path}")
        return model, True
    except Exception as e:
        logging.error(f"Failed to load ML model: {e}")
        return None, False


class DDoSDetector:
    def __init__(self, model_path):
        self.model, self.is_loaded = load_model(model_path)

    def predict(self, pps, bps, duration_sec, packet_count):
        """
        Classify a single network flow as DDoS or normal.

        Returns:
            (is_ddos: bool, inference_ms: float)

        The inference_ms is written into shared_state.json so the React
        dashboard's "ML Decision Delay" KPI card displays a real measured value.
        Falls back to PPS threshold when detector.joblib is not yet trained.
        """
        start = time.perf_counter()

        if self.is_loaded and self.model is not None:
            features = [[pps, bps, duration_sec, packet_count]]
            try:
                prediction = self.model.predict(features)[0]
                result = (prediction == 1)
            except Exception as e:
                logging.error(f"ML inference error: {e}")
                result = pps > THRESHOLD_FALLBACK
        else:
            result = pps > THRESHOLD_FALLBACK

        inference_ms = round((time.perf_counter() - start) * 1000, 3)
        return result, inference_ms
