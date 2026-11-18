"""Insert clearly labelled synthetic Indian demo data for presentations.
Run inside the web container:
  docker compose exec web python scripts/seed_demo_data.py
Safe to rerun: stable demo names/codes prevent duplicate records.
All coordinates, people, readings and crop facts are synthetic; never use for farm decisions.
"""
from pathlib import Path
from datetime import datetime, timedelta
import sys
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import db
NAME = "DEMO ONLY - Sehore Learning Farm"
FARMER_CODE = "DEMO-FARMER-SEHORE"
VERIFIED_SAMPLE_CODE = "DEMO-SOIL-VERIFIED-001"
PENDING_SAMPLE_CODE = "DEMO-SOIL-PENDING-001"
lat, lon = 23.2031, 77.0844  # illustrative point only; not a real farmer's plot
farm_ring = [[lon-0.0018,lat-0.0012],[lon+0.0018,lat-0.0012],[lon+0.0018,lat+0.0012],[lon-0.0018,lat+0.0012],[lon-0.0018,lat-0.0012]]
plot_ring = [[lon-0.0014,lat-0.0009],[lon+0.0001,lat-0.0009],[lon+0.0001,lat+0.0009],[lon-0.0014,lat+0.0009],[lon-0.0014,lat-0.0009]]
polygon = lambda ring: json.dumps({"type":"Feature","properties":{"demo":True},"geometry":{"type":"Polygon","coordinates":[ring]}})

with db.db_cursor() as cur:
    cur.execute("SELECT virtual_farm_id FROM virtual_farms WHERE farm_name=%s", (NAME,))
    found = cur.fetchone()
if found:
    farm_id = found["virtual_farm_id"]
    print(f"Demo virtual farm already exists (ID {farm_id}).")
else:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO virtual_farms
          (farm_name,village,district,state,country,latitude,longitude,total_area_ha,
           agro_climatic_zone_id,agro_climatic_zone_name,farming_system,land_form,
           water_source,primary_irrigation_method,boundary_geojson,climate_profile_json,
           soil_profile_json,regional_context_json,data_provenance_json)
          VALUES (%s,%s,%s,%s,'India',%s,%s,2.0,'X','Western Plateau and Hills','Mixed crop','Plain',
           'Borewell','Drip',%s,%s,%s,%s,%s)""",
          (NAME,'Demo village','Sehore','Madhya Pradesh',lat,lon,polygon(farm_ring),
           json.dumps({'source':'Synthetic demo values','mean_air_temperature_c':27.4,'mean_annual_rainfall_mm':1120}),
           json.dumps({'source':'Synthetic example only; not measured','texture_group_screening':'Black soil (illustrative)'}),
           json.dumps({'demo':True,'note':'Synthetic demonstration profile; not actual Sehore farm data'}),
           json.dumps({'farm_profile':'Synthetic demo','soil_values':'Illustrative only','weather':'Illustrative only'})))
        farm_id = cur.lastrowid
    print(f"Created synthetic virtual farm ID {farm_id}.")

with db.db_cursor() as cur:
    cur.execute("SELECT COUNT(*) AS n FROM virtual_farm_plots WHERE virtual_farm_id=%s", (farm_id,))
    plots = int(cur.fetchone()["n"])
if not plots:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO virtual_farm_plots
          (virtual_farm_id,plot_code,plot_name,area_ha,crop_name,crop_variety,season,crop_stage,
           indian_soil_group,soil_texture,soil_ph,soil_ec_ds_m,organic_carbon_pct,
           available_n_kg_ha,available_p_kg_ha,available_k_kg_ha,soil_test_source,soil_test_date,
           irrigation_method,water_source,boundary_geojson,notes)
          VALUES (%s,'DEMO-PLOT-01','Demo Soybean Field',1.2,'Soybean','Illustrative variety','Kharif',
           'Vegetative growth','Black / Regur','Clay loam',7.2,0.35,0.62,245,18,310,
           'Synthetic demo values - NOT a real lab report','2026-06-10','Drip','Borewell',%s,
           'Presentation-only synthetic values. Replace with farmer-entered and laboratory-verified data.')""",
          (farm_id,polygon(plot_ring)))
        cur.execute("""INSERT INTO virtual_farm_assets
          (virtual_farm_id,asset_type,asset_name,latitude,longitude,capacity_or_size,notes)
          VALUES (%s,'Farm pond','Demo farm pond',%s,%s,'Illustrative 30,000 L','Synthetic demo asset')""",
          (farm_id,lat+0.0004,lon+0.0008))

