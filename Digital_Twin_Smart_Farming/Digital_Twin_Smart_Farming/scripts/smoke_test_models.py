"""Database-independent smoke test for the trained inference artifacts."""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.prediction import predict_options


def main():
    df = pd.read_csv(ROOT / "data" / "kolkata_unified_dataset.csv", parse_dates=["Timestamp"])
    for farm_code, group in df.groupby("Farm_ID"):
        g = group.sort_values("Timestamp").tail(600)
        columns = ["Timestamp", "Volumetric_Moisture_Pct", "Atm_Temperature_C",
                   "Atm_Pressure_inHg", "Soil_Temperature_C", "Sensor_Board_Temperature_C",
                   "Hour_sin", "Hour_cos", "Day_sin", "Day_cos"]
        rows = g[columns].to_dict("records")
        for horizon in (1, 6):
            result = predict_options(farm_code, horizon, rows)
            print(f"{farm_code} | {horizon}h | current={result['current_moisture']:.3f}%")
            for option in result["options"]:
                print(f"  {option['model_name']:<24} {option['predicted']:.3f}%")
    print("Model smoke test completed. Database/API integration still requires a configured MySQL service.")

if __name__ == "__main__":
    main()
