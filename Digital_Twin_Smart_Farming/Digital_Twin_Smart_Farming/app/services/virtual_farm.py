"""Persistence and validation for user-defined Indian virtual farm structures."""
from __future__ import annotations

import json
import math
import re
from datetime import date
from app import db

INDIA_BOUNDS = {"lat_min": 6.0, "lat_max": 37.5, "lon_min": 68.0, "lon_max": 98.5}
SQFT_PER_HECTARE = 107639.104167
SQFT_PER_SQM = 10.7639104167

def square_feet_to_hectares(value) -> float:
    number = _nullable_float(value, "Area in square feet", 10, 1000000000)
    if number is None:
        raise ValueError("Farm/plot area in square feet is required.")
    return number / SQFT_PER_HECTARE

def hectares_to_square_feet(value) -> float:
    return float(value or 0) * SQFT_PER_HECTARE
ASSET_TYPES = ["Borewell / Tube well", "Open well", "Farm pond", "Water tank", "Canal / Field channel", "Pump house", "Farm building", "Cattle shed", "Storage / Granary", "Solar pump", "Drainage channel", "Other"]


def _json_dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value is not None else None


def _safe_india_point(lat, lon):
    lat, lon = float(lat), float(lon)
    if not (INDIA_BOUNDS["lat_min"] <= lat <= INDIA_BOUNDS["lat_max"] and INDIA_BOUNDS["lon_min"] <= lon <= INDIA_BOUNDS["lon_max"]):
        raise ValueError("The point must be within India's approximate geographic bounds.")
    return lat, lon


def _validate_polygon_feature(feature, farm_lat, farm_lon):
    if feature in (None, ""):
        return None
    if isinstance(feature, str):
        feature = json.loads(feature)
    if not isinstance(feature, dict):
        raise ValueError("Plot boundary must be a GeoJSON Feature.")
    geometry = feature.get("geometry") if feature.get("type") == "Feature" else feature
    if not geometry or geometry.get("type") != "Polygon":
        raise ValueError("Each plot boundary must be a GeoJSON Polygon.")
    rings = geometry.get("coordinates") or []
    if not rings or len(rings[0]) < 4:
        raise ValueError("Plot boundary needs at least four coordinate pairs including closure.")
    points=[]
    for pair in rings[0]:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            raise ValueError("Invalid GeoJSON coordinate pair.")
        lat, lon = _safe_india_point(pair[1], pair[0])
        points.append((lon, lat))
    if points[0] != points[-1]:
        raise ValueError("Plot polygon ring must be closed (first and last coordinates must match).")
    if len(points) > 5000:
        raise ValueError("Plot boundary has too many vertices; simplify the shape.")
    # Prevent an obviously unrelated plot being attached to the selected location.
    if min(abs(p[0]-farm_lon) for p in points) > 1.0 or min(abs(p[1]-farm_lat) for p in points) > 1.0:
        raise ValueError("Draw the plot near the selected farm location, or re-check the selected place.")
    return _json_dumps(feature)



def _point_in_polygon(longitude: float, latitude: float, feature: dict) -> bool:
    """Ray-casting test for a GeoJSON Polygon outer ring, including edge points."""
    geometry = feature.get("geometry") if feature.get("type") == "Feature" else feature
    rings = (geometry or {}).get("coordinates") or []
    if not rings or len(rings[0]) < 4:
        return False
    ring = rings[0]
    inside = False
    eps = 1e-9
    for i in range(len(ring) - 1):
        x1, y1 = float(ring[i][0]), float(ring[i][1])
        x2, y2 = float(ring[i + 1][0]), float(ring[i + 1][1])
        cross = (longitude - x1) * (y2 - y1) - (latitude - y1) * (x2 - x1)
        if abs(cross) <= eps and min(x1, x2) - eps <= longitude <= max(x1, x2) + eps and min(y1, y2) - eps <= latitude <= max(y1, y2) + eps:
            return True
        if (y1 > latitude) != (y2 > latitude):
            intersection_x = x1 + (latitude - y1) * (x2 - x1) / (y2 - y1)
            if longitude < intersection_x:
                inside = not inside
    return inside


