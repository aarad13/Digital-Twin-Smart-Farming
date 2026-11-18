"""Location-based agricultural intelligence services.

External data are clearly identified as gridded/modelled or API-derived.  The
module deliberately avoids translating regional estimates into field-tested
fertilizer or irrigation prescriptions.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import json
import math
import re
import time
from difflib import get_close_matches

import numpy as np
import pandas as pd
import requests
from app.services.indian_agriculture import context_for_location
from app.services.regional_problems import build_regional_problem_report

ROOT = Path(__file__).resolve().parents[2]
REGION_DIR = ROOT / "data" / "regional"
CACHE_DIR = REGION_DIR / "cache"
CROP_FILE = REGION_DIR / "crop_production.csv"
CROP_METADATA_FILE = REGION_DIR / "crop_production_metadata.json"
DEMO_CROP_FILE = ROOT / "data" / "demo" / "DEMO_CROP_STATISTICS_SYNTHETIC.csv"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "DigitalTwinSmartFarmingAcademicPrototype/1.0"})
REQUEST_TIMEOUT = (8, 35)


def _cache_path(key: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", key)
    return CACHE_DIR / f"{safe}.json"


def _read_cache(key: str, max_age_seconds: int):
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(obj.get("cached_at", 0)) <= max_age_seconds:
            return obj.get("data")
    except (OSError, ValueError, TypeError):
        return None
    return None


def _write_cache(key: str, data):
    path = _cache_path(key)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"cached_at": time.time(), "data": data}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def geocode_location(query: str, count: int = 6) -> list[dict]:
    query = (query or "").strip()
    if len(query) < 2:
        raise ValueError("Enter at least two characters for a location search.")
    cache_key = "geocode_" + re.sub(r"\W+", "_", query.lower())
    cached = _read_cache(cache_key, 30 * 86400)
    if cached is not None:
        return cached
    response = SESSION.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": query, "count": count, "language": "en", "countryCode": "IN"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    results = []
    for item in payload.get("results", []):
        if str(item.get("country_code", "")).upper() != "IN":
            continue
        results.append({
            "name": item.get("name"), "admin1": item.get("admin1"),
            "admin2": item.get("admin2"), "country": item.get("country", "India"),
            "latitude": float(item["latitude"]), "longitude": float(item["longitude"]),
            "elevation_m": item.get("elevation"), "timezone": item.get("timezone"),
        })
    _write_cache(cache_key, results)
    return results


def _valid_series(values: dict) -> list[float]:
    cleaned = []
    for value in values.values():
        try:
            number = float(value)
            if math.isfinite(number) and number > -900:
                cleaned.append(number)
        except (TypeError, ValueError):
            continue
    return cleaned


def fetch_nasa_climate(latitude: float, longitude: float) -> dict:
    """Summarize the last ten complete calendar years of NASA POWER daily data."""
    latest_end = (date.today() - timedelta(days=3)).strftime("%Y%m%d")
    cache_key = f"nasa_v2_{latitude:.2f}_{longitude:.2f}_2016_{latest_end}"
    cached = _read_cache(cache_key, 7 * 86400)
    if cached is not None:
        return cached
    params = {
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN",
        "community": "AG", "longitude": longitude, "latitude": latitude,
        "start": "20160101", "end": latest_end, "format": "JSON", "time-standard": "UTC",
    }
    response = SESSION.get("https://power.larc.nasa.gov/api/temporal/daily/point", params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    parameter = payload.get("properties", {}).get("parameter", {})
    required = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M"]
    missing = [key for key in required if key not in parameter]
    if missing:
        raise ValueError("NASA POWER response is missing parameters: " + ", ".join(missing))

    frame = pd.DataFrame({k: pd.Series(v, dtype="float64") for k, v in parameter.items()})
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d", errors="coerce")
    frame = frame.sort_index().replace(-999, np.nan)
    frame = frame.dropna(subset=["T2M", "PRECTOTCORR"])
    if frame.empty:
        raise ValueError("NASA POWER returned no valid daily observations for this point.")
    # Keep current historical weather for the location-specific forecast model.
    weather_records = frame[[c for c in ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"] if c in frame]].copy()
    weather_records = weather_records.reset_index(names="date")
    weather_records["date"] = weather_records["date"].dt.strftime("%Y-%m-%d")
    _write_cache(f"nasa_weather_series_{latitude:.2f}_{longitude:.2f}", weather_records.to_dict(orient="records"))
    # Climate normals use ten complete calendar years; partial 2026 is excluded.
    climate_frame = frame.loc[frame.index <= pd.Timestamp("2025-12-31")].copy()
    if climate_frame.empty:
        raise ValueError("No complete 2016–2025 climate record was returned for this location.")
    climate_frame["year"] = climate_frame.index.year
    climate_frame["month"] = climate_frame.index.month
    annual_rain = climate_frame.groupby("year")["PRECTOTCORR"].sum(min_count=1)
    monthly = climate_frame.groupby("month").agg(
        rainfall_mm=("PRECTOTCORR", "mean"),
        mean_temp_c=("T2M", "mean"),
        max_temp_c=("T2M_MAX", "mean"),
        min_temp_c=("T2M_MIN", "mean"),
        mean_rh_pct=("RH2M", "mean"),
    ).reindex(range(1, 13))
    # Monthly rainfall shown is mean daily rainfall; annual values are also supplied.
    monthly_rain_totals = climate_frame.groupby("month")["PRECTOTCORR"].sum(min_count=1) / max(1, climate_frame["year"].nunique())
    wettest_month = int(monthly_rain_totals.idxmax()) if monthly_rain_totals.notna().any() else None
    annual_avg = float(annual_rain.mean()) if annual_rain.notna().any() else None
    monsoon_rain = float(climate_frame.loc[climate_frame["month"].isin([6, 7, 8, 9]), "PRECTOTCORR"].sum())
    total_rain = float(climate_frame["PRECTOTCORR"].sum())
    monsoon_share = 100.0 * monsoon_rain / total_rain if total_rain > 0 else None
    if monsoon_share is not None and monsoon_share >= 50:
        rainfall_regime = "Monsoon-concentrated rainfall pattern (June–September)"
    elif wettest_month:
        rainfall_regime = "Seasonal rainfall; wettest month is " + date(2000, wettest_month, 1).strftime("%B")
    else:
        rainfall_regime = "Rainfall seasonality could not be determined"
    result = {
        "period": "2016–2025 (10 complete calendar years)",
        "weather_history_latest_date": frame.index.max().strftime("%Y-%m-%d"),
        "source": "NASA POWER Daily Agroclimatology Point API",
        "daily_records_used": int(len(climate_frame)),
        "mean_air_temperature_c": round(float(climate_frame["T2M"].mean()), 2),
        "mean_daily_max_temperature_c": round(float(climate_frame["T2M_MAX"].mean()), 2),
        "mean_daily_min_temperature_c": round(float(climate_frame["T2M_MIN"].mean()), 2),
        "mean_relative_humidity_pct": round(float(climate_frame["RH2M"].mean()), 2) if climate_frame["RH2M"].notna().any() else None,
        "mean_wind_speed_ms": round(float(climate_frame["WS2M"].mean()), 2) if "WS2M" in climate_frame and climate_frame["WS2M"].notna().any() else None,
        "mean_daily_solar_radiation_mj_m2": round(float(climate_frame["ALLSKY_SFC_SW_DWN"].mean() * 3.6), 2) if "ALLSKY_SFC_SW_DWN" in climate_frame and climate_frame["ALLSKY_SFC_SW_DWN"].notna().any() else None,
        "mean_annual_rainfall_mm": round(annual_avg, 1) if annual_avg is not None else None,
        "monsoon_jun_sep_rainfall_share_pct": round(monsoon_share, 1) if monsoon_share is not None else None,
        "rainfall_regime": rainfall_regime,
        "wettest_month": date(2000, wettest_month, 1).strftime("%B") if wettest_month else None,
        "monthly": [
            {"month": date(2000, m, 1).strftime("%b"),
             "mean_daily_rainfall_mm": round(float(monthly.loc[m, "rainfall_mm"]), 2) if pd.notna(monthly.loc[m, "rainfall_mm"]) else None,
             "mean_monthly_rainfall_mm": round(float(monthly_rain_totals.loc[m]), 1) if pd.notna(monthly_rain_totals.loc[m]) else None,
             "mean_temp_c": round(float(monthly.loc[m, "mean_temp_c"]), 1) if pd.notna(monthly.loc[m, "mean_temp_c"]) else None}
            for m in range(1, 13)
        ],
        "annual_rainfall": [{"year": int(y), "rainfall_mm": round(float(v), 1)} for y, v in annual_rain.items() if pd.notna(v)],
    }
    _write_cache(cache_key, result)
    return result


def fetch_weather_forecast(latitude: float, longitude: float) -> dict:
    cache_key = f"forecast_{latitude:.2f}_{longitude:.2f}"
    cached = _read_cache(cache_key, 3 * 3600)
    if cached is not None:
        return cached
    params = {
        "latitude": latitude, "longitude": longitude,
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,relative_humidity_2m_mean,wind_speed_10m_mean,et0_fao_evapotranspiration",
        "forecast_days": 7, "timezone": "auto",
    }
    response = SESSION.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    daily = payload.get("daily", {})
    days = []
    length = len(daily.get("time", []))
    for i in range(length):
        def take(key):
            arr = daily.get(key, [])
            return arr[i] if i < len(arr) else None
        days.append({
            "date": take("time"), "mean_temp_c": take("temperature_2m_mean"),
            "max_temp_c": take("temperature_2m_max"), "min_temp_c": take("temperature_2m_min"),
            "precipitation_mm": take("precipitation_sum"),
            "precipitation_probability_pct": take("precipitation_probability_max"),
            "relative_humidity_pct": take("relative_humidity_2m_mean"),
            "wind_speed_ms": take("wind_speed_10m_mean"), "et0_mm": take("et0_fao_evapotranspiration"),
        })
    result = {
        "source": "Open-Meteo Forecast API", "timezone": payload.get("timezone"),
        "daily": days,
        "total_precipitation_mm": round(sum(float(x["precipitation_mm"] or 0) for x in days), 1),
        "max_temperature_c": max([x["max_temp_c"] for x in days if x["max_temp_c"] is not None], default=None),
        "max_precipitation_probability_pct": max([x["precipitation_probability_pct"] for x in days if x["precipitation_probability_pct"] is not None], default=None),
    }
    _write_cache(cache_key, result)
    return result



def fetch_nasa_rootzone_series(latitude: float, longitude: float) -> tuple[pd.DataFrame, str, str]:
    """Fetch gridded root-zone moisture from NASA POWER Hydrology community.

    RZMC is volumetric root-zone water content (m³/m³). If unavailable, the
    fallback GWETROOT is a relative saturation fraction and is not the same unit.
    """
    latest_end = (date.today() - timedelta(days=3)).strftime("%Y%m%d")
    cache_key = f"nasa_rootzone_{latitude:.2f}_{longitude:.2f}_2016_{latest_end}"
    cached = _read_cache(cache_key, 7 * 86400)
    if cached is not None:
        frame = pd.DataFrame(cached)
        frame["date"] = pd.to_datetime(frame["date"])
        target_name = cached[0].get("target_name", "RZMC") if cached else "RZMC"
        return frame.set_index("date")[["target"]].sort_index(), target_name, "NASA POWER Hydrology"

    last_error = None
    for target in ("RZMC", "GWETROOT"):
        params = {
            "parameters": target, "community": "HY", "longitude": longitude,
            "latitude": latitude, "start": "20160101", "end": latest_end,
            "format": "JSON", "time-standard": "UTC",
        }
        try:
            response = SESSION.get("https://power.larc.nasa.gov/api/temporal/daily/point", params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            values = payload.get("properties", {}).get("parameter", {}).get(target)
            if not values:
                raise ValueError(f"NASA POWER did not return {target} values.")
            series = pd.Series(values, dtype="float64")
            series.index = pd.to_datetime(series.index, format="%Y%m%d", errors="coerce")
            frame = pd.DataFrame({"target": series}).sort_index().replace(-999, np.nan).dropna()
            frame = frame[np.isfinite(frame["target"])]
            if len(frame) < 500:
                raise ValueError(f"Only {len(frame)} root-zone moisture records were returned; at least 500 are required for the regional model.")
            frame = frame[(frame["target"] >= 0) & (frame["target"] <= 1.0)]
            records = frame.reset_index(names="date")
            records["date"] = records["date"].dt.strftime("%Y-%m-%d")
            records["target_name"] = target
            _write_cache(cache_key, records.to_dict(orient="records"))
            return frame, target, "NASA POWER Hydrology (gridded land-surface model product)"
        except Exception as exc:
            last_error = exc
    raise ValueError(f"NASA POWER root-zone moisture series is unavailable: {last_error}")


def _regional_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    y = frame["target"].astype(float)
    x = pd.DataFrame(index=frame.index)
    x["moisture_lag_1d"] = y.shift(1)
    x["moisture_lag_3d"] = y.shift(3)
    x["moisture_lag_7d"] = y.shift(7)
    x["moisture_mean_prev_3d"] = y.shift(1).rolling(3, min_periods=3).mean()
    x["moisture_mean_prev_7d"] = y.shift(1).rolling(7, min_periods=7).mean()
    # Only prior-day weather is used to predict the current day's target.
    # Using same-day observed weather would leak information unavailable at
    # the forecast origin in a real next-day deployment.
    for col in ["T2M", "PRECTOTCORR", "RH2M", "WS2M"]:
        x[f"{col}_lag_1d"] = frame[col].shift(1)
    doy = frame.index.dayofyear
    x["day_year_sin"] = np.sin(2 * np.pi * doy / 365.25)
    x["day_year_cos"] = np.cos(2 * np.pi * doy / 365.25)
    valid = x.replace([np.inf, -np.inf], np.nan).notna().all(axis=1) & y.notna()
    return x.loc[valid], y.loc[valid], list(x.columns)


def _metric_pack(y_true, y_pred) -> dict:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 5),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 5),
        "r2": round(float(r2_score(y_true, y_pred)), 4) if len(y_true) > 1 else None,
    }


def forecast_regional_rootzone_moisture(latitude: float, longitude: float, weather_forecast: dict) -> dict:
    """Fit at the selected grid point, evaluate chronologically, then forecast 7 days recursively."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    weather_key = f"nasa_weather_series_{latitude:.2f}_{longitude:.2f}"
    weather_records = _read_cache(weather_key, 7 * 86400)
    if not weather_records:
        raise ValueError("Historical NASA POWER weather series was not cached; refresh the regional climate profile first.")
    weather = pd.DataFrame(weather_records)
    weather["date"] = pd.to_datetime(weather["date"])
    weather = weather.set_index("date").sort_index()
    soil, target_name, source = fetch_nasa_rootzone_series(latitude, longitude)
    frame = weather.join(soil, how="inner").dropna(subset=["target", "T2M", "PRECTOTCORR", "RH2M", "WS2M"]).sort_index()
    # Preserve calendar-day lags even when one or more daily source observations are missing.
    frame = frame[~frame.index.duplicated(keep="last")].asfreq("D")
    frame = frame.replace([np.inf, -np.inf], np.nan)
    valid_target_dates = frame["target"].dropna().index
    if len(valid_target_dates) == 0:
        raise ValueError("No overlapping root-zone moisture and weather observations were available.")
    latest_observation_date = valid_target_dates.max()
    staleness_days = int((pd.Timestamp(date.today()) - latest_observation_date.normalize()).days)
    if staleness_days > 14:
        raise ValueError(f"The latest root-zone moisture observation is {staleness_days} days old; a current regional forecast is withheld to avoid using stale soil state.")
    X, y, feature_names = _regional_features(frame)
    if len(X) < 500:
        raise ValueError(f"Only {len(X)} aligned daily records are available; at least 500 are required.")
    split = int(len(X) * 0.8)
    if split < 300 or len(X) - split < 60:
        raise ValueError("The aligned regional series is too short for the selected chronological holdout.")
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    baseline = X_test["moisture_lag_1d"].to_numpy()
    results = {"Persistence": _metric_pack(y_test, baseline)}
    candidates = {
        "Ridge": make_pipeline(StandardScaler(), Ridge(alpha=2.0)),
        "Random Forest": RandomForestRegressor(n_estimators=160, max_depth=14, min_samples_leaf=3, random_state=42, n_jobs=-1),
    }
    fitted = {}
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        pred = np.clip(model.predict(X_test), 0, 1)
        results[name] = _metric_pack(y_test, pred)
        fitted[name] = model
    # Select a learned model only when it beats persistence on the chronological holdout.
    ml_winner = min(candidates, key=lambda name: results[name]["rmse"])
    baseline_beaten = results[ml_winner]["rmse"] < results["Persistence"]["rmse"]
    selected = ml_winner if baseline_beaten else "Persistence"

    best_model = None
    if selected != "Persistence":
        best_model = candidates[selected]
        best_model.fit(X, y)

    recent_state = frame.loc[:latest_observation_date, "target"].ffill(limit=2)
    if recent_state.tail(7).isna().any():
        raise ValueError("The latest seven days of root-zone moisture contain gaps; a current recursive forecast is withheld.")
    hist_values = recent_state.tail(7).astype(float).tolist()
    weather_columns = ["T2M", "PRECTOTCORR", "RH2M", "WS2M"]
    hist_weather = frame.loc[:latest_observation_date, weather_columns].ffill(limit=2)
    if hist_weather.tail(1).isna().any(axis=None):
        raise ValueError("The latest observed weather values are incomplete; the first forecast step cannot be generated reliably.")
    previous_weather = hist_weather.iloc[-1].astype(float).to_dict()
    fallback = hist_weather.mean().to_dict()
    preds = []
    for day in weather_forecast.get("daily", []):
        if not day.get("date"):
            continue
        fdate = pd.Timestamp(day["date"])
        def number_or_fallback(value, key):
            try:
                val = float(value)
                return val if math.isfinite(val) else float(fallback[key])
            except (TypeError, ValueError):
                return float(fallback[key])
        # Forecast weather for the target day is retained for the next recursive
        # step. The current prediction uses weather from the preceding day only.
        target_day_weather = {
            "T2M": number_or_fallback(day.get("mean_temp_c"), "T2M"),
            "PRECTOTCORR": number_or_fallback(day.get("precipitation_mm"), "PRECTOTCORR"),
            "RH2M": number_or_fallback(day.get("relative_humidity_pct"), "RH2M"),
            "WS2M": number_or_fallback(day.get("wind_speed_ms"), "WS2M"),
        }
        if len(hist_values) < 7:
            continue
        feat = {
            "moisture_lag_1d": hist_values[-1],
            "moisture_lag_3d": hist_values[-3],
            "moisture_lag_7d": hist_values[-7],
            "moisture_mean_prev_3d": float(np.mean(hist_values[-3:])),
            "moisture_mean_prev_7d": float(np.mean(hist_values[-7:])),
            "T2M_lag_1d": previous_weather["T2M"],
            "PRECTOTCORR_lag_1d": previous_weather["PRECTOTCORR"],
            "RH2M_lag_1d": previous_weather["RH2M"],
            "WS2M_lag_1d": previous_weather["WS2M"],
            "day_year_sin": math.sin(2 * math.pi * fdate.dayofyear / 365.25),
            "day_year_cos": math.cos(2 * math.pi * fdate.dayofyear / 365.25),
        }
        if selected == "Persistence":
            pred = hist_values[-1]
        else:
            pred = float(best_model.predict(pd.DataFrame([feat], columns=feature_names))[0])
        pred = float(np.clip(pred, 0, 1))
        preds.append({"date": fdate.strftime("%Y-%m-%d"), "predicted_rootzone_moisture": round(pred, 5),
                      "predicted_volumetric_percent": round(pred * 100, 2),
                      "weather": target_day_weather})
        hist_values.append(pred)
        previous_weather = target_day_weather

    if not preds:
        raise ValueError("No future daily weather values were available for a regional moisture forecast.")
    return {
        "status": "available", "target_name": target_name,
        "target_description": "Root-zone volumetric soil moisture (RZMC)" if target_name == "RZMC" else "Root-zone relative wetness (GWETROOT)",
        "unit": "m³/m³" if target_name == "RZMC" else "fraction of saturation",
        "source": source, "training_period": f"{X.index.min().date()} to {X.index.max().date()}",
        "latest_observation_date": latest_observation_date.strftime("%Y-%m-%d"), "staleness_days": staleness_days,
        "aligned_daily_records": int(len(X)), "chronological_holdout_fraction": 0.2,
        "validation_horizon_days": 1, "forecast_horizon_days": len(preds),
        "validation_protocol": "Chronological one-day-ahead holdout; features use prior-day weather only",
        "forecast_mode": "Recursive multi-day forecast using weather outlook and predicted moisture lags",
        "validation_metrics": results, "selected_model": selected,
        "learned_model_beats_persistence": bool(baseline_beaten),
        "forecasts": preds,
        "interpretation": "NASA POWER gridded land-surface model target at the nearest data grid, not a field sensor reading. Model scores are point-specific and do not establish farm-level accuracy.",
    }

