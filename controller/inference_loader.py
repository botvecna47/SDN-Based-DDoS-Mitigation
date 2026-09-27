import os
import time
import logging

# We will try to import joblib, but if it's missing we can still fallback
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

THRESHOLD_FALLBACK = 10000  # PPS above which we consider it an attack without ML

def load_model(model_path):
    """
    Loads the scikit-learn ML model from the specified path.
    Returns: (model, True) if successful, (None, False) otherwise.
    """
    if not JOBLIB_AVAILABLE:
        logging.warning("joblib not installed. Cannot load ML model.")
        return None, False
        
    if not os.path.exists(model_path):
        logging.warning(f"ML model file not found at {model_path}. Falling back to threshold.")
        return None, False
        
    try:
        model = joblib.load(model_path)
        logging.info(f"Successfully loaded ML model from {model_path}")
        return model, True
    except Exception as e:
        logging.error(f"Failed to load ML model from {model_path}: {e}")
        return None, False

class DDoSDetector:
    def __init__(self, model_path):
        self.model, self.is_loaded = load_model(model_path)
        
    def predict(self, pps, bps, duration_sec, packet_count):
        """
        Predicts if a flow is DDoS or normal.
        Returns True if DDoS (1), False if Normal (0).
        Falls back to a PPS threshold if the ML model is not loaded.
        """
        start_time = time.perf_counter()
        
        if self.is_loaded and self.model is not None:
            # Build feature array: [pps, bps, duration_sec, packet_count]
            features = [[pps, bps, duration_sec, packet_count]]
            try:
                # model.predict returns an array of predictions, we want the first one
                prediction = self.model.predict(features)[0]
                result = (prediction == 1)
            except Exception as e:
                logging.error(f"Error during ML inference: {e}")
                # Fallback on error
                result = pps > THRESHOLD_FALLBACK
        else:
            # Fallback to threshold
            result = pps > THRESHOLD_FALLBACK
            
        end_time = time.perf_counter()
        inference_time_ms = (end_time - start_time) * 1000
        
        # Logging inference time could be noisy, but useful for debugging
        # logging.debug(f"Inference completed in {inference_time_ms:.2f} ms")
        
        return result