def _ensure_inside_farm(feature: str | dict, farm_boundary: dict, item_label: str) -> None:
    if not farm_boundary:
        raise ValueError("Draw and save the outer farm boundary before adding plots or infrastructure.")
    if isinstance(feature, str):
        feature = json.loads(feature)
    geometry = feature.get("geometry") if feature.get("type") == "Feature" else feature
    if geometry and geometry.get("type") == "Point":
        coordinates = geometry.get("coordinates") or []
        candidates = [coordinates] if len(coordinates) >= 2 else []
    else:
        coordinates = (geometry or {}).get("coordinates") or []
        ring = coordinates[0] if coordinates else []
        candidates = ring[:-1]
    for pair in candidates:
        if not _point_in_polygon(float(pair[0]), float(pair[1]), farm_boundary):
            raise ValueError(f"The {item_label} must lie inside the saved outer farm boundary.")

def _nullable_float(value, label, minimum=None, maximum=None):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric.")
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number.")
    if minimum is not None and number < minimum or maximum is not None and number > maximum:
        raise ValueError(f"{label} is outside its allowed range.")
    return number


def create_virtual_farm(payload: dict) -> int:
    loc = payload.get("location") or {}
    state = str(loc.get("admin1") or payload.get("state") or "").strip()
    district = str(loc.get("admin2") or payload.get("district") or "").strip()
    name = str(payload.get("farm_name") or "").strip()
    if not name or len(name) > 160:
        raise ValueError("Enter a farm name (maximum 160 characters).")
    if not state or not district:
        raise ValueError("State and district are required to create an Indian virtual farm.")
    lat, lon = _safe_india_point(loc.get("latitude"), loc.get("longitude"))
    if payload.get("total_area_sqft") not in (None, ""):
        area = square_feet_to_hectares(payload.get("total_area_sqft"))
    else:
        # Backward compatibility for older clients that still send hectares.
        area = _nullable_float(payload.get("total_area_ha"), "Total farm area", 0.0001, 10000000)
    if area is None:
        raise ValueError("Enter the total farm area in square feet.")
    zone_id = str(payload.get("agro_climatic_zone_id") or "").strip() or None
    zone_name = str(payload.get("agro_climatic_zone_name") or "").strip() or None
    if zone_id and zone_id not in {"I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV"}:
        raise ValueError("Select one of the 15 Planning Commission agro-climatic regions.")
    climate = payload.get("climate_profile") or {}
    soil = payload.get("soil_profile") or {}
    context = dict(payload.get("indian_context") or {})
    context["regional_crop_pattern"] = payload.get("crop_pattern") or {}
    context["weather_forecast_snapshot"] = payload.get("weather_forecast") or {}
    context["regional_location"] = {"name": loc.get("name"), "latitude": lat, "longitude": lon, "elevation_m": loc.get("elevation_m")}
    provenance = {
        "location": "Open-Meteo geocoding result selected by user",
        "climate": climate.get("source", "Not captured"),
        "soil": soil.get("source", "Not captured"),
        "agro_climatic_zone": "User selected from India 15-region framework; verify at district/sub-district level",
        "crop_context": "Not inferred automatically; plot crop and season entered per plot or populated from uploaded district statistics"
    }
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO virtual_farms
            (farm_name,village,district,state,country,latitude,longitude,total_area_ha,
             agro_climatic_zone_id,agro_climatic_zone_name,farming_system,land_form,
             water_source,primary_irrigation_method,climate_profile_json,soil_profile_json,
             regional_context_json,data_provenance_json)
            VALUES (%s,%s,%s,%s,'India',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (name, (payload.get("village") or "").strip() or None, district, state, lat, lon, area,
             zone_id, zone_name, payload.get("farming_system") or None, payload.get("land_form") or None,
             payload.get("water_source") or None, payload.get("primary_irrigation_method") or None,
             _json_dumps(climate), _json_dumps(soil), _json_dumps(context), _json_dumps(provenance)))
        return int(cur.lastrowid)



