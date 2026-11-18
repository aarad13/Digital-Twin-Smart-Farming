"""Pre-run integrity checks for the Smart Farming Digital Twin package."""
from __future__ import annotations
import argparse
import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)
    print(f"[OK] {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-only", action="store_true", help="Skip web/geospatial dependency and database checks")
    parser.add_argument("--with-db", action="store_true", help="Also test Flask rendering and MySQL table connectivity")
    args = parser.parse_args()

    must_exist = [
        "app/app.py", "app/db.py", "app/serialization.py", "app/templates/index.html",
        "app/static/css/styles.css", "app/static/js/auth-ui.js", "app/static/js/dashboard.js", "app/static/js/virtual-farm.js", "app/static/js/farmer-ui.js", "app/static/js/service-desk.js", "app/static/js/farm-outlook.js",
        "sql/schema.sql", "data/kolkata_unified_dataset.csv", "models/predictive_models.joblib",
        "models/training_manifest.json", "scripts/init_db.py", "scripts/import_dataset.py", "scripts/seed_demo_data.py", "ASSISTED_VILLAGE_SERVICE_GUIDE.md",
        "scripts/train_models.py", "scripts/wait_for_mysql.py", "scripts/docker_entrypoint.sh", "scripts/migrate_app_access.py", "scripts/create_user.py", "scripts/prepare_india_crop_model.py", "app/services/india_crop_model.py", "AUTH_AND_ACCESS_GUIDE.md", "FARM_PREDICTIONS_AND_REGIONAL_DATA_GUIDE.md", "DATASET_SOURCES_AND_PREDICTIONS.md", "DATASET_SETUP_QUICKSTART.md", "app/static/DATASET_SOURCES_AND_PREDICTIONS.md", "data/regional/README.md", "data/demo/DEMO_CROP_STATISTICS_SYNTHETIC.csv",
        "setup_windows.bat", "RUN_WINDOWS.bat", "setup_mac_linux.sh", "run_mac_linux.sh",
        ".env.example", ".dockerignore", "Dockerfile", "requirements.txt", "docker-compose.yml",
    ]
    missing = [rel for rel in must_exist if not (ROOT / rel).is_file()]
    require(not missing, "Required project files are present" if not missing else f"Missing required files: {missing}")

    py_files = list((ROOT / "app").rglob("*.py")) + list((ROOT / "scripts").rglob("*.py")) + list((ROOT / "tests").rglob("*.py"))
    py_files.append(ROOT / "run.py")
    for path in py_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    require(True, f"Python syntax valid ({len(py_files)} files)")

    import pandas as pd
    df = pd.read_csv(ROOT / "data/kolkata_unified_dataset.csv", parse_dates=["Timestamp"])
    expected_shape = (21312, 22)
    require(df.shape == expected_shape, f"Bundled dataset shape is {expected_shape}")
    required_columns = {
        "Timestamp", "Farm_ID", "Volumetric_Moisture_Pct", "Sensor_Board_Temperature_C",
        "Raw_Capacitive_ADC", "Sensor_Voltage_V", "Atm_Pressure_inHg", "Atm_Temperature_C",
        "Soil_Temperature_C", "SM_Level_15cm", "SM_Volume_15cm", "SM_Aggregate_Pct", "SM_Volume_Pct",
        "Hour", "Day", "Month", "DayOfWeek", "DayOfYear", "Hour_sin", "Hour_cos", "Day_sin", "Day_cos",
    }
    require(required_columns.issubset(df.columns), "Dataset contains every required feature column")
    require(not df[list(required_columns)].isna().any().any(), "Dataset has no missing values in required fields")
    require(df.duplicated(["Farm_ID", "Timestamp"]).sum() == 0, "Dataset has no duplicate farm/timestamp records")
    require(df["Volumetric_Moisture_Pct"].between(0, 100).all(), "Soil-moisture target values are within 0–100 percent")
    for farm_id, group in df.groupby("Farm_ID"):
        delta = group.sort_values("Timestamp")["Timestamp"].diff().dropna()
        require(len(group) == 10656 and (delta == pd.Timedelta(minutes=15)).all(), f"{farm_id}: 10,656 records at exact 15-minute intervals")

    import joblib
    artifact = joblib.load(ROOT / "models/predictive_models.joblib")
    require(isinstance(artifact, dict) and len(artifact) == 8, "Eight per-farm/per-horizon model bundles load")
    from app.services.prediction import predict_options
    for farm_id, group in df.groupby("Farm_ID"):
        history = group.tail(1200).copy()
        # Match the columns produced by the SQL model-history query.
        history = history.rename(columns={
            "Volumetric_Moisture_Pct": "Volumetric_Moisture_Pct",
            "Atm_Temperature_C": "Atm_Temperature_C",
            "Atm_Pressure_inHg": "Atm_Pressure_inHg",
            "Soil_Temperature_C": "Soil_Temperature_C",
            "Sensor_Board_Temperature_C": "Sensor_Board_Temperature_C",
        })
        for horizon in (1, 6):
            result = predict_options(farm_id, horizon, history.to_dict(orient="records"))
            values = [item["predicted"] for item in result["options"]]
            require(len(values) == 4 and all(0 <= float(v) <= 100 for v in values), f"{farm_id}: {horizon}-hour forecast smoke test")

    # Check that static JS element references exist in the HTML template.
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    all_ids = re.findall(r'\bid=["\']([^"\']+)["\']', html)
    ids = set(all_ids)
    duplicate_ids = sorted({value for value in all_ids if all_ids.count(value) > 1})
    require(not duplicate_ids, "HTML element IDs are unique" if not duplicate_ids else f"Duplicate HTML IDs: {duplicate_ids}")
    required_views = {"home-view", "field-team-view", "soil-lab-view", "farmer-card-view", "location-view", "farm-view", "outlook-view", "insights-view"}
    require(required_views.issubset(ids), "All assisted-service and legacy farm intelligence views are present")
    require({"farm-outlook-crop-model", "farm-outlook-season", "vf-area", "vf-plot-area"}.issubset(ids), "Indian crop-pattern model and square-foot farm inputs are present")
    js_files = [ROOT / "app/static/js/auth-ui.js", ROOT / "app/static/js/dashboard.js", ROOT / "app/static/js/virtual-farm.js", ROOT / "app/static/js/farmer-ui.js", ROOT / "app/static/js/service-desk.js", ROOT / "app/static/js/farm-outlook.js"]
    missing_ids = []
    for js_path in js_files:
        js = js_path.read_text(encoding="utf-8")
        for element_id in re.findall(r'\$\s*\(\s*["\']([^"\']+)["\']\s*\)', js):
            if element_id not in ids:
                missing_ids.append(f"{js_path.name}: {element_id}")
    require(not missing_ids, "All literal JavaScript DOM IDs exist in the HTML" if not missing_ids else f"Missing HTML IDs: {missing_ids}")

    node_exe = None
    import shutil
    node_exe = shutil.which("node")
    if node_exe:
        for js_path in js_files:
            subprocess.run([node_exe, "--check", str(js_path)], check=True)
        require(True, f"All {len(js_files)} JavaScript files pass Node syntax checks")
    else:
        print("[INFO] Node.js not installed; JavaScript syntax check skipped")

    if not args.core_only:
        dependencies = ["flask", "pymysql", "cryptography", "dotenv", "requests", "owslib", "rasterio", "pyproj", "plotly"]
        missing_deps = [name for name in dependencies if importlib.util.find_spec(name) is None]
        require(not missing_deps, "Web/database/geospatial dependencies are installed" if not missing_deps else f"Missing Python packages: {missing_deps}; run pip install -r requirements.txt")
        if args.with_db:
            from app.app import app
            client = app.test_client()
            response = client.get("/")
            require(response.status_code == 200 and b"Good farming support starts with a village visit" in response.data and b"service-desk.js" in response.data,
                    "Flask application renders the assisted village-service interface")
            from app.db import db_cursor
            with db_cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                require(cursor.fetchone()["ok"] == 1, "MySQL connection is live")
                cursor.execute("SHOW TABLES")
                table_names = {next(iter(row.values())) for row in cursor.fetchall()}
            expected_tables = {"farms", "observations", "forecasts", "advisories", "virtual_farms", "virtual_farm_plots", "virtual_farm_assets", "soil_reports", "field_farmers", "field_visits", "soil_samples", "app_users"}
            require(expected_tables.issubset(table_names), "All twelve MySQL tables exist")

    print("\nProject integrity checks passed. External regional APIs are checked when a location is analyzed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nCHECK FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
