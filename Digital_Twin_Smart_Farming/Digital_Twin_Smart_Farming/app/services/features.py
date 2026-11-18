"""Feature construction shared by model training and live inference."""
import numpy as np
import pandas as pd

TARGET = "Volumetric_Moisture_Pct"
AR_COLS = [
    "moisture_now", "lag_1h", "lag_6h", "lag_24h", "lag_72h",
    "mean_prev_1h", "mean_prev_6h", "std_prev_6h",
    "Hour_sin", "Hour_cos", "Day_sin", "Day_cos",
]
ENV_COLS = AR_COLS + [
    "Atm_Temperature_C", "Atm_Pressure_inHg",
    "Soil_Temperature_C", "Sensor_Board_Temperature_C",
]
HORIZONS = {1: 4, 6: 24}  # dataset samples every 15 minutes


def build_training_features(group: pd.DataFrame) -> pd.DataFrame:
    g = group.sort_values("Timestamp").copy()
    y = pd.to_numeric(g[TARGET], errors="coerce")
    X = pd.DataFrame(index=g.index)
    X["moisture_now"] = y
    for samples, name in [(4, "lag_1h"), (24, "lag_6h"), (96, "lag_24h"), (288, "lag_72h")]:
        X[name] = y.shift(samples)
    X["mean_prev_1h"] = y.rolling(4, min_periods=4).mean()
    X["mean_prev_6h"] = y.rolling(24, min_periods=24).mean()
    X["std_prev_6h"] = y.rolling(24, min_periods=24).std()
    for col in ["Hour_sin", "Hour_cos", "Day_sin", "Day_cos"]:
        X[col] = pd.to_numeric(g[col], errors="coerce")
    for col in ["Atm_Temperature_C", "Atm_Pressure_inHg", "Soil_Temperature_C", "Sensor_Board_Temperature_C"]:
        X[col] = pd.to_numeric(g[col], errors="coerce")
    for horizon, steps in HORIZONS.items():
        X[f"target_{horizon}h"] = y.shift(-steps)
    result = pd.concat([g[["Timestamp"]].reset_index(drop=True), X.reset_index(drop=True)], axis=1)
    return result.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)


def make_live_features(history: pd.DataFrame) -> dict:
    """Create one feature row from oldest-to-newest observations."""
    g = history.sort_values("Timestamp").reset_index(drop=True)
    if len(g) < 289:
        raise ValueError(f"At least 289 observations (72 h + current reading) are required; found {len(g)}.")
    y = pd.to_numeric(g[TARGET], errors="coerce")
    latest = g.iloc[-1]
    features = {
        "moisture_now": float(y.iloc[-1]),
        "lag_1h": float(y.iloc[-1 - 4]),
        "lag_6h": float(y.iloc[-1 - 24]),
        "lag_24h": float(y.iloc[-1 - 96]),
        "lag_72h": float(y.iloc[-1 - 288]),
        "mean_prev_1h": float(y.iloc[-4:].mean()),
        "mean_prev_6h": float(y.iloc[-24:].mean()),
        "std_prev_6h": float(y.iloc[-24:].std()),
        "Hour_sin": float(latest["Hour_sin"]),
        "Hour_cos": float(latest["Hour_cos"]),
        "Day_sin": float(latest["Day_sin"]),
        "Day_cos": float(latest["Day_cos"]),
        "Atm_Temperature_C": float(latest["Atm_Temperature_C"]),
        "Atm_Pressure_inHg": float(latest["Atm_Pressure_inHg"]),
        "Soil_Temperature_C": float(latest["Soil_Temperature_C"]),
        "Sensor_Board_Temperature_C": float(latest["Sensor_Board_Temperature_C"]),
    }
    if not np.isfinite(list(features.values())).all():
        raise ValueError("The latest farm history contains missing or non-finite model inputs.")
    return features
