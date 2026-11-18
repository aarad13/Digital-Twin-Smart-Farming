"""Flask application for the Smart Farming Predictive Digital Twin."""
import os
import uuid
import re
import secrets
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import requests
import pandas as pd
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_from_directory, session, g
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from app import db
from app.serialization import json_safe
from app.services.prediction import predict_options, create_advisory
from app.services import regional
from app.services import virtual_farm
from app.services.india_crop_model import predict_indian_crop_pattern

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-development-key-change-me")
app.config["JSON_SORT_KEYS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0").lower() in ("1", "true", "yes")
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 10  # 10 hours
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB per upload
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", ROOT / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_SOIL_REPORT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp"}


def clean_row(row):
    return json_safe(row)


def api_error(message, status=400):
    return jsonify({"ok": False, "error": str(message)}), status


AUTH_PUBLIC_ENDPOINTS = {"auth_login", "auth_register_farmer", "auth_activate_farmer", "auth_me", "auth_logout"}
ROLE_ENDPOINT_ALLOW = {
    "service_create_farmer": {"government_officer", "company_officer", "admin"},
    "service_create_sample": {"government_officer", "company_officer", "admin"},
    "service_save_sample_results": {"lab_staff", "admin"},
    "region_crop_stats_upload": {"government_officer", "company_officer", "admin"},
    "region_crop_stats_demo": {"government_officer", "company_officer", "admin"},
    "update_farm_settings": {"government_officer", "company_officer", "admin"},
    "virtual_farm_create": {"farmer", "government_officer", "company_officer", "admin"},
    "virtual_farm_save_boundary": {"farmer", "government_officer", "company_officer", "admin"},
    "virtual_farm_add_plot": {"farmer", "government_officer", "company_officer", "admin"},
    "virtual_farm_add_asset": {"farmer", "government_officer", "company_officer", "admin"},
    "upload_soil_report": {"farmer", "government_officer", "company_officer", "admin"},
}


def _public_user(user):
    if not user:
        return None
    return {
        "user_id": int(user["user_id"]),
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"],
        "organization_name": user.get("organization_name"),
        "farmer_id": int(user["farmer_id"]) if user.get("farmer_id") is not None else None,
    }


def _fetch_session_user(user_id):
    with db.db_cursor() as cur:
        cur.execute("""SELECT user_id, username, password_hash, role, display_name,
            organization_name, farmer_id, is_active FROM app_users WHERE user_id=%s""", (user_id,))
        return cur.fetchone()


def _role_name(role):
    return {
        "farmer": "Farmer",
        "government_officer": "Government agriculture / extension officer",
        "company_officer": "Agriculture company / FPO field team",
        "lab_staff": "Soil laboratory staff",
        "admin": "Platform administrator",
    }.get(role, "User")


@app.before_request
def require_authenticated_api_and_role():
    """Protect API records with a signed server-side session and role checks."""
    if not request.path.startswith("/api/") or request.endpoint in AUTH_PUBLIC_ENDPOINTS:
        return None
    user_id = session.get("user_id")
    if not user_id:
        return api_error("Please sign in to continue.", 401)
    try:
        user = _fetch_session_user(user_id)
    except Exception:
        app.logger.exception("Could not validate the active user session")
        return api_error("The service is temporarily unavailable. Please try again.", 503)
    if not user or not int(user.get("is_active", 0)):
        session.clear()
        return api_error("This account is inactive or no longer available. Please sign in again.", 401)
    g.current_user = user
    permitted = ROLE_ENDPOINT_ALLOW.get(request.endpoint)
    if permitted and user["role"] not in permitted:
        return api_error("This task is not available to your account type. Please contact your organisation administrator.", 403)
    return None


def _farmer_owns_record(farmer_id):
    user = getattr(g, "current_user", None)
    if not user:
        return False
    if user["role"] != "farmer":
        return True
    return user.get("farmer_id") is not None and int(user["farmer_id"]) == int(farmer_id)


def _farmer_can_access_virtual_farm(farm_id):
    user = getattr(g, "current_user", None)
    if not user:
        return False
    if user["role"] == "farmer":
        if not user.get("farmer_id"):
            return False
        with db.db_cursor() as cur:
            cur.execute("SELECT 1 FROM field_farmers WHERE farmer_id=%s AND virtual_farm_id=%s", (user["farmer_id"], farm_id))
            return cur.fetchone() is not None
    if user["role"] == "company_officer":
        with db.db_cursor() as cur:
            cur.execute("SELECT 1 FROM field_farmers WHERE virtual_farm_id=%s AND registered_by_organization=%s LIMIT 1",
                        (farm_id, user.get("organization_name")))
            return cur.fetchone() is not None
    if user["role"] == "lab_staff":
        with db.db_cursor() as cur:
            cur.execute("""SELECT 1 FROM field_farmers f JOIN soil_samples s ON s.farmer_id=f.farmer_id
                WHERE f.virtual_farm_id=%s AND s.assigned_lab_organization=%s LIMIT 1""",
                (farm_id, user.get("organization_name")))
            return cur.fetchone() is not None
    return True


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/auth/me")
def auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": True, "authenticated": False, "user": None})
    try:
        user = _fetch_session_user(user_id)
        if not user or not int(user.get("is_active", 0)):
            session.clear()
            return jsonify({"ok": True, "authenticated": False, "user": None})
        return jsonify({"ok": True, "authenticated": True, "user": _public_user(user)})
    except Exception:
        app.logger.exception("Session lookup failed")
        return api_error("Sign-in service is temporarily unavailable. Please try again.", 503)


@app.post("/api/auth/login")
def auth_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    selected_role = str(payload.get("role", "")).strip()
    if not username or not password:
        return api_error("Enter your user ID / mobile number and password.", 422)
    try:
        with db.db_cursor() as cur:
            cur.execute("""SELECT user_id, username, password_hash, role, display_name,
                organization_name, farmer_id, is_active, must_change_password FROM app_users WHERE username=%s LIMIT 1""", (username,))
            user = cur.fetchone()
        if not user or not int(user.get("is_active", 0)) or not check_password_hash(user["password_hash"], password):
            return api_error("The user ID or password is incorrect.", 401)
        if int(user.get("must_change_password", 0)):
            return api_error("Your farmer account is not activated yet. Choose the field-team activation option and enter the code on your farmer slip.", 403)
        if selected_role and selected_role != user["role"]:
            return api_error("This account belongs to a different access type. Choose the correct sign-in option.", 403)
        session.clear()
        session["user_id"] = int(user["user_id"])
        session.permanent = True
        with db.db_cursor(commit=True) as cur:
            cur.execute("UPDATE app_users SET last_login_at=NOW() WHERE user_id=%s", (user["user_id"],))
        return jsonify({"ok": True, "user": _public_user(user), "role_label": _role_name(user["role"])})
    except Exception:
        app.logger.exception("User sign-in failed")
        return api_error("Sign-in could not be completed. Check that the database has been initialized.", 503)