def _soilgrids_sample_property(prop: str, latitude: float, longitude: float) -> float | None:
    """Sample a small ~1 km neighborhood using SoilGrids WCS (not the paused REST API)."""
    from owslib.wcs import WebCoverageService
    from pyproj import Transformer
    from rasterio.io import MemoryFile

    cache_key = f"soil_{prop}_{latitude:.3f}_{longitude:.3f}"
    cached = _read_cache(cache_key, 30 * 86400)
    if cached is not None:
        return cached

    transformer = Transformer.from_crs(
        "EPSG:4326", "+proj=igh +datum=WGS84 +units=m +no_defs +type=crs", always_xy=True
    )
    x, y = transformer.transform(longitude, latitude)
    url = f"https://maps.isric.org/mapserv?map=/map/{prop}.map"
    wcs = WebCoverageService(url, version="2.0.1", timeout=REQUEST_TIMEOUT[1])
    coverage_id = f"{prop}_0-5cm_mean"
    if coverage_id not in wcs.contents:
        raise ValueError(f"SoilGrids coverage {coverage_id} was not advertised by the service.")
    coverage = wcs.contents[coverage_id]
    formats = list(getattr(coverage, "supportedFormats", []) or [])
    fmt = next((f for f in formats if "tiff" in str(f).lower()), formats[0] if formats else "image/tiff")
    response = wcs.getCoverage(
        identifier=[coverage_id],
        crs="http://www.opengis.net/def/crs/EPSG/0/152160",
        subsets=[("X", x - 500, x + 500), ("Y", y - 500, y + 500)],
        resx=250, resy=250, format=fmt,
    )
    raw = response.read()
    if not raw or len(raw) < 100:
        raise ValueError(f"SoilGrids returned an empty raster for {prop}.")
    with MemoryFile(raw) as mem:
        with mem.open() as ds:
            arr = ds.read(1, masked=True).astype("float64")
            values = arr.compressed()
            values = values[np.isfinite(values)]
            if not len(values):
                return None
            # Median over surrounding pixels reduces single-cell edge artefacts.
            val = float(np.median(values))
    _write_cache(cache_key, val)
    return val


