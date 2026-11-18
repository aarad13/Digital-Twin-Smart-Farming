"""Small MySQL data-access layer using PyMySQL."""
import os
from contextlib import contextmanager


def connect(database=True):
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:
        raise RuntimeError("PyMySQL is not installed. Run: pip install -r requirements.txt") from exc
    kwargs = dict(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=8,
    )
    if database:
        kwargs["database"] = os.getenv("MYSQL_DATABASE", "smart_farming_digital_twin")
    return pymysql.connect(**kwargs)


@contextmanager
def db_cursor(commit=False):
    conn = connect()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_farms():
    with db_cursor() as cur:
        cur.execute("""SELECT farm_id, farm_code, display_name, location, crop_name,
                       soil_type, field_area_ha, moisture_threshold_pct, threshold_note
                       FROM farms ORDER BY display_name""")
        return cur.fetchall()


def get_farm_by_code(code):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM farms WHERE farm_code=%s", (code,))
        return cur.fetchone()


def get_observations(farm_id, limit=500):
    limit = max(1, min(int(limit), 5000))
    with db_cursor() as cur:
        cur.execute(f"""SELECT observed_at, moisture_pct, atmospheric_temp_c,
                         atmospheric_pressure_inhg, soil_temp_c, sensor_board_temp_c,
                         raw_capacitive_adc, sensor_voltage_v
                  FROM observations WHERE farm_id=%s
                  ORDER BY observed_at DESC LIMIT {limit}""", (farm_id,))
        rows = cur.fetchall()
    return list(reversed(rows))


def get_recent_model_rows(farm_id, limit=600):
    limit = max(300, min(int(limit), 1200))
    with db_cursor() as cur:
        cur.execute(f"""SELECT observed_at AS Timestamp,
                    moisture_pct AS Volumetric_Moisture_Pct,
                    atmospheric_temp_c AS Atm_Temperature_C,
                    atmospheric_pressure_inhg AS Atm_Pressure_inHg,
                    soil_temp_c AS Soil_Temperature_C,
                    sensor_board_temp_c AS Sensor_Board_Temperature_C,
                    hour_sin AS Hour_sin, hour_cos AS Hour_cos,
                    day_sin AS Day_sin, day_cos AS Day_cos
                 FROM observations WHERE farm_id=%s
                 ORDER BY observed_at DESC LIMIT {limit}""", (farm_id,))
        rows = cur.fetchall()
    rows.reverse()
    return rows


def insert_forecast_and_advisory(farm_id, origin_at, target_at, horizon_minutes,
                                 model_name, feature_set, predicted, current,
                                 threshold, level, message):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO forecasts
                (farm_id, origin_at, target_at, horizon_minutes, model_name,
                 feature_set, predicted_moisture_pct)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (farm_id, origin_at, target_at, horizon_minutes, model_name,
                 feature_set, float(predicted)))
            forecast_id = cur.lastrowid
            cur.execute("""INSERT INTO advisories
                (forecast_id, farm_id, current_moisture_pct, predicted_moisture_pct,
                 threshold_pct, advisory_level, advisory_text)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (forecast_id, farm_id, float(current), float(predicted),
                 float(threshold), level, message))
        conn.commit()
        return forecast_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_recent_forecasts(farm_id, limit=12):
    limit = max(1, min(int(limit), 50))
    with db_cursor() as cur:
        cur.execute(f"""SELECT f.forecast_id, f.origin_at, f.target_at,
                       f.horizon_minutes, f.model_name, f.predicted_moisture_pct,
                       a.threshold_pct, a.advisory_level, a.advisory_text, f.generated_at
                    FROM forecasts f LEFT JOIN advisories a ON a.forecast_id=f.forecast_id
                    WHERE f.farm_id=%s ORDER BY f.generated_at DESC LIMIT {limit}""", (farm_id,))
        return cur.fetchall()