@app.post("/api/auth/register-farmer")
def auth_register_farmer():
    payload = request.get_json(silent=True) or {}
    try:
        name = _service_text(payload.get("farmer_name"), "Farmer name", 160)
        mobile = re.sub(r"\D", "", str(payload.get("mobile", "")))
        if len(mobile) != 10:
            raise ValueError("Enter a valid 10-digit mobile number. This is used as your sign-in ID.")
        password = str(payload.get("password", ""))
        if len(password) < 8:
            raise ValueError("Choose a password with at least 8 characters.")
        village = _service_text(payload.get("village"), "Village", 120)
        district = _service_text(payload.get("district"), "District", 120)
        state = _service_text(payload.get("state"), "State", 120)
        language = _service_text(payload.get("preferred_language") or "Hindi", "Preferred language", 30)
        if payload.get("consent_recorded") is not True:
            raise ValueError("Please confirm consent before creating the farmer account.")
        farmer_code = "FARM-" + uuid.uuid4().hex[:10].upper()
        conn = db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM app_users WHERE username=%s", (mobile,))
                if cur.fetchone():
                    raise ValueError("An account already exists for this mobile number. Please sign in instead.")
                cur.execute("""INSERT INTO field_farmers
                    (farmer_code, farmer_name, mobile, preferred_language, village, district, state,
                     consent_recorded, consent_recorded_at, created_by, registered_by_role, registered_by_organization)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,1,NOW(),'Farmer self-registration','farmer',NULL)""",
                    (farmer_code, name, mobile, language, village, district, state))
                farmer_id = cur.lastrowid
                cur.execute("""INSERT INTO app_users
                    (username, password_hash, role, display_name, organization_name, farmer_id)
                    VALUES (%s,%s,'farmer',%s,NULL,%s)""",
                    (mobile, generate_password_hash(password), name, farmer_id))
                user_id = cur.lastrowid
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        session.clear()
        session["user_id"] = int(user_id)
        session.permanent = True
        return jsonify({"ok": True, "message": "Your farmer account has been created.", "farmer_code": farmer_code,
                        "user": {"user_id": int(user_id), "username": mobile, "role": "farmer",
                                 "display_name": name, "organization_name": None, "farmer_id": int(farmer_id)}}), 201
    except ValueError as exc:
        return api_error(exc, 422)
    except Exception:
        app.logger.exception("Farmer account creation failed")
        return api_error("Could not create your account. Please check the details or contact the service team.", 503)


@app.post("/api/auth/activate-farmer")
def auth_activate_farmer():
    """Activate a farmer login using a one-time code handed over by the field team."""
    payload = request.get_json(silent=True) or {}
    mobile = re.sub(r"\D", "", str(payload.get("mobile", "")))
    farmer_code = str(payload.get("farmer_code", "")).strip().upper()
    activation_code = str(payload.get("activation_code", "")).strip()
    password = str(payload.get("password", ""))
    if len(mobile) != 10 or not farmer_code or not activation_code:
        return api_error("Enter the registered 10-digit mobile number, farmer code and activation code.", 422)
    if len(password) < 8:
        return api_error("Choose a password with at least 8 characters.", 422)
    try:
        with db.db_cursor() as cur:
            cur.execute("""SELECT u.user_id, u.activation_code_hash, u.activation_expires_at,
                u.must_change_password, u.is_active, u.farmer_id, f.farmer_code
                FROM app_users u JOIN field_farmers f ON f.farmer_id=u.farmer_id
                WHERE u.username=%s AND u.role='farmer' LIMIT 1""", (mobile,))
            row = cur.fetchone()
        if not row or not int(row.get("is_active", 0)) or not int(row.get("must_change_password", 0)):
            return api_error("No pending farmer activation was found for these details.", 404)
        if row.get("farmer_code", "").upper() != farmer_code:
            return api_error("The farmer code does not match this mobile number.", 403)
        expires = row.get("activation_expires_at")
        if not row.get("activation_code_hash") or not expires or expires < datetime.now():
            return api_error("This activation code has expired. Ask your field worker to issue a new one.", 410)
        if not check_password_hash(row["activation_code_hash"], activation_code):
            return api_error("The activation code is incorrect.", 403)
        with db.db_cursor(commit=True) as cur:
            cur.execute("""UPDATE app_users SET password_hash=%s, must_change_password=0,
                activation_code_hash=NULL, activation_expires_at=NULL WHERE user_id=%s""",
                (generate_password_hash(password), row["user_id"]))
        session.clear()
        session["user_id"] = int(row["user_id"])
        session.permanent = True
        return jsonify({"ok": True, "message": "Your farmer account is activated.",
                        "user": {"user_id": int(row["user_id"]), "username": mobile,
                                 "role": "farmer", "display_name": "Farmer", "organization_name": None,
                                 "farmer_id": int(row["farmer_id"])}})
    except Exception:
        app.logger.exception("Farmer account activation failed")
        return api_error("Could not activate this account. Please ask your field worker for help.", 503)


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True, "message": "You have signed out."})


@app.get("/health")
def health():
    try:
        farms = db.get_farms()
        return jsonify({"status": "ok", "database": "connected", "farms": len(farms)})
    except Exception as exc:
        return api_error(f"Database connection failed: {exc}", 503)


@app.get("/api/farms")
def farms():
    try:
        return jsonify({"ok": True, "farms": [clean_row(x) for x in db.get_farms()]})
    except Exception as exc:
        return api_error(exc, 503)


@app.get("/api/overview")
def overview():
    farm_code = request.args.get("farm_code", "")
    try:
        farm = db.get_farm_by_code(farm_code)
        if not farm:
            return api_error("Farm not found.", 404)
        rows = db.get_observations(farm["farm_id"], limit=96)
        if not rows:
            return api_error("No observations have been imported for this farm.", 404)
        latest = rows[-1]
        moisture = float(latest["moisture_pct"])
        threshold = float(farm["moisture_threshold_pct"])
        return jsonify({
            "ok": True,
            "farm": clean_row(farm),
            "latest": clean_row(latest),
            "observation_count": _observation_count(farm["farm_id"]),
            "trend": [clean_row(x) for x in rows],
            "threshold_pct": threshold,
            "threshold_note": farm.get("threshold_note"),
            "current_flag": "AT/BELOW THRESHOLD" if moisture <= threshold else "ABOVE THRESHOLD",
        })
    except Exception as exc:
        return api_error(exc, 503)


def _observation_count(farm_id):
    with db.db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM observations WHERE farm_id=%s", (farm_id,))
        return int(cur.fetchone()["n"])


