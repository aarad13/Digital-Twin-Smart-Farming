"""Fit per-farm, per-horizon models for the live Digital Twin dashboard.

The evaluation reported in results/ is separate. These operational artifacts are
refitted on all available historical observations after the evaluation protocol.
"""
from pathlib import Path
import json
import sys
import joblib
import pandas as pd
import sklearn
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.features import build_training_features, AR_COLS, ENV_COLS, HORIZONS, TARGET


def main():
    data_path = ROOT / "data" / "kolkata_unified_dataset.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")
    df = pd.read_csv(data_path, parse_dates=["Timestamp"])
    df = df.sort_values(["Farm_ID", "Timestamp"])
    models = {}
    manifest = {
        "dataset": "EcoIrrigate: Multi-Sensor Soil Moisture Monitoring Dataset",
        "doi": "10.17632/8x4v7yy3ds.1",
        "target": TARGET,
        "sampling_minutes": 15,
        "horizons_hours": list(HORIZONS.keys()),
        "scikit_learn": sklearn.__version__,
        "models": [],
    }
    for farm_code, group in df.groupby("Farm_ID", sort=True):
        feat = build_training_features(group)
        for horizon in HORIZONS:
            target_col = f"target_{horizon}h"
            for feature_set, cols in [("autoregressive", AR_COLS), ("environment_augmented", ENV_COLS)]:
                X = feat[cols]
                y = feat[target_col]
                # Operational model fit uses the full historical series after the
                # separate chronological research evaluation has been run.
                ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
                ridge.fit(X, y)
                rf = RandomForestRegressor(
                    n_estimators=35, max_depth=12, min_samples_leaf=5,
                    max_features=0.9, n_jobs=-1, random_state=42
                )
                rf.fit(X, y)
                key = f"{farm_code}|{horizon}|{feature_set}"
                models[key] = {
                    "Ridge": {"model": ridge, "features": cols},
                    "Random Forest": {"model": rf, "features": cols},
                }
                manifest["models"].append({
                    "key": key, "rows": int(len(feat)), "ridge_features": cols,
                    "target": target_col
                })
    model_path = ROOT / "models" / "predictive_models.joblib"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(models, model_path, compress=3)
    (ROOT / "models" / "training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {len(models)} model bundles to {model_path}")
    print(f"Dataset rows: {len(df):,}; farms: {df['Farm_ID'].nunique()}")

if __name__ == "__main__":
    main()