def save_farm_boundary(farm_id: int, feature) -> None:
    farm = get_virtual_farm(farm_id)
    if not farm:
        raise ValueError("Virtual farm not found.")
    boundary = _validate_polygon_feature(feature, float(farm["latitude"]), float(farm["longitude"]))
    if not boundary:
        raise ValueError("Draw an outer farm boundary before saving it.")
    if not _point_in_polygon(float(farm["longitude"]), float(farm["latitude"]), json.loads(boundary)):
        raise ValueError("The selected farm reference point must lie inside the outer farm boundary.")
    with db.db_cursor(commit=True) as cur:
        cur.execute("UPDATE virtual_farms SET boundary_geojson=%s WHERE virtual_farm_id=%s", (boundary, farm_id))


def add_plot(farm_id: int, payload: dict) -> int:
    farm = get_virtual_farm(farm_id)
    if not farm:
        raise ValueError("Virtual farm not found.")
    name = str(payload.get("plot_name") or "").strip()
    if not name or len(name) > 120:
        raise ValueError("Enter a plot name (maximum 120 characters).")
    if payload.get("area_sqft") not in (None, ""):
        area = square_feet_to_hectares(payload.get("area_sqft"))
    else:
        # Backward compatibility for existing plot forms.
        area = _nullable_float(payload.get("area_ha"), "Plot area", 0.0001, 1000000)
    if area is None:
        raise ValueError("Enter the plot area in square feet.")
    existing_area = sum(float(x.get("area_ha") or 0) for x in farm["plots"])
    if existing_area + area > float(farm["total_area_ha"]) * 1.02:
        raise ValueError(f"Plot areas exceed the farm's registered area ({hectares_to_square_feet(farm['total_area_ha']):,.0f} sq ft). Existing plots total {hectares_to_square_feet(existing_area):,.0f} sq ft.")
    boundary = _validate_polygon_feature(payload.get("boundary_geojson"), float(farm["latitude"]), float(farm["longitude"]))
    if not boundary:
        raise ValueError("Draw the plot boundary on the map before saving the plot.")
    _ensure_inside_farm(boundary, farm.get("boundary"), "plot boundary")
    ph = _nullable_float(payload.get("soil_ph"), "Soil pH", 0, 14)
    ec = _nullable_float(payload.get("soil_ec_ds_m"), "Soil EC", 0, 1000)
    oc = _nullable_float(payload.get("organic_carbon_pct"), "Organic carbon", 0, 100)
    nitrogen = _nullable_float(payload.get("available_n_kg_ha"), "Available nitrogen", 0, 100000)
    phosphorus = _nullable_float(payload.get("available_p_kg_ha"), "Available phosphorus", 0, 100000)
    potassium = _nullable_float(payload.get("available_k_kg_ha"), "Available potassium", 0, 100000)
    code = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")[:36] or "PLOT"
    code = f"{code}-{len(farm['plots'])+1:02d}"
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO virtual_farm_plots
            (virtual_farm_id,plot_code,plot_name,area_ha,crop_name,crop_variety,season,sowing_date,
             crop_stage,indian_soil_group,soil_texture,soil_ph,soil_ec_ds_m,organic_carbon_pct,
             available_n_kg_ha,available_p_kg_ha,available_k_kg_ha,soil_test_source,soil_test_date,
             irrigation_method,water_source,boundary_geojson,notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (farm_id,code,name,area,(payload.get("crop_name") or "").strip() or None,
             (payload.get("crop_variety") or "").strip() or None,payload.get("season") or None,
             payload.get("sowing_date") or None,payload.get("crop_stage") or None,
             payload.get("indian_soil_group") or None,(payload.get("soil_texture") or "").strip() or None,
             ph,ec,oc,nitrogen,phosphorus,potassium,payload.get("soil_test_source") or None,
             payload.get("soil_test_date") or None,payload.get("irrigation_method") or None,
             payload.get("water_source") or None,boundary,(payload.get("notes") or "").strip() or None))
        return int(cur.lastrowid)