@app.post("/api/forecast/run")
def run_forecast():
    payload = request.get_json(silent=True) or {}
    farm_code = str(payload.get("farm_code", ""))
    model_name = str(payload.get("model_name", "Persistence"))
    try:
        horizon = int(payload.get("horizon_hours", 1))
        threshold = float(payload.get("threshold_pct", 12.0))
    except (TypeError, ValueError):
        return api_error("Horizon and threshold must be numeric.")
    if horizon not in (1, 6):
        return api_error("Supported forecast horizons are 1 hour and 6 hours.")
    if not (0 <= threshold <= 100):
        return api_error("Threshold must be between 0 and 100 percent.")
    if model_name not in ("Persistence", "Ridge", "Random Forest", "Ridge + sensor context"):
        return api_error("Unknown model selection.")
    try:
        farm = db.get_farm_by_code(farm_code)
        if not farm:
            return api_error("Farm not found.", 404)
        history = db.get_recent_model_rows(farm["farm_id"], limit=1200)
        if len(history) < 289:
            return api_error("At least 289 15-minute observations are required to create the 72-hour lag features.", 422)
        result = predict_options(farm_code, horizon, history)
        selected = next((x for x in result["options"] if x["model_name"] == model_name), None)
        if not selected:
            return api_error("Selected model output was not generated.", 422)
        current = result["current_moisture"]
        predicted = selected["predicted"]
        level, message = create_advisory(current, predicted, threshold)
        forecast_id = db.insert_forecast_and_advisory(
            farm["farm_id"], result["origin_at"], result["target_at"], horizon * 60,
            model_name, selected["feature_set"], predicted, current, threshold, level, message
        )
        return jsonify({
            "ok": True,
            "forecast_id": forecast_id,
            "farm_code": farm_code,
            "horizon_hours": horizon,
            "origin_at": result["origin_at"].isoformat(sep=" "),
            "target_at": result["target_at"].isoformat(sep=" "),
            "current_moisture": current,
            "selected_model": model_name,
            "selected_prediction": predicted,
            "feature_set": selected["feature_set"],
            "all_model_predictions": result["options"],
            "threshold_pct": threshold,
            "advisory_level": level,
            "advisory_text": message,
            "notice": "Prototype decision support only. Thresholds require crop/soil-specific agronomic verification; dataset values are experimental farm observations, not live sensor readings."
        })
    except FileNotFoundError as exc:
        return api_error(exc, 503)
    except ValueError as exc:
        return api_error(exc, 422)
    except Exception as exc:
        app.logger.exception("Forecast generation failed")
        return api_error(exc, 500)


@app.get("/api/forecast/history")
def forecast_history():
    farm_code = request.args.get("farm_code", "")
    try:
        farm = db.get_farm_by_code(farm_code)
        if not farm:
            return api_error("Farm not found.", 404)
        rows = db.get_recent_forecasts(farm["farm_id"], limit=15)
        return jsonify({"ok": True, "forecasts": [clean_row(x) for x in rows]})
    except Exception as exc:
        return api_error(exc, 503)


@app.post("/api/farm/settings")
def update_farm_settings():
    payload = request.get_json(silent=True) or {}
    farm_code = str(payload.get("farm_code", ""))
    crop_name = (payload.get("crop_name") or "").strip() or None
    soil_type = (payload.get("soil_type") or "").strip() or None
    area = payload.get("field_area_sqft")
    try:
        threshold = float(payload.get("threshold_pct", 12.0))
        if area not in (None, ""):
            area_value = virtual_farm.square_feet_to_hectares(area)
        else:
            legacy_area = payload.get("field_area_ha")
            area_value = float(legacy_area) if legacy_area not in (None, "") else None
    except (ValueError, TypeError):
        return api_error("Field area and threshold must be numeric.")
    if not 0 <= threshold <= 100 or (area_value is not None and area_value < 0):
        return api_error("Threshold must be 0–100 and area must be non-negative.")
    try:
        conn = db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("""UPDATE farms SET crop_name=%s, soil_type=%s,
                           field_area_ha=%s, moisture_threshold_pct=%s,
                           threshold_note=%s WHERE farm_code=%s""",
                           (crop_name, soil_type, area_value, threshold,
                            "Prototype threshold; verify for crop/soil before field use", farm_code))
                if cur.rowcount == 0:
                    cur.execute("SELECT farm_id FROM farms WHERE farm_code=%s", (farm_code,))
                    if not cur.fetchone():
                        return api_error("Farm not found.", 404)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return jsonify({"ok": True, "message": "Farm profile updated."})
    except Exception as exc:
        return api_error(exc, 500)


@app.get("/api/region/search")
def region_search():
    query = request.args.get("q", "")
    try:
        results = regional.geocode_location(query)
        return jsonify({"ok": True, "locations": results})
    except ValueError as exc:
        return api_error(exc, 400)
    except requests.RequestException as exc:
        return api_error(f"Location search service is unavailable: {exc}", 502)
    except Exception as exc:
        app.logger.exception("Region geocoding failed")
        return api_error(exc, 502)


@app.post("/api/region/analyze")
def region_analyze():
    payload = request.get_json(silent=True) or {}
    try:
        location = {
            "name": str(payload.get("name", "Selected location")),
            "admin1": payload.get("admin1"), "admin2": payload.get("admin2"),
            "country": payload.get("country", "India"),
            "latitude": float(payload.get("latitude")),
            "longitude": float(payload.get("longitude")),
            "elevation_m": payload.get("elevation_m"),
        }
        result = regional.analyze_region(location)
        return jsonify({"ok": True, "region": result})
    except (TypeError, ValueError) as exc:
        return api_error(exc, 422)
    except requests.RequestException as exc:
        return api_error(f"A climate or forecast data service is unavailable: {exc}", 502)
    except Exception as exc:
        app.logger.exception("Regional intelligence analysis failed")
        return api_error(exc, 502)


@app.post("/api/region/crop-stats/upload")
def region_crop_stats_upload():
    uploaded = request.files.get("crop_stats")
    try:
        summary = regional.save_crop_statistics_csv(uploaded)
        return jsonify({"ok": True, "summary": summary,
                        "message": "District crop statistics imported. Run the regional analysis again to view the local crop pattern."})
    except (ValueError, pd.errors.ParserError) as exc:
        return api_error(exc, 400)
    except Exception as exc:
        app.logger.exception("Crop statistics import failed")
        return api_error(exc, 500)


@app.post("/api/region/crop-stats/demo")
def region_crop_stats_demo():
    """Load a bundled, clearly synthetic crop-history example for presentations."""
    try:
        summary = regional.load_demo_crop_statistics()
        return jsonify({"ok": True, "summary": summary,
                        "message": "Synthetic presentation crop-history loaded. It is not official government data."})
    except Exception as exc:
        app.logger.exception("Synthetic crop dataset load failed")
        return api_error(exc, 500)


@app.get("/api/indian-farming/context")
def indian_farming_context():
    from app.services.indian_agriculture import context_for_location
    state = request.args.get("state", "")
    return jsonify({"ok": True, "context": context_for_location({"admin1": state})})


