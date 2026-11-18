"""Location-and-season crop-pattern model built from an openly licensed Indian dataset."""
from __future__ import annotations

import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REGIONAL_DIR = ROOT / "data" / "regional"
MODEL_FILE = REGIONAL_DIR / "india_district_crop_pattern_model.joblib"
MANIFEST_FILE = REGIONAL_DIR / "india_district_crop_model_manifest.json"

SOIL_FEATURE_MAP = {
    "soil_ph_h2o_0_5cm": "ph",
    "soil_total_n_g_kg_0_5cm": "total_nitrogen_g_kg",
    "soil_soc_g_kg_0_5cm": "soil_organic_carbon_g_kg",
    "soil_cec_cmol_kg_0_5cm": "cation_exchange_capacity_cmol_kg",
    "soil_clay_pct_0_5cm": "clay_pct",
    "soil_sand_pct_0_5cm": "sand_pct",
    "soil_silt_pct_0_5cm": "silt_pct",
    "soil_bulk_density_kg_dm3_0_5cm": "bulk_density_kg_dm3",
    "soil_org_c_density_kg_m3_0_5cm": "organic_carbon_density_kg_m3",
    "soil_coarse_frag_pct_0_5cm": "coarse_fragments_pct",
}
CLIMATE_COLUMNS = [
    "temp_mean_c", "temp_max_c", "temp_min_c", "humidity_pct", "rainfall_mm",
    "rain_days_proxy_mm_per_day", "solar_mj_m2_day", "wind_m_s",
    "annual_rainfall_mm", "annual_temp_mean_c", "annual_humidity_pct", "elevation_m",
]


def _season_name(value: str) -> str:
    key = str(value or "").strip().lower()
    aliases = {"kharif": "Kharif", "rabi": "Rabi", "zaid": "Summer", "summer": "Summer",
               "perennial": "Whole Year", "whole year": "Whole Year", "whole-year": "Whole Year",
               "autumn": "Autumn", "winter": "Winter"}
    return aliases.get(key, "")


def _season_periods(frame: pd.DataFrame, season: str) -> list[pd.DataFrame]:
    """Return complete calendar slices while retaining the weather columns."""
    if frame is None or frame.empty:
        return []
    year_min = int(frame.index.min().year)
    year_max = int(frame.index.max().year)
    periods = []
    # Crop-year windows follow the dataset's published season definitions.
    # Include only years for which the season could end before the last data date.
    for year in range(year_min, year_max + 1):
        if season == "Kharif":
            start, end = pd.Timestamp(year, 6, 1), pd.Timestamp(year, 11, 1)
        elif season == "Rabi":
            start, end = pd.Timestamp(year, 11, 1), pd.Timestamp(year + 1, 4, 1)
        elif season == "Whole Year":
            start, end = pd.Timestamp(year, 6, 1), pd.Timestamp(year + 1, 6, 1)
        elif season == "Summer":
            start, end = pd.Timestamp(year, 3, 1), pd.Timestamp(year, 6, 1)
        elif season == "Autumn":
            start, end = pd.Timestamp(year, 9, 1), pd.Timestamp(year, 12, 1)
        elif season == "Winter":
            start, end = pd.Timestamp(year, 12, 1), pd.Timestamp(year + 1, 3, 1)
        else:
            return []
        # A final partial season is excluded by the minimum-day coverage check.
        block = frame.loc[(frame.index >= start) & (frame.index < end)].copy()
        periods.append(block)
    return periods


def _read_daily_weather(latitude: float, longitude: float) -> pd.DataFrame | None:
    # The regional service caches this series when it fetches NASA POWER climate.
    from app.services import regional
    records = regional._read_cache(f"nasa_weather_series_{latitude:.2f}_{longitude:.2f}", 30 * 86400)
    if not records:
        return None
    frame = pd.DataFrame(records)
    if "date" not in frame:
        return None
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).set_index("date").sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    for col in ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"]:
        if col in frame:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").replace(-999, np.nan)
        else:
            frame[col] = np.nan
    return frame


def _climate_features(frame: pd.DataFrame, season: str, elevation_m) -> dict:
    periods = _season_periods(frame, season)
    usable = []
    minimum_days = {"Kharif": 100, "Rabi": 100, "Whole Year": 240, "Summer": 60, "Autumn": 60, "Winter": 60}.get(season, 60)
    for block_index, block in enumerate(periods):
        start = block.index.min() if len(block) else None
        if len(block) < minimum_days:
            continue
        # Use the real rows in this block; do not fill missing observed history with made-up values.
        usable.append(block)
    if len(usable) < 3:
        raise ValueError("At least three reasonably complete historical seasons are required for this location and season.")
    combined = pd.concat(usable).sort_index()
    annual = frame.loc[frame.index <= pd.Timestamp("2025-12-31")].copy()
    if annual.empty:
        raise ValueError("No historical NASA POWER daily weather series was found.")
    annual_totals = annual["PRECTOTCORR"].groupby(annual.index.year).sum(min_count=200)
    features = {
        "temp_mean_c": combined["T2M"].mean(),
        "temp_max_c": combined["T2M_MAX"].mean(),
        "temp_min_c": combined["T2M_MIN"].mean(),
        "humidity_pct": combined["RH2M"].mean(),
        "rainfall_mm": float(np.mean([x["PRECTOTCORR"].sum(min_count=60) for x in usable])),
        "rain_days_proxy_mm_per_day": combined["PRECTOTCORR"].mean(),
        "solar_mj_m2_day": combined["ALLSKY_SFC_SW_DWN"].mean() * 3.6 if combined["ALLSKY_SFC_SW_DWN"].notna().any() else np.nan,
        "wind_m_s": combined["WS2M"].mean(),
        "annual_rainfall_mm": annual_totals.mean(),
        "annual_temp_mean_c": annual["T2M"].mean(),
        "annual_humidity_pct": annual["RH2M"].mean(),
        "elevation_m": float(elevation_m) if elevation_m not in (None, "") else np.nan,
    }
    return {key: (float(value) if pd.notna(value) and math.isfinite(float(value)) else None) for key, value in features.items()}