def fetch_soil_profile(latitude: float, longitude: float) -> dict:
    props = {}
    failures = []
    # 0–5 cm topsoil mean estimate. Scale factors follow SoilGrids metadata.
    config = {
        "phh2o": ("ph", 10.0, "pH units"),
        "sand": ("sand_pct", 10.0, "%"),
        "clay": ("clay_pct", 10.0, "%"),
        "silt": ("silt_pct", 10.0, "%"),
        "soc": ("soil_organic_carbon_g_kg", 10.0, "g/kg"),
        "nitrogen": ("total_nitrogen_g_kg", 100.0, "g/kg"),
        "cec": ("cation_exchange_capacity_cmol_kg", 10.0, "cmol(+)/kg"),
        "bdod": ("bulk_density_kg_dm3", 100.0, "kg/dm³"),
        "ocd": ("organic_carbon_density_kg_m3", 10.0, "kg/m³"),
        "cfvo": ("coarse_fragments_pct", 10.0, "%"),
    }
    for prop, (out_key, scale, unit) in config.items():
        try:
            raw = _soilgrids_sample_property(prop, latitude, longitude)
            if raw is not None:
                props[out_key] = {"value": round(raw / scale, 2), "unit": unit, "depth": "0–5 cm", "source": "SoilGrids mean estimate"}
        except Exception as exc:
            failures.append(f"{prop}: {str(exc)[:180]}")
    # Infer a coarse texture group only when both clay and sand values exist.
    sand = props.get("sand_pct", {}).get("value")
    clay = props.get("clay_pct", {}).get("value")
    silt = max(0.0, 100.0 - sand - clay) if sand is not None and clay is not None else None
    if silt is not None:
        props["silt_pct_derived"] = {"value": round(silt, 2), "unit": "%", "depth": "0–5 cm", "source": "Derived as 100 − sand − clay; confirm source fractions sum to 100"}
    texture = None
    if sand is not None and clay is not None:
        if clay >= 40:
            texture = "Clay-dominant"
        elif sand >= 70:
            texture = "Sand-dominant"
        elif clay >= 27:
            texture = "Clay-loam range"
        elif sand >= 52 and clay < 20:
            texture = "Sandy-loam range"
        elif 7 <= clay < 27 and 28 <= sand < 52:
            texture = "Loam-like range"
        elif silt is not None and silt >= 50 and clay < 27:
            texture = "Silt-loam range"
        else:
            texture = "Mixed texture; laboratory confirmation needed"
    return {
        "source": "ISRIC SoilGrids WCS", "depth": "0–5 cm", "spatial_resolution_m": 250,
        "properties": props, "texture_group_screening": texture,
        "status": "available" if props else "unavailable",
        "limitations": "Modelled regional soil-property estimates from a surrounding raster neighborhood; not a field soil test or a formal Indian soil taxonomic classification.",
        "warnings": failures[:4],
    }


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _normalise_crop_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("The uploaded crop statistics CSV is empty.")
    mapping = {_normalise_header(c): c for c in frame.columns}
    aliases = {
        "state": ["statename", "state", "stateut"],
        "district": ["districtname", "district"],
        "year": ["cropyear", "year"],
        "season": ["season"],
        "crop": ["crop", "cropname"],
        "area": ["area", "areahectare", "areahectares"],
        "production": ["production", "productiontonnes", "productiontons"],
    }
    selected = {}
    for key, candidates in aliases.items():
        source = next((mapping[c] for c in candidates if c in mapping), None)
        if source:
            selected[key] = source
    required = ["state", "district", "crop", "season"]
    missing = [x for x in required if x not in selected]
    if missing:
        raise ValueError("CSV must include State, District, Crop and Season columns. Missing: " + ", ".join(missing))
    clean = pd.DataFrame()
    for key, col in selected.items():
        clean[key] = frame[col]
    clean = clean.dropna(subset=required)
    for col in ["state", "district", "crop", "season"]:
        clean[col] = clean[col].astype(str).str.strip()
    if "year" in clean:
        raw_year = clean["year"].astype(str).str.strip()
        numeric_year = pd.to_numeric(raw_year, errors="coerce")
        # Government crop datasets often encode years as 2019-20 or 2019-2020.
        # Use the first four-digit year for chronological trend calculations.
        extracted_year = pd.to_numeric(raw_year.str.extract(r"(19\d{2}|20\d{2})", expand=False), errors="coerce")
        clean["year"] = numeric_year.fillna(extracted_year)
    else:
        clean["year"] = np.nan
    for col in ["area", "production"]:
        clean[col] = pd.to_numeric(clean[col], errors="coerce") if col in clean else np.nan
    clean = clean[(clean["state"] != "") & (clean["district"] != "") & (clean["crop"] != "") & (clean["season"] != "")]
    if clean.empty:
        raise ValueError("No usable district/crop/season rows remain after cleaning the CSV.")
    return clean