@app.get("/api/virtual-farms")
def virtual_farms_list():
    try:
        if g.current_user["role"] == "farmer":
            with db.db_cursor() as cur:
                cur.execute("""SELECT vf.* FROM virtual_farms vf JOIN field_farmers ff
                    ON ff.virtual_farm_id=vf.virtual_farm_id WHERE ff.farmer_id=%s
                    ORDER BY vf.updated_at DESC""", (g.current_user["farmer_id"],))
                rows = cur.fetchall()
        elif g.current_user["role"] == "company_officer":
            with db.db_cursor() as cur:
                cur.execute("""SELECT DISTINCT vf.* FROM virtual_farms vf JOIN field_farmers ff
                    ON ff.virtual_farm_id=vf.virtual_farm_id WHERE ff.registered_by_organization=%s
                    ORDER BY vf.updated_at DESC""", (g.current_user.get("organization_name"),))
                rows = cur.fetchall()
        elif g.current_user["role"] == "lab_staff":
            with db.db_cursor() as cur:
                cur.execute("""SELECT DISTINCT vf.* FROM virtual_farms vf
                    JOIN field_farmers ff ON ff.virtual_farm_id=vf.virtual_farm_id
                    JOIN soil_samples s ON s.farmer_id=ff.farmer_id
                    WHERE s.assigned_lab_organization=%s ORDER BY vf.updated_at DESC""",
                    (g.current_user.get("organization_name"),))
                rows = cur.fetchall()
        else:
            rows = virtual_farm.list_virtual_farms()
        return jsonify({"ok": True, "farms": [clean_row(x) for x in rows]})
    except Exception as exc:
        return api_error(exc, 503)


@app.post("/api/virtual-farms")
def virtual_farm_create():
    payload = request.get_json(silent=True) or {}
    try:
        farm_id = virtual_farm.create_virtual_farm(payload)
        if g.current_user["role"] == "farmer":
            with db.db_cursor(commit=True) as cur:
                cur.execute("UPDATE field_farmers SET virtual_farm_id=%s, farm_name=%s WHERE farmer_id=%s",
                            (farm_id, payload.get("farm_name"), g.current_user["farmer_id"]))
        return jsonify({"ok": True, "farm_id": farm_id, "farm": clean_row(virtual_farm.get_virtual_farm(farm_id))}), 201
    except ValueError as exc:
        return api_error(exc, 422)
    except Exception as exc:
        app.logger.exception("Virtual farm creation failed")
        return api_error(exc, 500)


@app.get("/api/virtual-farms/<int:farm_id>")
def virtual_farm_detail(farm_id):
    try:
        if not _farmer_can_access_virtual_farm(farm_id):
            return api_error("This farm is not linked to your farmer account.", 404)
        farm = virtual_farm.get_virtual_farm(farm_id)
        if not farm:
            return api_error("Virtual farm not found.", 404)
        return jsonify({"ok": True, "farm": clean_row(farm)})
    except Exception as exc:
        app.logger.exception("Virtual farm retrieval failed")
        return api_error(exc, 500)


@app.post("/api/virtual-farms/<int:farm_id>/outlook")
def virtual_farm_outlook(farm_id):
    """Build a location-specific outlook from the saved Indian farm coordinates.

    This returns gridded climate/soil context, the 7-day weather forecast,
    district crop-history context and a regional root-zone model when the
    underlying NASA series passes freshness/coverage checks. It never applies
    the Kolkata experimental sensor model to an Indian virtual farm.
    """
    if not _farmer_can_access_virtual_farm(farm_id):
        return api_error("This farm is not linked to your account or organisation.", 404)
    try:
        payload = request.get_json(silent=True) or {}
        farm = virtual_farm.get_virtual_farm(farm_id)
        if not farm:
            return api_error("Virtual farm not found.", 404)
        location = {
            "name": farm.get("village") or farm.get("farm_name") or farm.get("district"),
            "admin1": farm.get("state"),
            "admin2": farm.get("district"),
            "country": farm.get("country") or "India",
            "latitude": float(farm.get("latitude")),
            "longitude": float(farm.get("longitude")),
        }
        result = regional.analyze_region(location)
        selected_season = payload.get("season") or next((p.get("season") for p in farm.get("plots", []) if p.get("season")), None)
        saved_context = farm.get("regional_context") or {}
        saved_location = saved_context.get("regional_location") or {}
        result["crop_pattern_prediction"] = predict_indian_crop_pattern(
            float(farm.get("latitude")), float(farm.get("longitude")),
            selected_season or "", result.get("soil") or {}, saved_location.get("elevation_m")
        )
        verified_sample = None
        with db.db_cursor() as cur:
            cur.execute("""SELECT s.sample_code,s.lab_name,s.tested_at,s.soil_ph,s.soil_ec_ds_m,
                s.organic_carbon_pct,s.available_n_kg_ha,s.available_p_kg_ha,s.available_k_kg_ha,
                s.report_original_filename,s.lab_verified
                FROM field_farmers f JOIN soil_samples s ON s.farmer_id=f.farmer_id
                WHERE f.virtual_farm_id=%s AND s.lab_verified=1
                ORDER BY s.verified_at DESC,s.sample_id DESC LIMIT 1""", (farm_id,))
            verified_sample = cur.fetchone()
        return jsonify({
            "ok": True,
            "farm": clean_row({
                "virtual_farm_id": farm["virtual_farm_id"], "farm_name": farm["farm_name"],
                "village": farm.get("village"), "district": farm["district"], "state": farm["state"],
                "latitude": farm["latitude"], "longitude": farm["longitude"],
                "total_area_sqft": farm.get("total_area_sqft"), "agro_climatic_zone_name": farm.get("agro_climatic_zone_name"),
                "plots": [{"plot_name": p.get("plot_name"), "crop_name": p.get("crop_name"), "season": p.get("season"),
                           "crop_stage": p.get("crop_stage"), "area_sqft": p.get("area_sqft")} for p in farm.get("plots", [])],
            }),
            "verified_soil_sample": clean_row(verified_sample),
            "region": clean_row(result),
            "prediction_scope": "Regional grid point outlook at the saved farm coordinates. This is not a plot-level sensor prediction.",
        })
    except (TypeError, ValueError) as exc:
        return api_error(exc, 422)
    except requests.RequestException as exc:
        app.logger.exception("Farm outlook external data request failed")
        return api_error(f"Could not retrieve current location data. Check internet access and try again: {exc}", 502)
    except Exception as exc:
        app.logger.exception("Farm outlook generation failed")
        return api_error(exc, 500)


@app.post("/api/virtual-farms/<int:farm_id>/boundary")
def virtual_farm_save_boundary(farm_id):
    payload = request.get_json(silent=True) or {}
    try:
        if not _farmer_can_access_virtual_farm(farm_id):
            return api_error("This farm is not linked to your farmer account.", 404)
        virtual_farm.save_farm_boundary(farm_id, payload.get("boundary_geojson"))
        return jsonify({"ok": True, "farm": clean_row(virtual_farm.get_virtual_farm(farm_id))})
    except ValueError as exc:
        return api_error(exc, 422)
    except Exception as exc:
        app.logger.exception("Virtual farm boundary save failed")
        return api_error(exc, 500)


@app.post("/api/virtual-farms/<int:farm_id>/plots")
def virtual_farm_add_plot(farm_id):
    payload = request.get_json(silent=True) or {}
    try:
        if not _farmer_can_access_virtual_farm(farm_id):
            return api_error("This farm is not linked to your farmer account.", 404)
        plot_id = virtual_farm.add_plot(farm_id, payload)
        return jsonify({"ok": True, "plot_id": plot_id, "farm": clean_row(virtual_farm.get_virtual_farm(farm_id))}), 201
    except ValueError as exc:
        return api_error(exc, 422)
    except Exception as exc:
        app.logger.exception("Virtual plot creation failed")
        return api_error(exc, 500)


