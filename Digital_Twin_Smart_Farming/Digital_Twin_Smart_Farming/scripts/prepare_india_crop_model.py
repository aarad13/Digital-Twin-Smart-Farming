#!/usr/bin/env python3
"""Download and train the India district crop-pattern model (one-time setup).

The input is a CC BY 4.0 derived district-level historical dataset.  The model
predicts the historically dominant district crop for a season, not a farm-level
crop prescription, yield or profit estimate.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "regional"
DATA_FILE = DATA_DIR / "india_district_crop_dataset_1997_2015.csv"
MODEL_FILE = DATA_DIR / "india_district_crop_pattern_model.joblib"
MANIFEST_FILE = DATA_DIR / "india_district_crop_model_manifest.json"
DATA_URL = "https://raw.githubusercontent.com/priyanshupriyank04/india-district-crop-dataset/main/data/final/india_district_crop_dataset_1997_2015.csv"

SOIL_FEATURES = [
    "soil_ph_h2o_0_5cm",
    "soil_total_n_g_kg_0_5cm",
    "soil_soc_g_kg_0_5cm",
    "soil_cec_cmol_kg_0_5cm",
    "soil_clay_pct_0_5cm",
    "soil_sand_pct_0_5cm",
    "soil_silt_pct_0_5cm",
    "soil_bulk_density_kg_dm3_0_5cm",
    "soil_org_c_density_kg_m3_0_5cm",
    "soil_coarse_frag_pct_0_5cm",
]
CLIMATE_FEATURES = [
    "temp_mean_c", "temp_max_c", "temp_min_c", "humidity_pct", "rainfall_mm",
    "rain_days_proxy_mm_per_day", "solar_mj_m2_day", "wind_m_s",
    "annual_rainfall_mm", "annual_temp_mean_c", "annual_humidity_pct", "elevation_m",
]
NUMERIC_FEATURES = SOIL_FEATURES + CLIMATE_FEATURES
CATEGORICAL_FEATURES = ["season"]
REQUIRED_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["dominant_crop", "district_key"]


def download_dataset(force: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists() and not force:
        print(f"Using existing dataset: {DATA_FILE}")
        return DATA_FILE
    print("Downloading India district crop, soil and climate dataset (~23 MB)…")
    response = requests.get(DATA_URL, stream=True, timeout=(15, 180), headers={"User-Agent": "DigitalTwinSmartFarming/1.0"})
    response.raise_for_status()
    temp_file = DATA_FILE.with_suffix(".csv.part")
    total = 0
    try:
        with temp_file.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)
                    total += len(chunk)
        if total < 1_000_000:
            raise ValueError(f"Dataset download is unexpectedly small ({total:,} bytes).")
        # Validate the exact schema before replacing the final file.
        header = pd.read_csv(temp_file, nrows=2).columns
        missing = sorted(set(REQUIRED_COLUMNS) - set(header))
        if missing:
            raise ValueError("Downloaded CSV does not match the documented dataset schema. Missing: " + ", ".join(missing))
        temp_file.replace(DATA_FILE)
    except Exception:
        temp_file.unlink(missing_ok=True)
        raise
    print(f"Downloaded {total:,} bytes to {DATA_FILE}")
    return DATA_FILE


def build_pipeline() -> Pipeline:
    numeric = make_pipeline(SimpleImputer(strategy="median"))
    season = make_pipeline(SimpleImputer(strategy="most_frequent"), OneHotEncoder(handle_unknown="ignore"))
    preprocessor = ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("season", season, CATEGORICAL_FEATURES),
    ])
    classifier = RandomForestClassifier(
        n_estimators=120, max_depth=18, min_samples_leaf=2,
        class_weight="balanced_subsample", random_state=42, n_jobs=-1,
    )
    return Pipeline([("features", preprocessor), ("classifier", classifier)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-download", action="store_true", help="Download a fresh copy of the CSV")
    args = parser.parse_args()

    path = download_dataset(args.force_download)
    print("Checking dataset columns and preparing training rows…")
    frame = pd.read_csv(path, low_memory=False)
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise SystemExit("Dataset is missing required columns: " + ", ".join(missing))
    frame = frame[REQUIRED_COLUMNS].copy()
    frame = frame.dropna(subset=["dominant_crop", "district_key", "season"])
    frame["dominant_crop"] = frame["dominant_crop"].astype(str).str.strip()
    frame["district_key"] = frame["district_key"].astype(str).str.strip()
    frame["season"] = frame["season"].astype(str).str.strip().str.title()
    for column in NUMERIC_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame[column] = frame[column].replace([np.inf, -np.inf], np.nan)
    frame = frame[(frame["dominant_crop"] != "") & (frame["district_key"] != "") & (frame["season"] != "")]
    if frame.empty:
        raise SystemExit("Dataset has no valid dominant-crop rows after cleaning.")
    counts = frame["dominant_crop"].value_counts()
    selected_classes = counts[counts >= 100].index
    frame = frame[frame["dominant_crop"].isin(selected_classes)].copy()
    if len(frame) < 5000 or frame["district_key"].nunique() < 5 or frame["dominant_crop"].nunique() < 2:
        raise SystemExit("Dataset did not pass minimum row, district or crop-class checks.")
    X = frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = frame["dominant_crop"]
    groups = frame["district_key"].astype(str)

    print(f"Training data: {len(frame):,} rows · {groups.nunique():,} districts · {y.nunique():,} crops")
    fold_results = []
    splitter = GroupKFold(n_splits=5)
    for fold, (train_idx, test_idx) in enumerate(splitter.split(X, y, groups), start=1):
        model = build_pipeline()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        predicted = model.predict(X.iloc[test_idx])
        acc = accuracy_score(y.iloc[test_idx], predicted)
        macro = f1_score(y.iloc[test_idx], predicted, average="macro", zero_division=0)
        fold_results.append({"fold": fold, "accuracy": round(float(acc), 4), "macro_f1": round(float(macro), 4),
                             "train_rows": len(train_idx), "test_rows": len(test_idx),
                             "train_districts": int(groups.iloc[train_idx].nunique()),
                             "test_districts": int(groups.iloc[test_idx].nunique())})
        print(f"  Fold {fold}/5: accuracy={acc:.3f}, macro-F1={macro:.3f}")

    final_model = build_pipeline()
    final_model.fit(X, y)
    joblib.dump(final_model, MODEL_FILE, compress=3)
    manifest = {
        "model_name": "India district historical dominant-crop pattern classifier",
        "target": "dominant_crop",
        "target_definition": "Crop with the largest recorded sown area within a district/year/season in the source dataset.",
        "training_dataset": DATA_FILE.name,
        "source_dataset_url": DATA_URL,
        "source_repository_url": "https://github.com/priyanshupriyank04/india-district-crop-dataset",
        "license": "CC BY 4.0 for dataset; cite the repository and component sources listed in DATASET_SOURCES.md.",
        "rows_used": int(len(frame)), "districts": int(groups.nunique()),
        "crop_classes": sorted(str(x) for x in y.unique()),
        "numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES,
        "minimum_class_frequency": 100,
        "validation": {"method": "5-fold GroupKFold, grouped by district_key", "folds": fold_results,
                       "mean_accuracy": round(sum(x["accuracy"] for x in fold_results) / len(fold_results), 4),
                       "mean_macro_f1": round(sum(x["macro_f1"] for x in fold_results) / len(fold_results), 4)},
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "warning": "District-level historical pattern similarity only. Not a farm-level suitability, yield, profit, or fertilizer prescription model.",
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("\nREADY: India crop-pattern model saved.")
    print(f"Model: {MODEL_FILE}")
    print(f"Validation: mean accuracy {manifest['validation']['mean_accuracy']:.3f}; macro-F1 {manifest['validation']['mean_macro_f1']:.3f}")
    print("Interpretation: historical dominant-crop pattern similarity, not a crop recommendation.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"Dataset download failed: {exc}\nCheck the Mac's internet connection and retry this command.", file=sys.stderr)
        raise SystemExit(2)