with db.db_cursor() as cur:
    cur.execute("SELECT farmer_id FROM field_farmers WHERE farmer_code=%s", (FARMER_CODE,))
    found_farmer = cur.fetchone()
if found_farmer:
    farmer_id = found_farmer["farmer_id"]
    # This is a reserved synthetic record; repair provenance if it was created by
    # an earlier demo-seed version before organisation scoping was added.
    with db.db_cursor(commit=True) as cur:
        cur.execute("""UPDATE field_farmers SET virtual_farm_id=%s,
            registered_by_role='company_officer',
            registered_by_organization='Demo Fertiliser Field Partner'
            WHERE farmer_code=%s""", (farm_id, FARMER_CODE))
    print(f"Demo farmer already exists (ID {farmer_id}); demo organisation link checked.")
else:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO field_farmers
          (farmer_code,farmer_name,mobile,preferred_language,village,district,state,
           virtual_farm_id,farm_latitude,farm_longitude,farm_name,farm_area_ha,primary_crop,
           consent_recorded,consent_recorded_at,created_by,registered_by_role,registered_by_organization)
          VALUES (%s,'DEMO ONLY - Sample Farmer',NULL,'Hindi','Demo village','Sehore','Madhya Pradesh',
           %s,%s,%s,%s,2.0,'Soybean',1,NOW(),'DEMO FIELD TEAM','company_officer','Demo Fertiliser Field Partner')""", (FARMER_CODE, farm_id, lat, lon, NAME))
        farmer_id = cur.lastrowid
    print(f"Created demo farmer record ID {farmer_id}.")

now = datetime.now().replace(microsecond=0)
with db.db_cursor() as cur:
    cur.execute("SELECT sample_id FROM soil_samples WHERE sample_code=%s", (VERIFIED_SAMPLE_CODE,))
    has_verified = cur.fetchone()
if has_verified:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""UPDATE soil_samples SET collection_role='company_officer',
            collection_organization='Demo Fertiliser Field Partner',
            assigned_lab_organization='Demo Soil Testing Laboratory',
            lab_role='lab_staff', lab_organization='Demo Soil Testing Laboratory'
            WHERE sample_code=%s""", (VERIFIED_SAMPLE_CODE,))
if not has_verified:
    uploads = Path(os.getenv("UPLOAD_DIR", ROOT / "uploads"))
    uploads.mkdir(parents=True, exist_ok=True)
    source_pdf = ROOT / "data" / "demo" / "SAMPLE_SOIL_HEALTH_CARD_DEMO_ONLY.pdf"
    stored_pdf = "DEMO_SOIL_HEALTH_CARD_ONLY.pdf"
    if source_pdf.exists():
        shutil.copy2(source_pdf, uploads / stored_pdf)
    else:
        stored_pdf = None
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO soil_samples
          (sample_code,farmer_id,sample_description,collected_by,collected_at,latitude,longitude,
           collection_role,collection_organization,assigned_lab_organization,lab_name,status,received_at,tested_at,tested_by,
           lab_role,lab_organization,soil_ph,soil_ec_ds_m,organic_carbon_pct,
           available_n_kg_ha,available_p_kg_ha,available_k_kg_ha,lab_verified,verified_by,verified_at,
           report_original_filename,report_stored_filename,report_mime_type,lab_notes)
          VALUES (%s,%s,'Demo Soybean Field · sample A','DEMO FIELD TEAM',%s,%s,%s,
           'company_officer','Demo Fertiliser Field Partner','Demo Soil Testing Laboratory','DEMO ONLY - Example Soil Lab','Verified',%s,%s,'DEMO TECHNICIAN',
           'lab_staff','Demo Soil Testing Laboratory',7.2,0.35,0.62,
           245,18,310,1,'DEMO TECHNICIAN',%s,'SAMPLE_SOIL_HEALTH_CARD_DEMO_ONLY.pdf',%s,
           'application/pdf','Synthetic presentation values and fictional lab. Not an actual analysis.')""",
          (VERIFIED_SAMPLE_CODE, farmer_id, now-timedelta(days=8), lat, lon,
           now-timedelta(days=7), now-timedelta(days=6), now-timedelta(days=6), stored_pdf))
    print("Created one clearly labelled synthetic verified sample.")

with db.db_cursor() as cur:
    cur.execute("SELECT sample_id FROM soil_samples WHERE sample_code=%s", (PENDING_SAMPLE_CODE,))
    has_pending = cur.fetchone()
if has_pending:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""UPDATE soil_samples SET collection_role='company_officer',
            collection_organization='Demo Fertiliser Field Partner',
            assigned_lab_organization='Demo Soil Testing Laboratory'
            WHERE sample_code=%s""", (PENDING_SAMPLE_CODE,))