@app.post("/api/virtual-farms/<int:farm_id>/assets")
def virtual_farm_add_asset(farm_id):
    payload = request.get_json(silent=True) or {}
    try:
        if not _farmer_can_access_virtual_farm(farm_id):
            return api_error("This farm is not linked to your farmer account.", 404)
        asset_id = virtual_farm.add_asset(farm_id, payload)
        return jsonify({"ok": True, "asset_id": asset_id, "farm": clean_row(virtual_farm.get_virtual_farm(farm_id))}), 201
    except ValueError as exc:
        return api_error(exc, 422)
    except Exception as exc:
        app.logger.exception("Virtual farm asset creation failed")
        return api_error(exc, 500)


@app.post("/api/virtual-farms/<int:farm_id>/soil-reports")
def upload_soil_report(farm_id):
    """Store a farmer-provided soil report and its provenance; values are not OCR-extracted."""
    if not _farmer_can_access_virtual_farm(farm_id):
        return api_error("This farm is not linked to your farmer account.", 404)
    farm = virtual_farm.get_virtual_farm(farm_id)
    if not farm:
        return api_error("Virtual farm not found.", 404)
    uploaded = request.files.get("soil_report")
    if not uploaded or not uploaded.filename:
        return api_error("Choose a PDF or image of your Soil Health Card/lab report.")
    original = secure_filename(uploaded.filename)
    extension = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if extension not in ALLOWED_SOIL_REPORT_EXTENSIONS:
        return api_error("Allowed formats: PDF, JPG, PNG or WEBP.")
    report_date = request.form.get("report_date") or None
    source = (request.form.get("report_source") or "Farmer-provided report").strip()[:100]
    notes = (request.form.get("notes") or "").strip()[:1000]
    stored_name = f"farm-{farm_id}-{uuid.uuid4().hex}.{extension}"
    destination = UPLOAD_DIR / stored_name
    uploaded.save(destination)
    try:
        with db.db_cursor(commit=True) as cur:
            cur.execute("""INSERT INTO soil_reports
                (virtual_farm_id, original_filename, stored_filename, mime_type, report_source, report_date, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (farm_id, original[:255], stored_name, uploaded.mimetype or "application/octet-stream", source, report_date, notes))
            report_id = cur.lastrowid
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return jsonify({"ok": True, "report_id": report_id,
                    "message": "Report saved. Please enter measured values from the report into the field soil-test form; this prototype does not automatically read/OCR the document.",
                    "filename": original}), 201


@app.get("/api/virtual-farms/<int:farm_id>/soil-reports")
def list_soil_reports(farm_id):
    if not _farmer_can_access_virtual_farm(farm_id):
        return api_error("This farm is not linked to your farmer account.", 404)
    if not virtual_farm.get_virtual_farm(farm_id):
        return api_error("Virtual farm not found.", 404)
    try:
        with db.db_cursor() as cur:
            cur.execute("""SELECT report_id, original_filename, report_source, report_date, notes, uploaded_at
                           FROM soil_reports WHERE virtual_farm_id=%s ORDER BY uploaded_at DESC""", (farm_id,))
            return jsonify({"ok": True, "reports": [clean_row(x) for x in cur.fetchall()]})
    except Exception as exc:
        return api_error(exc, 500)


# ---------------------------------------------------------------------------
# Assisted village-service workflow (field team -> soil laboratory -> farmer)
# This is a local pilot/demo workflow. It does not claim live government or
# company connectivity; official integrations require partner approval.
# ---------------------------------------------------------------------------

def _service_text(value, label, maximum=160, required=True):
    value = str(value or "").strip()
    if required and not value:
        raise ValueError(f"{label} is required.")
    if len(value) > maximum:
        raise ValueError(f"{label} must be {maximum} characters or fewer.")
    return value or None


def _service_number(value, label, minimum=0, maximum=None, required=False):
    if value in (None, ""):
        if required:
            raise ValueError(f"{label} is required.")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if number < minimum or (maximum is not None and number > maximum):
        bound = f"{minimum} to {maximum}" if maximum is not None else f"at least {minimum}"
        raise ValueError(f"{label} must be {bound}.")
    return number


def _service_datetime(value, default_now=False):
    if not value:
        return datetime.now().replace(microsecond=0) if default_now else None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise ValueError("Date and time must use a valid date/time format.")


@app.get("/api/service/summary")
def service_summary():
    try:
        with db.db_cursor() as cur:
            if g.current_user["role"] == "farmer":
                farmer_id = g.current_user["farmer_id"]
                cur.execute("SELECT COUNT(*) AS n FROM field_farmers WHERE farmer_id=%s", (farmer_id,))
                farmers_count = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE farmer_id=%s AND status NOT IN ('Verified')", (farmer_id,))
                pending_samples = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE farmer_id=%s AND lab_verified=1", (farmer_id,))
                verified_samples = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM field_visits WHERE farmer_id=%s AND visit_status='Scheduled' AND visit_date >= NOW()", (farmer_id,))
                scheduled_visits = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE farmer_id=%s", (farmer_id,))
            elif g.current_user["role"] == "company_officer":
                org = g.current_user.get("organization_name")
                cur.execute("SELECT COUNT(*) AS n FROM field_farmers WHERE registered_by_organization=%s", (org,))
                farmers_count = int(cur.fetchone()["n"])
                cur.execute("""SELECT COUNT(*) AS n FROM soil_samples s JOIN field_farmers f ON f.farmer_id=s.farmer_id
                    WHERE f.registered_by_organization=%s AND s.status NOT IN ('Verified')""", (org,))
                pending_samples = int(cur.fetchone()["n"])
                cur.execute("""SELECT COUNT(*) AS n FROM soil_samples s JOIN field_farmers f ON f.farmer_id=s.farmer_id
                    WHERE f.registered_by_organization=%s AND s.lab_verified=1""", (org,))
                verified_samples = int(cur.fetchone()["n"])
                cur.execute("""SELECT COUNT(*) AS n FROM field_visits v JOIN field_farmers f ON f.farmer_id=v.farmer_id
                    WHERE f.registered_by_organization=%s AND v.visit_status='Scheduled' AND v.visit_date >= NOW()""", (org,))
                scheduled_visits = int(cur.fetchone()["n"])
                cur.execute("""SELECT COUNT(*) AS n FROM soil_samples s JOIN field_farmers f ON f.farmer_id=s.farmer_id
                    WHERE f.registered_by_organization=%s""", (org,))
            elif g.current_user["role"] == "lab_staff":
                org = g.current_user.get("organization_name")
                cur.execute("""SELECT COUNT(DISTINCT f.farmer_id) AS n FROM field_farmers f
                    JOIN soil_samples s ON s.farmer_id=f.farmer_id WHERE s.assigned_lab_organization=%s""", (org,))
                farmers_count = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE assigned_lab_organization=%s AND status NOT IN ('Verified')", (org,))
                pending_samples = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE assigned_lab_organization=%s AND lab_verified=1", (org,))
                verified_samples = int(cur.fetchone()["n"])
                cur.execute("""SELECT COUNT(*) AS n FROM field_visits v JOIN field_farmers f ON f.farmer_id=v.farmer_id
                    JOIN soil_samples s ON s.farmer_id=f.farmer_id WHERE s.assigned_lab_organization=%s
                    AND v.visit_status='Scheduled' AND v.visit_date >= NOW()""", (org,))
                scheduled_visits = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE assigned_lab_organization=%s", (org,))
            else:
                cur.execute("SELECT COUNT(*) AS n FROM field_farmers")
                farmers_count = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE status NOT IN ('Verified')")
                pending_samples = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples WHERE lab_verified=1")
                verified_samples = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM field_visits WHERE visit_status='Scheduled' AND visit_date >= NOW()")
                scheduled_visits = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM soil_samples")
            total_samples = int(cur.fetchone()["n"])
        return jsonify({"ok": True, "summary": {
            "farmers": farmers_count, "pending_samples": pending_samples,
            "verified_samples": verified_samples, "scheduled_visits": scheduled_visits,
            "total_samples": total_samples,
        }})
    except Exception as exc:
        app.logger.exception("Village service summary failed")
        return api_error(exc, 503)


@app.get("/api/service/farmers")
def service_farmers():
    try:
        with db.db_cursor() as cur:
            sql = """SELECT f.farmer_id, f.farmer_code, f.farmer_name, f.mobile,
                f.preferred_language, f.village, f.district, f.state, f.virtual_farm_id,
                f.farm_name, f.farm_area_ha, f.primary_crop, f.created_at,
                (SELECT s.status FROM soil_samples s WHERE s.farmer_id=f.farmer_id
                 ORDER BY s.collected_at DESC LIMIT 1) AS latest_sample_status
                FROM field_farmers f"""
            if g.current_user["role"] == "farmer":
                cur.execute(sql + " WHERE f.farmer_id=%s ORDER BY f.created_at DESC LIMIT 1", (g.current_user["farmer_id"],))
            elif g.current_user["role"] == "company_officer":
                cur.execute(sql + " WHERE f.registered_by_organization=%s ORDER BY f.created_at DESC LIMIT 250",
                            (g.current_user.get("organization_name"),))
            elif g.current_user["role"] == "lab_staff":
                cur.execute(sql + " WHERE EXISTS (SELECT 1 FROM soil_samples s WHERE s.farmer_id=f.farmer_id AND s.assigned_lab_organization=%s) ORDER BY f.created_at DESC LIMIT 250",
                            (g.current_user.get("organization_name"),))
            else:
                cur.execute(sql + " ORDER BY f.created_at DESC LIMIT 250")
            return jsonify({"ok": True, "farmers": [clean_row(x) for x in cur.fetchall()]})
    except Exception as exc:
        return api_error(exc, 503)


@app.post("/api/service/farmers")
def service_create_farmer():
    payload = request.get_json(silent=True) or {}
    try:
        name = _service_text(payload.get("farmer_name"), "Farmer name", 160)
        village = _service_text(payload.get("village"), "Village", 120)
        district = _service_text(payload.get("district"), "District", 120)
        state = _service_text(payload.get("state"), "State", 120)
        mobile = _service_text(payload.get("mobile"), "Mobile number", 20, required=False)
        if mobile:
            digits = re.sub(r"\D", "", mobile)
            if len(digits) == 12 and digits.startswith("91"):
                digits = digits[2:]
            elif len(digits) == 11 and digits.startswith("0"):
                digits = digits[1:]
            if len(digits) != 10:
                raise ValueError("Enter a valid Indian 10-digit mobile number, or leave it blank.")
            mobile = digits
        consent = payload.get("consent_recorded") is True
        if not consent:
            raise ValueError("Please record the farmer's consent before saving their details.")
        if payload.get("farm_area_sqft") not in (None, ""):
            area = virtual_farm.square_feet_to_hectares(payload.get("farm_area_sqft"))
        else:
            # Backward compatibility with older field-team forms.
            area = _service_number(payload.get("farm_area_ha"), "Farm area", 0.0001, 100000, False)
        virtual_farm_id = int(payload["virtual_farm_id"]) if payload.get("virtual_farm_id") else None
        farm_lat = _service_number(payload.get("farm_latitude"), "Farm latitude", 6, 37.5, False)
        farm_lon = _service_number(payload.get("farm_longitude"), "Farm longitude", 68, 98.5, False)
        if (farm_lat is None) != (farm_lon is None):
            raise ValueError("Enter both farm latitude and longitude, or leave both blank.")
        preferred = _service_text(payload.get("preferred_language") or "Hindi", "Preferred language", 30)
        farm_name = _service_text(payload.get("farm_name"), "Farm name", 160, False)
        crop = _service_text(payload.get("primary_crop"), "Main crop", 120, False)
        officer = _service_text(payload.get("officer_name"), "Field officer name", 120)
        visit_date = _service_datetime(payload.get("visit_date"), default_now=True)
        purpose = _service_text(payload.get("visit_purpose") or "Farm registration and soil sampling", "Visit purpose", 120)
        notes = _service_text(payload.get("notes"), "Notes", 1000, False)
        farmer_code = "FARM-" + uuid.uuid4().hex[:10].upper()
        with db.db_cursor() as cur:
            if virtual_farm_id is not None:
                cur.execute("SELECT virtual_farm_id FROM virtual_farms WHERE virtual_farm_id=%s", (virtual_farm_id,))
                if not cur.fetchone():
                    raise ValueError("The selected virtual farm does not exist.")
        with db.db_cursor(commit=True) as cur:
            current_user = g.current_user
            activation_code = None
            account_exists = False
            existing_user = None
            if mobile:
                cur.execute("SELECT user_id, role, farmer_id FROM app_users WHERE username=%s LIMIT 1 FOR UPDATE", (mobile,))
                existing_user = cur.fetchone()
            if existing_user:
                if existing_user.get("role") != "farmer" or not existing_user.get("farmer_id"):
                    raise ValueError("This mobile number is already used by an organisation account. Use a different farmer mobile number.")
                farmer_id = int(existing_user["farmer_id"])
                cur.execute("SELECT farmer_code, registered_by_organization FROM field_farmers WHERE farmer_id=%s LIMIT 1 FOR UPDATE", (farmer_id,))
                existing_farmer = cur.fetchone()
                if not existing_farmer:
                    raise ValueError("The existing farmer login is not linked to a farmer record. Ask the platform administrator to review it.")
                existing_org = existing_farmer.get("registered_by_organization")
                current_org = current_user.get("organization_name")
                if current_user["role"] == "company_officer" and existing_org and existing_org != current_org:
                    raise ValueError("This farmer is already registered under another organisation. Ask the farmer or district coordinator to resolve the record.")
                farmer_code = existing_farmer["farmer_code"]
                account_exists = True
                cur.execute("""UPDATE field_farmers SET farmer_name=%s, mobile=%s, preferred_language=%s,
                    village=%s, district=%s, state=%s,
                    virtual_farm_id=COALESCE(%s,virtual_farm_id),
                    farm_latitude=COALESCE(%s,farm_latitude), farm_longitude=COALESCE(%s,farm_longitude),
                    farm_name=COALESCE(NULLIF(%s,''),farm_name), farm_area_ha=COALESCE(%s,farm_area_ha),
                    primary_crop=COALESCE(NULLIF(%s,''),primary_crop),
                    registered_by_role=CASE WHEN registered_by_organization IS NULL AND %s IS NOT NULL THEN %s ELSE registered_by_role END,
                    registered_by_organization=COALESCE(registered_by_organization,%s)
                    WHERE farmer_id=%s""",
                    (name, mobile, preferred, village, district, state, virtual_farm_id, farm_lat, farm_lon,
                     farm_name, area, crop, current_org, current_user["role"], current_org, farmer_id))
            else:
                cur.execute("""INSERT INTO field_farmers
                    (farmer_code, farmer_name, mobile, preferred_language, village, district,
                     state, virtual_farm_id, farm_latitude, farm_longitude, farm_name, farm_area_ha, primary_crop,
                     consent_recorded, consent_recorded_at, created_by, registered_by_role, registered_by_organization)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,NOW(),%s,%s,%s)""",
                    (farmer_code, name, mobile, preferred, village, district, state,
                     virtual_farm_id, farm_lat, farm_lon, farm_name, area, crop, officer,
                     current_user["role"], current_user.get("organization_name")))
                farmer_id = cur.lastrowid
                if mobile:
                    activation_code = f"{secrets.randbelow(100000000):08d}"
                    cur.execute("""INSERT INTO app_users
                        (username,password_hash,role,display_name,organization_name,farmer_id,
                         must_change_password,activation_code_hash,activation_expires_at)
                        VALUES (%s,%s,'farmer',NULLIF(%s,''),NULL,%s,1,%s,%s)""",
                        (mobile, generate_password_hash(secrets.token_urlsafe(32)), name, farmer_id,
                         generate_password_hash(activation_code), datetime.now() + timedelta(days=7)))
            cur.execute("""INSERT INTO field_visits
                (farmer_id, officer_name, visit_date, visit_purpose, visit_status, notes, officer_role, organization_name)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (farmer_id, officer, visit_date, purpose,
                 "Completed" if visit_date <= datetime.now() else "Scheduled", notes,
                 current_user["role"], current_user.get("organization_name")))
        return jsonify({"ok": True, "farmer_id": farmer_id, "farmer_code": farmer_code,
                        "activation_code": activation_code, "farmer_account_exists": account_exists,
                        "activation_expires_in_days": 7 if activation_code else None,
                        "message": "Farmer registered and field visit recorded. " +
                                   ("A one-time farmer activation code has been created; hand it directly to the farmer." if activation_code else
                                    ("A farmer login already exists for this mobile number." if account_exists else "No login was created because no mobile number was provided."))}), 201
    except ValueError as exc:
        return api_error(exc, 422)
    except Exception as exc:
        app.logger.exception("Farmer registration failed")
        return api_error(exc, 500)


