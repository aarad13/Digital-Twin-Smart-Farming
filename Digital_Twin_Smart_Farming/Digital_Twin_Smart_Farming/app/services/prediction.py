"""Forecast and decision-support services."""
from pathlib import Path
import os
import joblib
import numpy as np
import pandas as pd
from .features import make_live_features, AR_COLS, ENV_COLS

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT / "models" / "predictive_models.joblib"))


def load_models():
    if not MODEL_PATH.is_absolute():
        path = ROOT / MODEL_PATH
    else:
        path = MODEL_PATH
    if not path.exists():
        raise FileNotFoundError("Model artifacts not found. Run: python scripts/train_models.py")
    return joblib.load(path)


def predict_options(farm_code: str, horizon_h: int, history_rows: list[dict]):
    history = pd.DataFrame(history_rows)
    if history.empty:
        raise ValueError("No historical observations are available for this farm.")
    history["Timestamp"] = pd.to_datetime(history["Timestamp"])
    values = make_live_features(history)
    current = float(values["moisture_now"])
    origin = pd.Timestamp(history["Timestamp"].iloc[-1]).to_pydatetime()
    steps = int(horizon_h * 4)
    target_at = origin + pd.Timedelta(minutes=15 * steps)
    models = load_models()
    options = [{
        "model_name": "Persistence",
        "feature_set": "baseline",
        "predicted": current,
        "description": "Carries forward the latest observed moisture value."
    }]
    key_ar = f"{farm_code}|{horizon_h}|autoregressive"
    key_env = f"{farm_code}|{horizon_h}|environment_augmented"
    if key_ar not in models:
        raise ValueError(f"No trained model bundle exists for {farm_code}, {horizon_h} h.")
    for name in ("Ridge", "Random Forest"):
        entry = models[key_ar][name]
        X = pd.DataFrame([{c: values[c] for c in entry["features"]}])
        pred = float(entry["model"].predict(X)[0])
        options.append({"model_name": name, "feature_set": "autoregressive", "predicted": float(np.clip(pred, 0, 100)),
                        "description": "Uses moisture history and time features."})
    # Show the weather/sensor-augmented Ridge comparison as a separate option.
    env_entry = models[key_env]["Ridge"]
    Xenv = pd.DataFrame([{c: values[c] for c in env_entry["features"]}])
    env_pred = float(env_entry["model"].predict(Xenv)[0])
    options.append({"model_name": "Ridge + sensor context", "feature_set": "environment_augmented",
                    "predicted": float(np.clip(env_pred, 0, 100)),
                    "description": "Adds atmospheric, soil and sensor-board temperature/pressure fields available in this dataset."})
    return {
        "farm_code": farm_code, "horizon_hours": horizon_h,
        "origin_at": origin, "target_at": target_at,
        "current_moisture": current, "options": options,
        "latest_features": values,
    }


def create_advisory(current: float, predicted: float, threshold: float):
    if predicted <= threshold:
        level = "REVIEW IRRIGATION"
        message = (f"The forecast ({predicted:.2f}%) is at or below the configured prototype threshold "
                   f"({threshold:.2f}%). Review field conditions and crop-specific irrigation guidance before acting.")
    elif predicted <= threshold + 1.5:
        level = "MONITOR"
        message = (f"The forecast ({predicted:.2f}%) is within 1.5 percentage points above the configured "
                   f"threshold ({threshold:.2f}%). Continue monitoring and review local field conditions.")
    else:
        level = "NO LOW-MOISTURE FLAG"
        message = (f"The forecast ({predicted:.2f}%) is above the configured prototype threshold "
                   f"({threshold:.2f}%). This is not a guarantee that irrigation is unnecessary.")
    return level, message