if not has_pending:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO soil_samples
          (sample_code,farmer_id,sample_description,collected_by,collected_at,latitude,longitude,status,collection_role,collection_organization,assigned_lab_organization)
          VALUES (%s,%s,'Demo North Field · awaiting laboratory','DEMO FIELD TEAM',%s,%s,%s,'Collected','company_officer','Demo Fertiliser Field Partner','Demo Soil Testing Laboratory')""",
          (PENDING_SAMPLE_CODE, farmer_id, now-timedelta(days=1), lat+0.0002, lon+0.0002))
    print("Created one synthetic sample awaiting laboratory testing.")

with db.db_cursor() as cur:
    cur.execute("SELECT COUNT(*) AS n FROM field_visits WHERE farmer_id=%s", (farmer_id,))
    visits = int(cur.fetchone()["n"])
if visits:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""UPDATE field_visits SET officer_role='company_officer',
            organization_name='Demo Fertiliser Field Partner'
            WHERE farmer_id=%s AND officer_name='DEMO FIELD TEAM'""", (farmer_id,))
if not visits:
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO field_visits
          (farmer_id,officer_name,visit_date,visit_purpose,visit_status,notes)
          VALUES (%s,'DEMO FIELD TEAM',%s,'Demonstration farm visit','Completed',
          'Synthetic presentation-only visit record.')""", (farmer_id, now-timedelta(days=8)))

print("\nDemo service records are ready.")
print(f"  Farmer: {FARMER_CODE}")
print(f"  Verified sample: {VERIFIED_SAMPLE_CODE}")
print(f"  Pending sample:  {PENDING_SAMPLE_CODE}")
print("All people, locations, values, samples and lab details above are synthetic demo data. Do not use them for actual farm decisions.")

# Demo-only role accounts. Real organisation accounts must be created by an
# administrator after checking the organisation and user's authorisation.
from werkzeug.security import generate_password_hash

DEMO_USERS = [
    ("farmer.demo", "Farmer@123", "farmer", "Demo Farmer Login", None, farmer_id),
    ("govt.demo", "Govt@123", "government_officer", "Demo Agriculture Officer", "Demo District Agriculture Office", None),
    ("company.demo", "Company@123", "company_officer", "Demo Company Field Officer", "Demo Fertiliser Field Partner", None),
    ("lab.demo", "Lab@123", "lab_staff", "Demo Soil Laboratory Technician", "Demo Soil Testing Laboratory", None),
    ("admin.demo", "Admin@123", "admin", "Demo Platform Administrator", "Demo Platform Administrator", None),
]
for username, password, role, display_name, organization_name, linked_farmer in DEMO_USERS:
    with db.db_cursor() as cur:
        cur.execute("SELECT user_id FROM app_users WHERE username=%s", (username,))
        existing = cur.fetchone()
    if existing:
        print(f"Demo account already exists: {username} (existing password retained).")
        continue
    with db.db_cursor(commit=True) as cur:
        cur.execute("""INSERT INTO app_users
            (username,password_hash,role,display_name,organization_name,farmer_id)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (username, generate_password_hash(password), role, display_name, organization_name, linked_farmer))
    print(f"Created demo account: {username} ({role}).")

print("\nDEMO-ONLY SIGN-IN ACCOUNTS (change before any shared or public deployment):")
print("  Farmer:      farmer.demo / Farmer@123")
print("  Government:  govt.demo / Govt@123")
print("  Company:     company.demo / Company@123")
print("  Soil lab:    lab.demo / Lab@123")
print("  Admin:       admin.demo / Admin@123")

# Make the regional crop-history pages presentation-ready without overwriting an
# uploaded district dataset. Synthetic figures are explicitly labelled in metadata.
from app.services import regional
if regional.CROP_FILE.exists():
    print(f"Regional crop dataset already exists and was preserved: {regional.CROP_FILE.name}")
else:
    crop_summary = regional.load_demo_crop_statistics()
    print("Loaded synthetic district crop-history for presentation only: "
          f"{crop_summary['rows']} rows across {crop_summary['districts']} districts.")
    print("This is not official Government data and must not be used for farm decisions.")
