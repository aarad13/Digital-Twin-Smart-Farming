import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from app.services import india_crop_model


def make_weather(start="2016-01-01", end="2021-12-31"):
    dates = pd.date_range(start, end, freq="D")
    day = np.arange(len(dates), dtype=float)
    return pd.DataFrame({
        "T2M": 24 + np.sin(day / 30),
        "T2M_MAX": 31 + np.sin(day / 30),
        "T2M_MIN": 18 + np.sin(day / 30),
        "PRECTOTCORR": np.where(pd.Series(dates).dt.month.isin([6, 7, 8, 9]), 4.0, 0.5),
        "RH2M": 60 + np.sin(day / 20),
        "WS2M": 2.5 + np.sin(day / 15) * 0.1,
        "ALLSKY_SFC_SW_DWN": 5.2 + np.sin(day / 40) * 0.2,
    }, index=dates)


def test_season_periods_retain_daily_weather_columns():
    frame = make_weather()
    periods = india_crop_model._season_periods(frame, "Kharif")
    assert len(periods) >= 5
    assert all("T2M" in block.columns and "PRECTOTCORR" in block.columns for block in periods)
    assert all(100 <= len(block) <= 160 for block in periods if len(block))


def test_climate_feature_builder_returns_complete_model_feature_names():
    frame = make_weather()
    result = india_crop_model._climate_features(frame, "Kharif", elevation_m=540)
    assert set(result) == set(india_crop_model.CLIMATE_COLUMNS)
    assert result["temp_mean_c"] is not None
    assert result["rainfall_mm"] > 0
    assert result["elevation_m"] == 540.0
    assert result["solar_mj_m2_day"] > 0


def test_indian_season_names_map_to_source_dataset_categories():
    assert india_crop_model._season_name("Kharif") == "Kharif"
    assert india_crop_model._season_name("Rabi") == "Rabi"
    assert india_crop_model._season_name("Zaid") == "Summer"
    assert india_crop_model._season_name("Perennial") == "Whole Year"
    assert india_crop_model._season_name("unknown") == ""


def test_missing_trained_model_exposes_simple_prepare_command(monkeypatch, tmp_path):
    monkeypatch.setattr(india_crop_model, "MODEL_FILE", tmp_path / "not-trained.joblib")
    status = india_crop_model.model_status()
    assert status["available"] is False
    assert "prepare_india_crop_model.py" in status["prepare_command"]
    assert status["license"] == "CC BY 4.0"
    assert status["source_dataset_url"].startswith("https://github.com/")


def test_prepare_script_requires_documented_dataset_features():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "prepare_india_crop_model.py"
    spec = importlib.util.spec_from_file_location("prepare_india_crop_model_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "dominant_crop" in module.REQUIRED_COLUMNS
    assert "district_key" in module.REQUIRED_COLUMNS
    assert "soil_ph_h2o_0_5cm" in module.REQUIRED_COLUMNS
    assert "annual_rainfall_mm" in module.REQUIRED_COLUMNS
    assert module.DATA_FILE.name == "india_district_crop_dataset_1997_2015.csv"


def test_classifier_prediction_reports_vote_share_not_success_probability(monkeypatch, tmp_path):
    from app.services.india_crop_model import SOIL_FEATURE_MAP

    expected_columns = list(SOIL_FEATURE_MAP) + india_crop_model.CLIMATE_COLUMNS + ["season"]

    class DummyClassifier:
        classes_ = np.array(["Maize", "Rice", "Soybean"])

        def predict_proba(self, matrix):
            assert list(matrix.columns) == expected_columns
            return np.array([[0.2, 0.5, 0.3]])

    model_file = tmp_path / "model.joblib"
    model_file.write_bytes(b"model")
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text('{"rows_used": 1000, "districts": 25, "crop_classes": ["Rice", "Soybean", "Maize"], "validation": {"mean_accuracy": 0.4}}')
    monkeypatch.setattr(india_crop_model, "MODEL_FILE", model_file)
    monkeypatch.setattr(india_crop_model, "MANIFEST_FILE", manifest_file)
    monkeypatch.setattr(india_crop_model, "_read_daily_weather", lambda lat, lon: make_weather())
    monkeypatch.setattr(india_crop_model.joblib, "load", lambda path: DummyClassifier())
    properties = {
        key: {"value": 1.0} for key in SOIL_FEATURE_MAP.values()
    }
    result = india_crop_model.predict_indian_crop_pattern(
        23.2, 77.4, "Kharif", {"properties": properties}, elevation_m=500
    )
    assert result["status"] == "available"
    assert result["top_historical_crops"][0]["crop"] == "Rice"
    assert result["top_historical_crops"][0]["model_vote_share_pct"] == 50.0
    assert "similarity_probability_pct" not in result["top_historical_crops"][0]
    assert "not probability of farm success" in result["score_interpretation"]


def test_downloaded_dataset_pipeline_fits_a_small_representative_frame():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "prepare_india_crop_model.py"
    spec = importlib.util.spec_from_file_location("prepare_india_crop_model_pipeline_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = 48
    frame = pd.DataFrame({
        name: np.linspace(1, 10, rows) for name in module.NUMERIC_FEATURES
    })
    frame["season"] = ["Kharif", "Rabi", "Summer"] * (rows // 3)
    target = np.array(["Rice", "Wheat", "Maize"] * (rows // 3))
    pipeline = module.build_pipeline()
    pipeline.fit(frame, target)
    assert pipeline.predict(frame.iloc[:3]).tolist() == target[:3].tolist()
    probabilities = pipeline.predict_proba(frame.iloc[:3])
    assert np.allclose(probabilities.sum(axis=1), 1.0)