def _soil_features(soil_profile: dict) -> dict:
    props = (soil_profile or {}).get("properties") or {}
    features = {}
    for model_column, property_key in SOIL_FEATURE_MAP.items():
        item = props.get(property_key) or {}
        value = item.get("value")
        try:
            value = float(value)
            if not math.isfinite(value):
                value = None
        except (TypeError, ValueError):
            value = None
        features[model_column] = value
    return features


def model_status() -> dict:
    if not MODEL_FILE.exists():
        return {"available": False, "reason": "The India district crop-pattern dataset has not yet been downloaded and trained on this installation.",
                "prepare_command": "docker compose exec web python /app/scripts/prepare_india_crop_model.py",
                "dataset_file": "data/regional/india_district_crop_dataset_1997_2015.csv",
                "source_dataset_url": "https://github.com/priyanshupriyank04/india-district-crop-dataset",
                "license": "CC BY 4.0", "download_size_mb_approx": 23}
    manifest = {}
    try:
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return {"available": True, "model_name": manifest.get("model_name", "India district crop-pattern model"),
            "rows_used": manifest.get("rows_used"), "districts": manifest.get("districts"),
            "crop_classes": len(manifest.get("crop_classes", [])), "validation": manifest.get("validation"),
            "source_dataset_url": manifest.get("source_dataset_url"),
            "source_repository_url": manifest.get("source_repository_url"),
            "license": manifest.get("license", "CC BY 4.0")}


def predict_indian_crop_pattern(latitude: float, longitude: float, season: str, soil_profile: dict, elevation_m=None) -> dict:
    selected_season = _season_name(season)
    if not selected_season:
        return {"status": "needs_season", "reason": "Choose Kharif, Rabi, Zaid or Perennial to compare historical crop patterns."}
    if not MODEL_FILE.exists():
        return {"status": "dataset_not_prepared", **model_status(),
                "reason": model_status().get("reason")}
    try:
        weather = _read_daily_weather(latitude, longitude)
        if weather is None or weather.empty:
            return {"status": "unavailable", "reason": "Historical NASA POWER daily weather is not cached yet. Refresh My Area for this location first."}
        climate = _climate_features(weather, selected_season, elevation_m)
        soil_features = _soil_features(soil_profile)
        available_soil = sum(value is not None for value in soil_features.values())
        if available_soil < 3:
            return {"status": "unavailable", "reason": "Fewer than three mapped topsoil properties were available. Try again later or use the field laboratory report; the crop model will not invent soil values."}
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8")) if MANIFEST_FILE.exists() else {}
        model = joblib.load(MODEL_FILE)
        row = {**soil_features, **climate, "season": selected_season}
        matrix = pd.DataFrame([row])
        probabilities = model.predict_proba(matrix)[0]
        classes = model.classes_
        order = np.argsort(probabilities)[::-1][:3]
        top = [{"crop": str(classes[i]), "model_vote_share_pct": round(float(probabilities[i]) * 100, 1)} for i in order]
        return {
            "status": "available", "season": season, "dataset_season": selected_season,
            "top_historical_crops": top, "score_interpretation": "Uncalibrated classifier vote share used only to rank historical district crop-pattern classes; not probability of farm success, crop suitability, yield or profit.", "input_coverage": {"mapped_soil_properties_available": available_soil, "mapped_soil_properties_expected": len(SOIL_FEATURE_MAP), "climate_features_available": sum(v is not None for v in climate.values()), "climate_features_expected": len(CLIMATE_COLUMNS)},
            "validation": manifest.get("validation"), "training_rows": manifest.get("rows_used"),
            "training_districts": manifest.get("districts"), "crop_classes": len(manifest.get("crop_classes", [])),
            "source_dataset_url": manifest.get("source_dataset_url"),
            "training_period": "1997–2015 district × crop-year × season records",
            "prediction_scope": "Historical dominant-crop pattern similarity at district-scale environmental inputs; not a farm-specific suitability, yield, profit or planting prescription.",
            "field_soil_test_used": False,
            "reason": "SoilGrids and gridded climate inputs are regional estimates. A laboratory Soil Health Card is shown separately and should be reviewed by an agronomist before crop decisions.",
        }
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc)[:300]}
