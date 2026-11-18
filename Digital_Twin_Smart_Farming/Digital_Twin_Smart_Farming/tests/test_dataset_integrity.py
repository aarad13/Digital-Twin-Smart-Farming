from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "kolkata_unified_dataset.csv"

REQUIRED = {
    "Timestamp", "Farm_ID", "Volumetric_Moisture_Pct",
    "Sensor_Board_Temperature_C", "Raw_Capacitive_ADC", "Sensor_Voltage_V",
    "Atm_Pressure_inHg", "Atm_Temperature_C", "Soil_Temperature_C",
    "SM_Level_15cm", "SM_Volume_15cm", "SM_Aggregate_Pct", "SM_Volume_Pct",
    "Hour", "Day", "Month", "DayOfWeek", "DayOfYear",
    "Hour_sin", "Hour_cos", "Day_sin", "Day_cos",
}


def test_bundled_dataset_schema_and_completeness():
    assert DATA.exists(), "Bundled EcoIrrigate dataset is missing"
    frame = pd.read_csv(DATA, parse_dates=["Timestamp"])
    assert frame.shape == (21312, 22)
    assert REQUIRED.issubset(frame.columns)
    assert frame[list(REQUIRED)].notna().all().all()
    assert set(frame["Farm_ID"].unique()) == {"Kolkata_Farm_1", "Kolkata_Farm_2"}
    assert frame.duplicated(["Farm_ID", "Timestamp"]).sum() == 0
    assert frame["Volumetric_Moisture_Pct"].between(0, 100).all()


def test_each_farm_has_regular_quarter_hour_sampling():
    frame = pd.read_csv(DATA, parse_dates=["Timestamp"])
    for farm_id, group in frame.groupby("Farm_ID"):
        ordered = group.sort_values("Timestamp")
        deltas = ordered["Timestamp"].diff().dropna()
        assert len(ordered) == 10656, farm_id
        assert (deltas == pd.Timedelta(minutes=15)).all(), farm_id
        assert ordered["Timestamp"].min() == pd.Timestamp("2025-01-05 00:00:00")
        assert ordered["Timestamp"].max() == pd.Timestamp("2025-04-25 23:45:00")
