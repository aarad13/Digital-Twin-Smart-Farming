import io

import pandas as pd

from app.services import regional


class NamedStringIO(io.StringIO):
    filename = "district_crop_statistics.csv"


def test_crop_statistics_upload_normalizes_official_style_headers(tmp_path, monkeypatch):
    monkeypatch.setattr(regional, "CROP_FILE", tmp_path / "crop_production.csv")
    csv_text = (
        "State_Name,District_Name,Crop_Year,Season,Crop,Area,Production\n"
        "Madhya Pradesh,Sehore,2021-22,Kharif,Soybean,100,150\n"
        "Madhya Pradesh,Sehore,2022-23,Kharif,Soybean,120,180\n"
        "Madhya Pradesh,Sehore,2022-23,Rabi,Wheat,80,240\n"
        "Maharashtra,Pune,2022-23,Rabi,Wheat,70,210\n"
    )
    uploaded = NamedStringIO(csv_text)
    result = regional.save_crop_statistics_csv(uploaded)
    assert result["rows"] == 4
    assert result["states"] == 2
    assert result["districts"] == 2
    pattern = regional.get_crop_pattern("Sehore", "Madhya Pradesh")
    assert pattern["available"] is True
    assert {item["crop"] for item in pattern["crops"]} == {"Soybean", "Wheat"}


def test_crop_statistics_upload_rejects_missing_required_columns(tmp_path, monkeypatch):
    monkeypatch.setattr(regional, "CROP_FILE", tmp_path / "crop_production.csv")
    uploaded = NamedStringIO("State,District,Crop\nMadhya Pradesh,Sehore,Soybean\n")
    try:
        regional.save_crop_statistics_csv(uploaded)
    except ValueError as exc:
        assert "Season" in str(exc)
    else:
        raise AssertionError("CSV without Season column should be rejected")


def test_regional_weather_features_use_previous_day_only():
    dates = pd.date_range("2025-01-01", periods=12, freq="D")
    frame = pd.DataFrame({
        "target": [0.1 + i * 0.01 for i in range(12)],
        "T2M": [20 + i for i in range(12)],
        "PRECTOTCORR": [i for i in range(12)],
        "RH2M": [50 + i for i in range(12)],
        "WS2M": [2 + i for i in range(12)],
    }, index=dates)
    X, _, _ = regional._regional_features(frame)
    # Feature row for 2025-01-08 uses 2025-01-07 weather, not same-day weather.
    assert X.loc[pd.Timestamp("2025-01-08"), "T2M_lag_1d"] == 26
    assert X.loc[pd.Timestamp("2025-01-08"), "PRECTOTCORR_lag_1d"] == 6


def test_synthetic_demo_crop_statistics_load_with_provenance_and_district_trends(tmp_path, monkeypatch):
    monkeypatch.setattr(regional, "CROP_FILE", tmp_path / "crop_production.csv")
    monkeypatch.setattr(regional, "CROP_METADATA_FILE", tmp_path / "crop_production_metadata.json")
    summary = regional.load_demo_crop_statistics()
    assert summary["rows"] > 0
    assert summary["districts"] == 2
    pattern = regional.get_crop_pattern("Sehore", "Madhya Pradesh")
    assert pattern["available"] is True
    assert pattern["data_type"] == "synthetic_demo"
    assert "NOT GOVERNMENT DATA" in pattern["source"]
    soybean = next(item for item in pattern["trend_projections"] if item["crop"] == "Soybean")
    assert soybean["target_year"] == 2025
    assert soybean["area_ha"] is not None
    assert soybean["production_t"] is not None


def test_crop_year_ranges_are_normalised_to_starting_year():
    frame = pd.DataFrame({
        "State_Name": ["Madhya Pradesh", "Madhya Pradesh", "Madhya Pradesh"],
        "District_Name": ["Sehore", "Sehore", "Sehore"],
        "Crop_Year": ["2021-22", "2022-23", "2023-24"],
        "Season": ["Kharif", "Kharif", "Kharif"],
        "Crop": ["Soybean", "Soybean", "Soybean"],
        "Area": [100, 110, 120],
        "Production": [150, 165, 180],
    })
    clean = regional._normalise_crop_frame(frame)
    assert clean["year"].tolist() == [2021, 2022, 2023]


def test_regional_analysis_returns_partial_results_when_one_provider_is_unavailable(monkeypatch):
    def broken_climate(*_args, **_kwargs):
        raise RuntimeError("NASA POWER test outage")

    monkeypatch.setattr(regional, "fetch_nasa_climate", broken_climate)
    monkeypatch.setattr(regional, "fetch_weather_forecast", lambda *_args, **_kwargs: {
        "source": "Open-Meteo test", "daily": [], "total_precipitation_mm": None,
        "max_temperature_c": None, "max_precipitation_probability_pct": None,
    })
    monkeypatch.setattr(regional, "fetch_soil_profile", lambda *_args, **_kwargs: {
        "source": "SoilGrids test", "status": "unavailable", "properties": {},
        "texture_group_screening": None, "limitations": "Unavailable",
    })
    monkeypatch.setattr(regional, "get_crop_pattern", lambda *_args, **_kwargs: {
        "available": False, "message": "No crop CSV", "crops": [],
    })
    result = regional.analyze_region({
        "name": "Test village", "admin1": "Madhya Pradesh", "admin2": "Sehore",
        "country": "India", "latitude": 23.2, "longitude": 77.1,
    })
    assert result["climate"]["status"] == "unavailable"
    assert result["weather_forecast"]["daily"] == []
    assert result["regional_prediction"]["status"] == "unavailable"
    assert result["source_errors"][0]["source"] == "NASA POWER historical climate"