@app.get("/api/service/farmers/<int:farmer_id>")
def service_farmer_detail(farmer_id):
    try:
        if not _farmer_owns_record(farmer_id):
            return api_error("This farmer record is not linked to your account.", 404)
        if g.current_user["role"] == "company_officer":
            with db.db_cursor() as access_cur:
                access_cur.execute("SELECT 1 FROM field_farmers WHERE farmer_id=%s AND registered_by_organization=%s",
                                    (farmer_id, g.current_user.get("organization_name")))
                if not access_cur.fetchone():
                    return api_error("This farmer record is outside your organisation workspace.", 404)
        if g.current_user["role"] == "lab_staff":
            with db.db_cursor() as access_cur:
                access_cur.execute("SELECT 1 FROM soil_samples WHERE farmer_id=%s AND assigned_lab_organization=%s LIMIT 1",
                                    (farmer_id, g.current_user.get("organization_name")))
                if not access_cur.fetchone():
                    return api_error("This farmer has no sample assigned to your laboratory.", 404)
        with db.db_cursor() as cur:
            cur.execute("SELECT * FROM field_farmers WHERE farmer_id=%s", (farmer_id,))
            farmer = cur.fetchone()
            if not farmer:
                return api_error("Farmer record not found.", 404)
            cur.execute("""SELECT * FROM soil_samples WHERE farmer_id=%s
                ORDER BY collected_at DESC, sample_id DESC LIMIT 1""", (farmer_id,))
            sample = cur.fetchone()
            cur.execute("""SELECT officer_name, visit_date, visit_purpose, visit_status, notes
                FROM field_visits WHERE farmer_id=%s ORDER BY visit_date DESC LIMIT 10""", (farmer_id,))
            visits = cur.fetchall()
        return jsonify({"ok": True, "farmer": clean_row(farmer),
                        "latest_sample": clean_row(sample) if sample else None,
                        "visits": [clean_row(x) for x in visits]})
    except Exception as exc:
        app.logger.exception("Farmer card retrieval failed")
        return api_error(exc, 500)