def _save_crop_frame(clean: pd.DataFrame, metadata: dict) -> dict:
    REGION_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(CROP_FILE, index=False)
    CROP_METADATA_FILE.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"rows": int(len(clean)), "states": int(clean["state"].nunique()),
            "districts": int(clean["district"].nunique()), "file": str(CROP_FILE.name),
            "provenance": metadata.get("provenance", "Unknown")}


def save_crop_statistics_csv(file_storage) -> dict:
    if not file_storage or not getattr(file_storage, "filename", "").lower().endswith(".csv"):
        raise ValueError("Upload a CSV downloaded from the Government of India's district-wise crop production statistics.")
    frame = pd.read_csv(file_storage, low_memory=False)
    clean = _normalise_crop_frame(frame)
    return _save_crop_frame(clean, {
        "data_type": "uploaded", "provenance": "User-uploaded CSV; the file origin has not been independently verified.",
        "filename": getattr(file_storage, "filename", "uploaded.csv"),
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
    })


def load_demo_crop_statistics() -> dict:
    """Load a clearly synthetic district crop-history file for presentations only."""
    if not DEMO_CROP_FILE.exists():
        raise FileNotFoundError("The synthetic demo crop-statistics CSV is missing from data/demo.")
    frame = pd.read_csv(DEMO_CROP_FILE, low_memory=False)
    clean = _normalise_crop_frame(frame)
    return _save_crop_frame(clean, {
        "data_type": "synthetic_demo", "provenance": "SYNTHETIC PRESENTATION DATA — NOT GOVERNMENT DATA AND NOT REAL DISTRICT STATISTICS.",
        "filename": DEMO_CROP_FILE.name,
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
    })


