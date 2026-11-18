"""Import the supplied EcoIrrigate CSV into MySQL (idempotent by farm/time)."""
from pathlib import Path
import argparse
import math
import os
import sys
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

REQUIRED = [
    "Timestamp", "Farm_ID", "Volumetric_Moisture_Pct",
    "Sensor_Board_Temperature_C", "Raw_Capacitive_ADC", "Sensor_Voltage_V",
    "Atm_Pressure_inHg", "Atm_Temperature_C", "Soil_Temperature_C",
    "SM_Level_15cm", "SM_Volume_15cm", "SM_Aggregate_Pct", "SM_Volume_Pct",
    "Hour", "Day", "Month", "DayOfWeek", "DayOfYear",
    "Hour_sin", "Hour_cos", "Day_sin", "Day_cos"
]


def clean(v):
    if pd.isna(v):
        return None
    if isinstance(v, np.generic):
        v = v.item()
    if hasattr(v, "to_pydatetime"):
        return v.to_pydatetime()
    if isinstance(v, (int,)):
        return int(v)
    if isinstance(v, (float,)):
        return float(v)
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "kolkata_unified_dataset.csv"))
    args = ap.parse_args()
    df = pd.read_csv(args.data)
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="raise")
    df = df.sort_values(["Farm_ID", "Timestamp"]).drop_duplicates(["Farm_ID", "Timestamp"])
    if df["Volumetric_Moisture_Pct"].isna().any():
        raise ValueError("Target soil-moisture column contains missing values.")
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "smart_farming_digital_twin"),
        charset="utf8mb4", cursorclass=DictCursor, autocommit=False
    )
    imported = 0
    try:
        with conn.cursor() as cur:
            farm_map = {}
            for farm_code in sorted(df["Farm_ID"].unique()):
                cur.execute("""INSERT INTO farms (farm_code, display_name, location)
                            VALUES (%s,%s,%s)
                            ON DUPLICATE KEY UPDATE display_name=VALUES(display_name)""",
                            (farm_code, farm_code.replace("_", " "), "Kolkata, West Bengal, India"))
                cur.execute("SELECT farm_id FROM farms WHERE farm_code=%s", (farm_code,))
                farm_map[farm_code] = cur.fetchone()["farm_id"]

            sql = """INSERT INTO observations
            (farm_id, observed_at, moisture_pct, sensor_board_temp_c, raw_capacitive_adc,
             sensor_voltage_v, atmospheric_pressure_inhg, atmospheric_temp_c, soil_temp_c,
             sm_level_15cm, sm_volume_15cm, sm_aggregate_pct, sm_volume_pct,
             hour_value, day_value, month_value, day_of_week, day_of_year,
             hour_sin, hour_cos, day_sin, day_cos, source_name)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              moisture_pct=VALUES(moisture_pct), sensor_board_temp_c=VALUES(sensor_board_temp_c),
              raw_capacitive_adc=VALUES(raw_capacitive_adc), sensor_voltage_v=VALUES(sensor_voltage_v),
              atmospheric_pressure_inhg=VALUES(atmospheric_pressure_inhg),
              atmospheric_temp_c=VALUES(atmospheric_temp_c), soil_temp_c=VALUES(soil_temp_c),
              sm_level_15cm=VALUES(sm_level_15cm), sm_volume_15cm=VALUES(sm_volume_15cm),
              sm_aggregate_pct=VALUES(sm_aggregate_pct), sm_volume_pct=VALUES(sm_volume_pct),
              hour_value=VALUES(hour_value), day_value=VALUES(day_value), month_value=VALUES(month_value),
              day_of_week=VALUES(day_of_week), day_of_year=VALUES(day_of_year),
              hour_sin=VALUES(hour_sin), hour_cos=VALUES(hour_cos), day_sin=VALUES(day_sin), day_cos=VALUES(day_cos)"""
            batch = []
            for row in df.itertuples(index=False):
                r = row._asdict()
                vals = (
                    farm_map[r["Farm_ID"]], clean(r["Timestamp"]), clean(r["Volumetric_Moisture_Pct"]),
                    clean(r["Sensor_Board_Temperature_C"]), clean(r["Raw_Capacitive_ADC"]),
                    clean(r["Sensor_Voltage_V"]), clean(r["Atm_Pressure_inHg"]),
                    clean(r["Atm_Temperature_C"]), clean(r["Soil_Temperature_C"]),
                    clean(r["SM_Level_15cm"]), clean(r["SM_Volume_15cm"]), clean(r["SM_Aggregate_Pct"]),
                    clean(r["SM_Volume_Pct"]), clean(r["Hour"]), clean(r["Day"]), clean(r["Month"]),
                    clean(r["DayOfWeek"]), clean(r["DayOfYear"]), clean(r["Hour_sin"]), clean(r["Hour_cos"]),
                    clean(r["Day_sin"]), clean(r["Day_cos"]), "EcoIrrigate Mendeley Data v1"
                )
                batch.append(vals)
                if len(batch) >= 1000:
                    cur.executemany(sql, batch); imported += len(batch); batch.clear()
            if batch:
                cur.executemany(sql, batch); imported += len(batch)
        conn.commit()
        print(f"Imported/updated {imported:,} observations across {len(farm_map)} farms.")
        print("Dataset: EcoIrrigate, Mendeley Data v1, DOI: 10.17632/8x4v7yy3ds.1 (CC BY 4.0).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