def add_asset(farm_id: int, payload: dict) -> int:
    farm = get_virtual_farm(farm_id)
    if not farm:
        raise ValueError("Virtual farm not found.")
    asset_type = str(payload.get("asset_type") or "").strip()
    if asset_type not in ASSET_TYPES:
        raise ValueError("Choose a valid farm infrastructure asset type.")
    name = str(payload.get("asset_name") or "").strip()
    if not name:
        raise ValueError("Enter an asset name.")
    lat, lon = _safe_india_point(payload.get("latitude"), payload.get("longitude"))
    if abs(lat-float(farm["latitude"])) > 1 or abs(lon-float(farm["longitude"])) > 1:
        raise ValueError("Place the infrastructure asset close to the selected farm location.")
    _ensure_inside_farm({"type": "Point", "coordinates": [lon, lat]}, farm.get("boundary"), "infrastructure asset")
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO virtual_farm_assets
            (virtual_farm_id,asset_type,asset_name,latitude,longitude,capacity_or_size,notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (farm_id,asset_type,name,lat,lon,(payload.get("capacity_or_size") or "").strip() or None,(payload.get("notes") or "").strip() or None))
        return int(cur.lastrowid)


def _parse_json(value):
    if not value:
        return None
    try: return json.loads(value)
    except (TypeError, ValueError): return None


def get_virtual_farm(farm_id: int) -> dict | None:
    with db.db_cursor() as cur:
        cur.execute("SELECT * FROM virtual_farms WHERE virtual_farm_id=%s", (farm_id,))
        farm = cur.fetchone()
        if not farm: return None
        cur.execute("SELECT * FROM virtual_farm_plots WHERE virtual_farm_id=%s ORDER BY plot_id", (farm_id,))
        plots = cur.fetchall()
        cur.execute("SELECT * FROM virtual_farm_assets WHERE virtual_farm_id=%s ORDER BY asset_id", (farm_id,))
        assets = cur.fetchall()
    farm = dict(farm)
    for key in ["climate_profile_json","soil_profile_json","regional_context_json","data_provenance_json","boundary_geojson"]:
        if key in farm:
            decoded = _parse_json(farm.pop(key))
            farm[key.replace("_json", "")] = decoded
    farm["plots"] = []
    for plot in plots:
        item=dict(plot); item["boundary"]=_parse_json(item.pop("boundary_geojson",None)); farm["plots"].append(item)
    farm["assets"] = [dict(x) for x in assets]
    farm["mapped_plot_area_ha"] = round(sum(float(x["area_ha"]) for x in farm["plots"]),4)
    farm["unmapped_area_ha"] = round(max(0,float(farm["total_area_ha"])-farm["mapped_plot_area_ha"]),4)
    farm["total_area_sqft"] = round(hectares_to_square_feet(farm["total_area_ha"]))
    farm["mapped_plot_area_sqft"] = round(hectares_to_square_feet(farm["mapped_plot_area_ha"]))
    farm["unmapped_area_sqft"] = round(hectares_to_square_feet(farm["unmapped_area_ha"]))
    for plot in farm["plots"]:
        plot["area_sqft"] = round(hectares_to_square_feet(plot.get("area_ha")))
    return farm


def list_virtual_farms() -> list[dict]:
    with db.db_cursor() as cur:
        cur.execute("""SELECT virtual_farm_id,farm_name,village,district,state,total_area_ha,
                    agro_climatic_zone_id,agro_climatic_zone_name,created_at
                    FROM virtual_farms ORDER BY updated_at DESC""")
        rows = cur.fetchall()
    for row in rows:
        row["total_area_sqft"] = round(hectares_to_square_feet(row.get("total_area_ha")))
    return rows