def get_crop_pattern(district: str | None, state: str | None, top_n: int = 8) -> dict:
    if not CROP_FILE.exists():
        return {"available": False, "message": "No district crop-production CSV has been uploaded yet.", "crops": []}
    frame = pd.read_csv(CROP_FILE)
    try:
        metadata = json.loads(CROP_METADATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        metadata = {"data_type": "unknown", "provenance": "Crop dataset provenance is unknown; verify the original source."}
    if not district:
        return {"available": False, "message": "District name is required to identify local crop patterns.", "crops": []}
    districts = frame["district"].dropna().astype(str).unique().tolist()
    match = next((x for x in districts if x.casefold() == district.casefold()), None)
    if not match:
        close = get_close_matches(district, districts, n=3, cutoff=0.72)
        return {"available": False, "message": "District was not found in the uploaded crop dataset.", "suggested_districts": close, "crops": []}
    subset = frame[frame["district"].astype(str).str.casefold() == match.casefold()]
    if state:
        s = subset[subset["state"].astype(str).str.casefold() == state.casefold()]
        if not s.empty:
            subset = s
    subset = subset.copy()
    if subset["year"].notna().any():
        latest_year = int(subset["year"].max())
        # Keep up to five most recent years to reduce sensitivity to one season.
        subset = subset[subset["year"].isna() | (subset["year"] >= latest_year - 4)]
    # Compute mean annual values rather than summing area/production over several years.
    # Summed area across years is an area-year quantity and can be misread as a single-year area.
    crop_year = subset.groupby(["crop", "season", "year"], dropna=False).agg(
        area_ha=("area", "sum"), production_t=("production", "sum")
    ).reset_index()
    crops = crop_year.groupby("crop").agg(
        mean_annual_area_ha=("area_ha", "mean"),
        mean_annual_production_t=("production_t", "mean"),
        seasons=("season", lambda values: sorted(set(map(str, values)))),
        years_observed=("year", "nunique"),
    ).reset_index().sort_values(
        ["mean_annual_area_ha", "mean_annual_production_t"], ascending=False, na_position="last"
    ).head(top_n)

    season_year = subset.groupby(["season", "year"], dropna=False).agg(
        area_ha=("area", "sum"), production_t=("production", "sum")
    ).reset_index()
    season_summary = season_year.groupby("season", dropna=True).agg(
        mean_annual_area_ha=("area_ha", "mean"),
        mean_annual_production_t=("production_t", "mean"),
        years_observed=("year", "nunique"),
    ).reset_index().sort_values(
        ["mean_annual_area_ha", "mean_annual_production_t"], ascending=False, na_position="last"
    )
    seasonal_patterns = [{
        "season": str(row.season),
        "mean_annual_area_ha": None if pd.isna(row.mean_annual_area_ha) else round(float(row.mean_annual_area_ha), 1),
        "mean_annual_production_t": None if pd.isna(row.mean_annual_production_t) else round(float(row.mean_annual_production_t), 1),
        "years_observed": int(row.years_observed),
    } for row in season_summary.itertuples()]
    dominant_season = seasonal_patterns[0]["season"] if seasonal_patterns else None
    # A simple district-level historical trend baseline is shown only when at least
    # three annual observations exist. It is not a farm yield or crop-suitability model.
    trend_projections = []
    if "year" in subset and subset["year"].notna().any():
        for crop_name, crop_rows in subset.groupby("crop"):
            annual = crop_rows.dropna(subset=["year"]).groupby("year", as_index=False).agg(
                area=("area", "sum"), production=("production", "sum")
            ).sort_values("year").tail(5)
            if len(annual) < 3:
                continue
            years = annual["year"].astype(float).to_numpy()
            target_year = int(np.nanmax(years)) + 1
            prediction = {"crop": str(crop_name), "target_year": target_year,
                          "years_used": [int(y) for y in years], "method": "Linear trend baseline on district historical totals"}
            for source_col, output_key in (("area", "area_ha"), ("production", "production_t")):
                values = pd.to_numeric(annual[source_col], errors="coerce").to_numpy(dtype=float)
                valid = np.isfinite(values)
                if valid.sum() >= 3:
                    estimate = float(np.polyval(np.polyfit(years[valid], values[valid], 1), target_year))
                    prediction[output_key] = round(max(0.0, estimate), 1)
                else:
                    prediction[output_key] = None
            if prediction["area_ha"] is not None or prediction["production_t"] is not None:
                trend_projections.append(prediction)
        trend_projections.sort(key=lambda item: item.get("production_t") or 0, reverse=True)
    return {
        "available": not crops.empty, "district": match,
        "state": subset["state"].iloc[0] if not subset.empty else state,
        "period": f"Recent available years ending {int(subset['year'].max())}" if subset["year"].notna().any() else "Uploaded dataset period",
        "source": metadata.get("provenance", "User-uploaded district crop statistics; origin not independently verified."),
        "data_type": metadata.get("data_type", "unknown"),
        "dominant_historical_season": dominant_season,
        "trend_projections": trend_projections,
        "trend_note": "Historical trend baseline for district totals only. Not a farm-level yield prediction, crop recommendation or guarantee.",
        "seasonal_patterns": seasonal_patterns,
        "crops": [{"crop": row.crop,
                   "mean_annual_area_ha": None if pd.isna(row.mean_annual_area_ha) else round(float(row.mean_annual_area_ha), 1),
                   "mean_annual_production_t": None if pd.isna(row.mean_annual_production_t) else round(float(row.mean_annual_production_t), 1),
                   "years_observed": int(row.years_observed),
                   "seasons": row.seasons} for row in crops.itertuples()],
        "message": "Historical district cropping pattern averaged over available years, not a crop-suitability, profitability or yield prediction.",
    }


def generate_regional_actions(climate: dict, forecast: dict, soil: dict, crop_pattern: dict) -> list[dict]:
    actions = []
    rain = forecast.get("total_precipitation_mm")
    max_temp = forecast.get("max_temperature_c")
    max_prob = forecast.get("max_precipitation_probability_pct")
    if rain is not None and rain >= 20:
        actions.append({"level": "Review", "title": "Review irrigation timing against forecast rain",
                        "detail": f"The 7-day forecast totals about {rain:.1f} mm of precipitation. Check local field moisture and crop stage before scheduling irrigation."})
    elif rain is not None and rain <= 5 and max_temp is not None and max_temp >= 32:
        actions.append({"level": "Monitor", "title": "Monitor moisture and heat conditions",
                        "detail": f"The 7-day forecast is relatively dry ({rain:.1f} mm) and reaches about {max_temp:.1f} °C. Inspect field moisture and crop stress; do not infer irrigation need from weather alone."})
    elif rain is not None:
        actions.append({"level": "Monitor", "title": "Use the local forecast in short-term planning",
                        "detail": f"Forecast precipitation is about {rain:.1f} mm over seven days. Reassess after actual rainfall and field inspection."})
    if max_prob is not None and max_prob >= 70:
        actions.append({"level": "Watch", "title": "Check high-probability rainfall days",
                        "detail": "One or more forecast days have a high precipitation probability. Review field access, drainage and irrigation plans."})
    if soil.get("status") == "available":
        pH = soil.get("properties", {}).get("ph", {}).get("value")
        sand = soil.get("properties", {}).get("sand_pct", {}).get("value")
        clay = soil.get("properties", {}).get("clay_pct", {}).get("value")
        if pH is not None and (pH < 5.5 or pH > 8.0):
            actions.append({"level": "Verify", "title": "Confirm soil pH with a laboratory test",
                            "detail": f"The mapped topsoil pH estimate is {pH:.1f}. Verify it with a representative field soil test before considering amendments."})
        if sand is not None and sand >= 70:
            actions.append({"level": "Field check", "title": "Check infiltration and moisture retention",
                            "detail": f"The mapped topsoil estimate is sand-dominant ({sand:.0f}% sand). Inspect actual infiltration and soil moisture in the field before setting irrigation intervals."})
        elif clay is not None and clay >= 40:
            actions.append({"level": "Field check", "title": "Check drainage after rainfall",
                            "detail": f"The mapped topsoil estimate is clay-dominant ({clay:.0f}% clay). Inspect drainage and waterlogging risk in the field after rainfall."})
        actions.append({"level": "Verify", "title": "Use a field Soil Health Card for fertilizer planning",
                        "detail": "The mapped layer does not provide a complete field-specific available N–P–K and micronutrient diagnosis. Use a current soil-test report for fertilizer decisions."})
    else:
        actions.append({"level": "Data needed", "title": "Add a field soil-test report",
                        "detail": "SoilGrids data were unavailable for this request. Enter or upload laboratory pH, EC, organic carbon and N–P–K results before assessing fertility."})
    if crop_pattern.get("available"):
        top = ", ".join(x["crop"] for x in crop_pattern["crops"][:4])
        source_label = "synthetic presentation data" if crop_pattern.get("data_type") == "synthetic_demo" else "loaded district crop statistics"
        actions.append({"level": "Information", "title": "Review the district cropping pattern",
                        "detail": f"The {source_label} list {top} among the leading crops by recorded area/production. This describes district history, not a farm-specific recommendation to plant them."})
    else:
        actions.append({"level": "Data needed", "title": "Load district crop-production statistics",
                        "detail": "Upload the Government of India district-wise crop-production CSV to identify crops historically grown in this district."})
    return actions


def analyze_region(location: dict) -> dict:
    """Assemble farm-region intelligence while preserving partial source results.

    A timeout from one public data provider must not blank every other panel.
    Unavailable sources are returned with explicit status/reason fields; model
    predictions remain unavailable whenever their required observed/forecast
    inputs cannot be verified.
    """
    lat = float(location["latitude"]); lon = float(location["longitude"])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Latitude/longitude is outside valid geographic bounds.")
    source_errors = []
    try:
        climate = fetch_nasa_climate(lat, lon)
    except Exception as exc:
        climate = {"status": "unavailable", "source": "NASA POWER", "period": "Unavailable",
                   "monthly": [], "annual_rainfall": [], "reason": str(exc)[:240]}
        source_errors.append({"source": "NASA POWER historical climate", "reason": str(exc)[:240]})
    try:
        weather = fetch_weather_forecast(lat, lon)
    except Exception as exc:
        weather = {"status": "unavailable", "source": "Open-Meteo Forecast API", "daily": [],
                   "total_precipitation_mm": None, "max_temperature_c": None,
                   "max_precipitation_probability_pct": None, "reason": str(exc)[:240]}
        source_errors.append({"source": "Open-Meteo 7-day forecast", "reason": str(exc)[:240]})
    try:
        soil = fetch_soil_profile(lat, lon)
    except Exception as exc:
        soil = {"status": "unavailable", "source": "ISRIC SoilGrids WCS", "properties": {},
                "texture_group_screening": None, "limitations": "Mapped soil estimate unavailable; obtain a field soil test.",
                "warnings": [str(exc)[:240]]}
        source_errors.append({"source": "ISRIC SoilGrids", "reason": str(exc)[:240]})
    crops = get_crop_pattern(location.get("admin2") or location.get("district"), location.get("admin1") or location.get("state"))
    if not weather.get("daily"):
        regional_prediction = {"status": "unavailable", "reason": "A current 7-day weather forecast was unavailable; the regional recursive model was not run."}
    else:
        try:
            regional_prediction = forecast_regional_rootzone_moisture(lat, lon, weather)
        except Exception as exc:
            regional_prediction = {"status": "unavailable", "reason": str(exc)[:300]}
    actions = generate_regional_actions(climate, weather, soil, crops)
    indian_context = context_for_location(location)
    problem_report = build_regional_problem_report(location, indian_context, climate, weather, soil, crops)
    if regional_prediction.get("status") == "available" and regional_prediction.get("forecasts"):
        first = regional_prediction["forecasts"][0]
        if first.get("predicted_volumetric_percent") is not None:
            actions.insert(0, {"level": "Model estimate", "title": "Review predicted regional root-zone moisture",
                               "detail": f"The selected point model forecasts {first['predicted_volumetric_percent']:.1f}% for {first['date']}. This is a coarse grid model estimate; check field moisture before any action."})
    data_notes = [
        "Climate profile uses NASA POWER gridded daily meteorological estimates for 2016–2025, not station observations at the farm gate.",
        "Seven-day weather forecast is model output, not a guarantee.",
        "SoilGrids values are 250 m modelled soil-property estimates for a surrounding area; they are not a field sample.",
        "District crop patterns are shown only when a crop-statistics CSV is loaded; inspect its provenance label before interpreting the figures.",
        "The existing EcoIrrigate moisture model is trained on two experimental Kolkata farms and is not applied to this arbitrary location.",
    ]
    if source_errors:
        data_notes.append("One or more regional providers did not respond. Available panels remain visible; unavailable panels show their reason. Check internet access and retry.")
    return {
        "location": location, "climate": climate, "weather_forecast": weather,
        "soil": soil, "crop_pattern": crops, "regional_prediction": regional_prediction,
        "indian_context": indian_context, "regional_problem_report": problem_report,
        "next_actions": actions, "source_errors": source_errors,
        "data_notes": data_notes,
        "sources": {
            "geocoding": "https://open-meteo.com/en/docs/geocoding-api",
            "climate": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
            "forecast": "https://open-meteo.com/en/docs",
            "soil": "https://docs.isric.org/globaldata/soilgrids/wcs.html",
            "crops": "https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0",
            "soil_health": "https://soilhealth.dac.gov.in/",
            "district_contingency_plans": "https://www.icar-crida.res.in/Crop_Contingency_Plan.html",
        },
    }