@app.get("/api/service/samples")
def service_samples():
    status_filter = request.args.get("status", "").strip()
    try:
        with db.db_cursor() as cur:
            sql = """SELECT s.*, f.farmer_name, f.farmer_code, f.village, f.district, f.state
                FROM soil_samples s JOIN field_farmers f ON f.farmer_id=s.farmer_id"""
            conditions, params = [], []
            if status_filter:
                conditions.append("s.status=%s"); params.append(status_filter)
            if g.current_user["role"] == "farmer":
                conditions.append("s.farmer_id=%s"); params.append(g.current_user["farmer_id"])
            elif g.current_user["role"] == "company_officer":
                conditions.append("f.registered_by_organization=%s"); params.append(g.current_user.get("organization_name"))
            elif g.current_user["role"] == "lab_staff":
                conditions.append("s.assigned_lab_organization=%s"); params.append(g.current_user.get("organization_name"))
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY s.collected_at DESC LIMIT 300"
            cur.execute(sql, tuple(params))
            return jsonify({"ok": True, "samples": [clean_row(x) for x in cur.fetchall()]})
    except Exception as exc:
        return api_error(exc, 503)


@app.post("/api/service/samples")
def service_create_sample():
    payload = request.get_json(silent=True) or {}
    try:
        farmer_id = int(payload.get("farmer_id"))
        collected_by = _service_text(payload.get("collected_by"), "Collected by", 120)
        description = _service_text(payload.get("sample_description"), "Sample location or plot", 255, False)
        assigned_lab = _service_text(payload.get("assigned_lab_organization"), "Destination soil laboratory", 180)
        collected_at = _service_datetime(payload.get("collected_at"), default_now=True)
        latitude = _service_number(payload.get("latitude"), "Latitude", 6, 37.5, False)
        longitude = _service_number(payload.get("longitude"), "Longitude", 68, 98.5, False)
        if (latitude is None) != (longitude is None):
            raise ValueError("Enter both latitude and longitude, or leave both blank.")
        with db.db_cursor() as cur:
            cur.execute("SELECT farmer_id FROM field_farmers WHERE farmer_id=%s", (farmer_id,))
            farmer_record = cur.fetchone()
            if not farmer_record:
                raise ValueError("Choose a registered farmer.")
            if g.current_user["role"] == "company_officer":
                cur.execute("SELECT 1 FROM field_farmers WHERE farmer_id=%s AND registered_by_organization=%s",
                            (farmer_id, g.current_user.get("organization_name")))
                if not cur.fetchone():
                    raise ValueError("This farmer is not assigned to your organisation workspace.")
        sample_code = "SOIL-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
        with db.db_cursor(commit=True) as cur:
            current_user = g.current_user
            cur.execute("""INSERT INTO soil_samples
                (sample_code, farmer_id, sample_description, collected_by, collected_at, latitude, longitude,
                 collection_role, collection_organization, assigned_lab_organization)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (sample_code, farmer_id, description, collected_by, collected_at, latitude, longitude,
                 current_user["role"], current_user.get("organization_name"), assigned_lab))
            sample_id = cur.lastrowid
        return jsonify({"ok": True, "sample_id": sample_id, "sample_code": sample_code,
                        "message": "Sample registered. Write this code on the sample bag and hand it to the laboratory."}), 201
    except (TypeError, ValueError) as exc:
        return api_error(exc, 422)
    except Exception as exc:
        app.logger.exception("Soil sample registration failed")
        return api_error(exc, 500)


@app.get("/api/service/samples/<int:sample_id>/report")
def service_sample_report(sample_id):
    """Serve the report attached to a sample. Local prototype only; production needs auth."""
    try:
        with db.db_cursor() as cur:
            if g.current_user["role"] == "farmer":
                cur.execute("SELECT report_stored_filename, report_original_filename FROM soil_samples WHERE sample_id=%s AND farmer_id=%s", (sample_id, g.current_user["farmer_id"]))
            elif g.current_user["role"] == "company_officer":
                cur.execute("""SELECT s.report_stored_filename, s.report_original_filename FROM soil_samples s
                    JOIN field_farmers f ON f.farmer_id=s.farmer_id
                    WHERE s.sample_id=%s AND f.registered_by_organization=%s""",
                    (sample_id, g.current_user.get("organization_name")))
            elif g.current_user["role"] == "lab_staff":
                cur.execute("SELECT report_stored_filename, report_original_filename FROM soil_samples WHERE sample_id=%s AND assigned_lab_organization=%s", (sample_id, g.current_user.get("organization_name")))
            else:
                cur.execute("SELECT report_stored_filename, report_original_filename FROM soil_samples WHERE sample_id=%s", (sample_id,))
            sample = cur.fetchone()
        if not sample or not sample.get("report_stored_filename"):
            return api_error("No laboratory report is attached to this sample.", 404)
        stored = Path(sample["report_stored_filename"]).name
        path = UPLOAD_DIR / stored
        if not path.is_file():
            return api_error("The saved report file is not available on this server.", 404)
        return send_from_directory(str(UPLOAD_DIR), stored, as_attachment=False,
                                   download_name=sample.get("report_original_filename") or stored)
    except Exception as exc:
        app.logger.exception("Lab report retrieval failed")
        return api_error(exc, 500)


@app.post("/api/service/samples/<int:sample_id>/results")
def service_save_sample_results(sample_id):
    form = request.form
    report = request.files.get("lab_report")
    stored_name = original_name = mime_type = None
    destination = None
    try:
        lab_name = _service_text(form.get("lab_name"), "Laboratory name", 180)
        if g.current_user["role"] == "lab_staff" and lab_name.casefold() != str(g.current_user.get("organization_name") or "").casefold():
            raise ValueError("The laboratory name must match the organisation assigned to your login.")
        tested_by = _service_text(form.get("tested_by"), "Technician name", 120)
        ph = _service_number(form.get("soil_ph"), "pH", 0, 14, False)
        ec = _service_number(form.get("soil_ec_ds_m"), "EC", 0, 1000, False)
        oc = _service_number(form.get("organic_carbon_pct"), "Organic carbon", 0, 100, False)
        n = _service_number(form.get("available_n_kg_ha"), "Available nitrogen", 0, 100000, False)
        p_value = _service_number(form.get("available_p_kg_ha"), "Available phosphorus", 0, 100000, False)
        k = _service_number(form.get("available_k_kg_ha"), "Available potassium", 0, 100000, False)
        if all(value is None for value in (ph, ec, oc, n, p_value, k)):
            raise ValueError("Enter at least one measured laboratory value.")
        verified = form.get("lab_verified") == "yes"
        verified_by = tested_by if verified else None
        tested_at = _service_datetime(form.get("tested_at"), default_now=True)
        notes = _service_text(form.get("lab_notes"), "Laboratory notes", 1500, False)
        if report and report.filename:
            original_name = secure_filename(report.filename)
            extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if extension not in ALLOWED_SOIL_REPORT_EXTENSIONS:
                raise ValueError("Lab report must be PDF, JPG, PNG or WEBP.")
            stored_name = f"sample-{sample_id}-{uuid.uuid4().hex}.{extension}"
            mime_type = report.mimetype or "application/octet-stream"
            destination = UPLOAD_DIR / stored_name
            report.save(destination)
        with db.db_cursor(commit=True) as cur:
            if g.current_user["role"] == "lab_staff":
                cur.execute("SELECT sample_id FROM soil_samples WHERE sample_id=%s AND assigned_lab_organization=%s", (sample_id, g.current_user.get("organization_name")))
            else:
                cur.execute("SELECT sample_id FROM soil_samples WHERE sample_id=%s", (sample_id,))
            if not cur.fetchone():
                raise ValueError("Soil sample was not found in your laboratory's assigned queue.")
            cur.execute("""UPDATE soil_samples SET lab_name=%s, tested_by=%s, tested_at=%s,
                lab_role=%s, lab_organization=%s,
                soil_ph=%s, soil_ec_ds_m=%s, organic_carbon_pct=%s,
                available_n_kg_ha=%s, available_p_kg_ha=%s, available_k_kg_ha=%s,
                lab_verified=%s, verified_by=%s, verified_at=%s,
                status=%s, report_original_filename=%s, report_stored_filename=%s,
                report_mime_type=%s, lab_notes=%s WHERE sample_id=%s""",
                (lab_name, tested_by, tested_at, g.current_user["role"], g.current_user.get("organization_name"),
                 ph, ec, oc, n, p_value, k, int(verified), verified_by, tested_at if verified else None,
                 "Verified" if verified else "Tested - pending verification",
                 original_name, stored_name, mime_type, notes, sample_id))
        return jsonify({"ok": True, "message": "Laboratory results saved and marked " + ("verified." if verified else "pending verification."),
                        "lab_verified": verified}), 200
    except ValueError as exc:
        if destination:
            destination.unlink(missing_ok=True)
        return api_error(exc, 422)
    except Exception as exc:
        if destination:
            destination.unlink(missing_ok=True)
        app.logger.exception("Laboratory result submission failed")
        return api_error(exc, 500)


if __name__ == "__main__":
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
