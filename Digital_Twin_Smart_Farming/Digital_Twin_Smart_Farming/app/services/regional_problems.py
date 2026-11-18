"""Region-aware farmer challenge and response knowledge for Indian agriculture.

Profiles are summaries of official ICAR material. They are regional planning
context, not diagnoses of an individual holding. Live signals are generated
separately from the selected point's weather forecast and mapped soil estimates.
"""
from __future__ import annotations

import re
from typing import Any

CRIDA_DIRECTORY = "https://www.icar-crida.res.in/Crop_Contingency_Plan.html"

STATE_PROFILES: dict[str, dict[str, Any]] = {
    "madhya pradesh": {
        "source_name": "ICAR state agricultural profile: Madhya Pradesh",
        "source_url": "https://www.icar.gov.in/hi/node/17271",
        "scope": "State-level documented constraints; district and farm conditions vary.",
        "farming_context": "Soybean–wheat and other cereal, pulse and oilseed systems; large rainfed share.",
        "challenges": [
            {"category":"Water and climate", "problem":"A large share of cultivated land is rainfed and depends on monsoon rainfall; drought and heat stress can affect crop establishment and yield.", "response":"Use the district crop-contingency plan for delayed monsoon or dry spells. Review farm-pond/rainwater harvesting, moisture conservation and need-based protective irrigation where water is available.", "verify":"Check local rainfall departure, sowing date, soil depth and actual field moisture before changing crop or irrigation plans."},
            {"category":"Soil health", "problem":"ICAR describes black and red soils in the state as having low-to-medium fertility; nutrient needs vary by field and crop.", "response":"Use a current Soil Health Card or laboratory report for soil-test-based nutrient management. Organic-resource recycling such as suitable composting can be considered as part of an integrated soil-health plan.", "verify":"Do not infer available N, P, K, sulphur or micronutrient deficiency from a regional soil map; obtain a field soil test."},
            {"category":"Wheat production", "problem":"ICAR identifies heat stress, drought stress, late sowing and limited varietal replacement among wheat production constraints.", "response":"Use the locally applicable sowing window and consult the district KVK/state agricultural university for varieties suited to timely or late sowing and irrigation availability.", "verify":"Confirm the actual crop, sowing date, variety and irrigation status before recommending a change."},
        ],
    },
    "maharashtra": {
        "source_name": "ICAR state agricultural profile: Maharashtra",
        "source_url": "https://www.icar.gov.in/index.php/en/node/17272",
        "scope": "State-level documented constraints; scarcity, plain and coastal zones differ substantially.",
        "farming_context": "Rain-dependent farming with cotton, soybean, sorghum, pearl millet, pulses, oilseeds and sugarcane in different zones.",
        "challenges": [
            {"category":"Water availability", "problem":"ICAR reports substantial dependence on rainfall and a relatively small irrigated share at the state level.", "response":"Review watershed development, rainwater harvesting and protective/life-saving irrigation planning. Check district rainfall forecasts and available water before scheduling irrigation.", "verify":"Confirm the farm's water source, storage, groundwater availability and the current district rainfall situation."},
            {"category":"Soil depth and nutrients", "problem":"ICAR identifies shallow soils and state-level deficiencies involving nitrogen, phosphorus, zinc and sulphur.", "response":"Use field-specific soil testing and site-specific nutrient management. Match nutrient application to crop, soil test and local university/KVK recommendation.", "verify":"These are state-level observations, not proof that a selected plot is deficient. Test available nutrients and soil depth on the farm."},
            {"category":"Rainfall extremes and field drainage", "problem":"ICAR-CRIDA's Maharashtra contingency preparedness material warns that intense or continuous rainfall can cause temporary waterlogging in susceptible fields.", "response":"Identify low-lying or waterlogging-prone plots. Where suitable, review broad-bed-and-furrow, ridge-and-furrow, paired-row planting and graded surface drainage with local agronomists.", "verify":"Use field topography and soil information. Do not apply one land-shaping method to every soil or slope."},
        ],
    },
    "haryana": {
        "source_name": "ICAR state agricultural profile: Haryana",
        "source_url": "https://www.icar.gov.in/index.php/en/node/17265",
        "scope": "State-level constraints; intensity varies by district, block and irrigation command.",
        "farming_context": "Rice–wheat, cotton–wheat and pearl-millet–wheat systems are reported by ICAR.",
        "challenges": [
            {"category":"Groundwater and water quality", "problem":"ICAR reports both declining and rising water tables and widespread areas underlain by poor-quality irrigation water.", "response":"Track groundwater depth and irrigation-water quality. Compare crop water demand with available supply and consider resource-conserving irrigation and locally suitable crop diversification.", "verify":"Obtain local groundwater and irrigation-water test results; the state profile cannot establish the condition of a particular well."},
            {"category":"Soil salinity and alkalinity", "problem":"ICAR reports soil salinity/alkalinity and declining soil health in parts of Haryana.", "response":"Test soil pH and electrical conductivity (EC). Apply gypsum or other reclamation treatments only where a soil/water test and local agronomic recommendation establish the need; assess drainage where relevant.", "verify":"Do not prescribe gypsum from location alone. Confirm sodicity, salinity, soil texture and drainage first."},
            {"category":"Nutrient-use efficiency", "problem":"ICAR identifies the need for site-specific nutrient management in the state's major cropping systems.", "response":"Base fertilizer planning on Soil Health Card/laboratory values and crop-stage recommendations; avoid blanket fertilizer rates.", "verify":"Available N, P, K, S and micronutrients require field-specific testing."},
        ],
    },
    "andhra pradesh": {
        "source_name": "ICAR state agricultural profile: Andhra Pradesh",
        "source_url": "https://www.icar.gov.in/en/node/17257",
        "scope": "State-level summary; coastal, delta, upland and drought-prone districts require separate plans.",
        "farming_context": "Rice, cotton, groundnut, pigeonpea, sunflower, blackgram and sorghum are reported as important crops.",
        "challenges": [
            {"category":"Drought and extreme weather", "problem":"ICAR describes recurrent droughts and severe cyclonic storms, with water scarcity affecting crop production.", "response":"Review village-pond renovation, farm water harvesting, supplementary irrigation planning and district contingency measures for drought/cyclone conditions.", "verify":"Check the current IMD warning and district contingency plan; a general climate profile is not a live hazard alert."},
            {"category":"Soil fertility and salinity", "problem":"ICAR reports red-lateritic and black soils, with low fertility and salt-affected areas in parts of the state.", "response":"Use soil and irrigation-water testing, site-specific nutrient management and locally approved reclamation/drainage measures where salinity is confirmed.", "verify":"Test soil pH, EC and available nutrients. Do not infer salinity or prescribe amendments solely from coordinates."},
            {"category":"Rice crop health", "problem":"ICAR identifies bacterial leaf blight, gall midge and sheath blight among rice production constraints in the state.", "response":"Use resistant/tolerant varieties and integrated pest and disease management recommended by the local KVK or agricultural university; seek diagnosis when symptoms appear.", "verify":"This is a regional crop-health risk, not a diagnosis. Confirm crop, symptoms and pest/disease through a qualified local extension service."},
        ],
    },
    "puducherry": {
        "source_name": "ICAR agricultural profile: Puducherry",
        "source_url": "https://www.icar.gov.in/en/node/17282",
        "scope": "Territory-level description; coastal, deltaic and inland plots may differ.",
        "farming_context": "Rice and blackgram are highlighted; horticulture and coconut systems are also described by ICAR.",
        "challenges": [
            {"category":"Salinity and waterlogging", "problem":"ICAR describes fine coastal/deltaic alluvial soils as alkaline or saline and reports rainy-season waterlogging and dry-season salinity in affected areas.", "response":"Check field drainage and test soil/water EC and pH. Use salt-tolerant crop varieties only when recommended for the crop and local salinity class; review moisture conservation and suitable drip irrigation in drought-prone plots.", "verify":"Confirm the field's salinity, water-table depth and drainage before choosing a crop or reclamation method."},
            {"category":"Soil fertility and organic resources", "problem":"ICAR reports low soil fertility in parts of the coastal/deltaic agricultural area.", "response":"Use a field Soil Health Card and locally recommended integrated nutrient management. Composting suitable farm residues can be reviewed where appropriate.", "verify":"Fertilizer and amendment rates must follow field soil-test results and crop recommendations."},
        ],
    },
}

# Regional-level fallback for states without a curated state profile above.
# These are broad context categories, not district-level diagnoses.
ZONE_PROFILES = {
    "I": {"name":"Western Himalayan Region", "challenges":[("Slope, erosion and fragile mountain soils","Use locally suitable contour/terrace maintenance, vegetative barriers and soil-conservation measures; obtain watershed/KVK guidance."),("Cold, frost and elevation-dependent growing windows","Use district crop calendars and locally recommended varieties; check IMD cold/frost advisories before sensitive crop stages.")]},
    "II": {"name":"Eastern Himalayan Region", "challenges":[("High rainfall, erosion and flood/landslide exposure in susceptible locations","Maintain field drainage and vegetative soil cover; use watershed and slope-specific conservation advice."),("Short-fallow shifting cultivation and soil degradation in some landscapes","Review locally appropriate integrated farming, agroforestry and soil-conservation options with ICAR/KVK institutions.")]},
    "III": {"name":"Lower Gangetic Plain Region", "challenges":[("Flooding and waterlogging in low-lying areas","Use district contingency plans, maintain field drainage and assess flood-tolerant crop options only through local recommendations."),("Fragmented holdings and drainage constraints","Coordinate drainage and crop planning at plot/village scale where possible.")]},
    "IV": {"name":"Middle Gangetic Plain Region", "challenges":[("Flood/drought variability and poor drainage in susceptible districts","Use ICAR-CRIDA district contingency plans and align sowing/variety decisions with rainfall and field drainage."),("Groundwater and soil-fertility variation","Test irrigation water and soil; use site-specific nutrient and water management.")]},
    "V": {"name":"Upper Gangetic Plain Region", "challenges":[("Irrigation dependence and groundwater pressure in some districts","Monitor local groundwater and irrigation demand; assess water-saving irrigation and locally suitable crop diversification."),("Soil fertility and residue-management constraints","Use Soil Health Card-based nutrient planning and locally suitable residue-management practices.")]},
    "VI": {"name":"Trans-Gangetic Plain Region", "challenges":[("Groundwater depletion, water-quality and salinity risks in parts of the region","Monitor water table and irrigation-water EC; use site-specific nutrient management and drainage/reclamation only after testing."),("Crop-residue and intensive cereal-system pressures","Review crop diversification and conservation agriculture with local extension services.")]},
    "VII": {"name":"Eastern Plateau and Hills Region", "challenges":[("Rainfed dependence, soil erosion and limited irrigation in some upland districts","Use watershed development, contour/graded bunding where suitable, rainwater harvesting and locally suitable mixed cropping."),("Low and variable soil fertility","Use field soil testing and integrated nutrient management rather than blanket fertilizer recommendations.")]},
    "VIII": {"name":"Central Plateau and Hills Region", "challenges":[("Seasonal drought and land degradation in susceptible areas","Review rainwater harvesting, farm ponds, moisture conservation and district contingency options."),("Soil depth and fertility vary sharply across short distances","Use plot-level soil testing and adapt crop/management choices to soil depth and water availability.")]},
    "IX": {"name":"Western Plateau and Hills Region", "challenges":[("Rainfed farming and monsoon variability","Review watershed measures, protective irrigation and crop-contingency plans for the selected district."),("Shallow or heavy soils and nutrient constraints in some tracts","Confirm soil depth, drainage and nutrient status by field survey and laboratory test before choosing amendments.")]},
    "X": {"name":"Southern Plateau and Hills Region", "challenges":[("Rainfall variability and recurring dry spells in semi-arid tracts","Use district-specific drought plans, soil-moisture conservation and water harvesting; adjust crop decisions through local advisories."),("Groundwater and irrigation constraints","Track source reliability and use efficient irrigation where agronomically and economically suitable.")]},
    "XI": {"name":"East Coast Plains and Hills Region", "challenges":[("Cyclone, intense rainfall, coastal salinity and waterlogging exposure in susceptible areas","Follow IMD warnings and district contingency plans; inspect drainage and protect seed, nursery and stored inputs."),("Seasonal water stress between rainfall periods","Review rainwater storage, soil-moisture conservation and crop-specific irrigation schedules.")]},
    "XII": {"name":"West Coast Plains and Ghats Region", "challenges":[("High rainfall, runoff, erosion and waterlogging on vulnerable slopes/lowlands","Maintain drainage and ground cover; use slope-appropriate conservation measures and avoid generic land-shaping prescriptions."),("Monsoon-related crop disease pressure","Use crop-specific surveillance and KVK/IPM advice; do not diagnose a disease from regional climate alone.")]},
    "XIII": {"name":"Gujarat Plains and Hills Region", "challenges":[("Rainfall concentration, drought and water scarcity in dry tracts","Use local water-harvesting, drought contingency and crop-water planning."),("Salinity/alkalinity in some inland and coastal settings","Test soil and irrigation water before selecting reclamation or crop-tolerance measures.")]},
    "XIV": {"name":"Western Dry Region", "challenges":[("Low and variable rainfall, drought and limited water storage","Prioritise rainwater harvesting, moisture conservation, locally adapted dryland crops and district contingency plans."),("Wind erosion and soil degradation in exposed areas","Maintain soil cover, windbreaks and locally suitable sand/soil conservation measures.")]},
    "XV": {"name":"Island Region", "challenges":[("Cyclone, coastal salinity, erosion and freshwater limitations","Use official cyclone warnings, protect freshwater storage, maintain coastal buffers and seek island-specific crop advisories."),("Heavy rain and localized drainage constraints","Inspect drainage and protect planting material and farm infrastructure before forecast extreme weather.")]},
}


def _key(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().casefold().replace("&", "and"))


def _live_signals(forecast: dict, soil: dict, location: dict) -> list[dict]:
    signals: list[dict] = []
    days = forecast.get("daily") or []
    rain_values = [float(d["precipitation_mm"]) for d in days if d.get("precipitation_mm") is not None]
    max_values = [float(d["max_temp_c"]) for d in days if d.get("max_temp_c") is not None]
    if rain_values and max_values and sum(rain_values) <= 5 and max(max_values) >= 35:
        signals.append({"level":"Watch", "title":"Short-term dry and hot weather watch", "evidence":f"The 7-day forecast totals {sum(rain_values):.1f} mm rainfall and reaches {max(max_values):.1f} °C maximum temperature.", "response":"Check crop stage and field moisture. Review protective irrigation or mulching only if the crop, soil and available water justify it; reassess after observed rainfall.", "basis":"Automated screening rule using Open-Meteo forecast; not an IMD drought/heatwave declaration."})
    heavy_days = [(d.get("date"), float(d["precipitation_mm"])) for d in days if d.get("precipitation_mm") is not None and float(d["precipitation_mm"]) >= 64.5]
    if heavy_days:
        peak = max(x[1] for x in heavy_days)
        signals.append({"level":"Watch", "title":"Heavy-rainfall amount appears in the 7-day model forecast", "evidence":f"At least one forecast day reaches {peak:.1f} mm. IMD classifies 64.5–115.5 mm in 24 hours as heavy rainfall.", "response":"Check the official IMD district warning; inspect field drains and low-lying plots, protect nursery/harvested produce and avoid irrigation before forecast rain. Do not treat this third-party model output as an IMD warning.", "basis":"Open-Meteo forecast screened against IMD rainfall terminology."})
    if max_values and max(max_values) >= (30 if str(location.get("landform", "")).lower() == "hilly" else 40):
        signals.append({"level":"Check official warning", "title":"High maximum-temperature threshold reached in forecast", "evidence":f"Forecast maximum temperature reaches {max(max_values):.1f} °C.", "response":"Check the official IMD heatwave bulletin and crop-specific KVK advice. Review crop stage, soil moisture and livestock water/shade arrangements where relevant.", "basis":"Temperature threshold screening only. IMD heatwave classification also depends on climatological departure and station criteria."})
    props = soil.get("properties", {}) if soil.get("status") == "available" else {}
    ph = (props.get("ph") or {}).get("value")
    sand = (props.get("sand_pct") or {}).get("value")
    clay = (props.get("clay_pct") or {}).get("value")
    if ph is not None and (float(ph) < 5.5 or float(ph) > 8.5):
        direction = "acidic" if float(ph) < 5.5 else "alkaline"
        signals.append({"level":"Field verification", "title":f"Mapped topsoil pH screening suggests an {direction} reaction", "evidence":f"SoilGrids mapped pH estimate is {float(ph):.1f} at {soil.get('depth','the reported depth')}.", "response":"Collect a representative field soil sample and confirm pH/EC through a Soil Health Card or accredited laboratory before considering liming, gypsum or other amendments.", "basis":"SoilGrids gridded prediction; not a field laboratory measurement."})
    if sand is not None and float(sand) >= 70:
        signals.append({"level":"Field verification", "title":"Mapped soil texture is sand-dominant", "evidence":f"Mapped sand fraction is approximately {float(sand):.0f}%.", "response":"Check infiltration and moisture retention in the actual plot. Consider locally suitable organic-matter and irrigation-management practices only after field verification.", "basis":"SoilGrids topsoil texture screening."})
    elif clay is not None and float(clay) >= 40:
        signals.append({"level":"Field verification", "title":"Mapped soil texture is clay-rich", "evidence":f"Mapped clay fraction is approximately {float(clay):.0f}%.", "response":"Inspect drainage and field trafficability after rain. Choose drainage or bed-shaping measures only after checking slope, soil structure and local recommendations.", "basis":"SoilGrids topsoil texture screening."})
    return signals


def build_regional_problem_report(location: dict, indian_context: dict, climate: dict,
                                  forecast: dict, soil: dict, crop_pattern: dict) -> dict:
    state = _key(location.get("admin1") or location.get("state"))
    profile = STATE_PROFILES.get(state)
    profile_level = "State-level ICAR profile" if profile else "Agro-climatic-zone context"
    if profile:
        challenges = [dict(x, evidence_scope="Documented state-level constraint") for x in profile["challenges"]]
        profile_name = state.title()
        context = profile.get("farming_context", "")
        source_name = profile["source_name"]
        source_url = profile["source_url"]
        scope_note = profile["scope"]
    else:
        candidates = indian_context.get("agro_climatic_zone_candidates") or []
        selected_zone = candidates[0] if candidates else None
        zone_profile = ZONE_PROFILES.get(str(selected_zone.get("id"))) if selected_zone else None
        if zone_profile:
            candidate_ids = {str(z.get("id")) for z in candidates}
            selected_profiles = [ZONE_PROFILES[zid] for zid in candidate_ids if zid in ZONE_PROFILES]
            profile_name = " / ".join(p["name"] for p in selected_profiles) or zone_profile["name"]
            context = "; ".join(sorted({system for z in candidates for system in z.get("typical_systems", [])}))
            merged = []
            seen = set()
            for zp in selected_profiles:
                for problem, response in zp["challenges"]:
                    if problem not in seen:
                        merged.append({"category":"Agro-climatic constraint", "problem":problem,
                                       "response":response, "verify":"This is broad regional context. Check the named district's ICAR-CRIDA contingency plan and local KVK before acting.",
                                       "evidence_scope":"Candidate agro-climatic-region context"})
                        seen.add(problem)
            challenges = merged
            source_name = "ICAR / Planning Commission agro-climatic region context"
            source_url = "https://www.icar.gov.in/sites/default/files/Circulars/India_BRICS_Agriculture_Report.pdf"
            scope_note = indian_context.get("zone_classification_note", "State-level zone matching is approximate.") + " These are candidate zones; district-level plans take precedence."
        else:
            profile_name = "Not established from available state/zone mapping"
            context = ""
            challenges = []
            source_name = "ICAR-CRIDA district contingency plan directory"
            source_url = CRIDA_DIRECTORY
            scope_note = "No state-specific profile was matched. Open the district plan directory and select the correct district."
    current_signals = _live_signals(forecast, soil, location)
    if crop_pattern.get("available"):
        crops = ", ".join(x.get("crop", "") for x in crop_pattern.get("crops", [])[:5])
        context = (context + ("; " if context else "") + f"Historical district crops in uploaded data: {crops}")
    return {
        "profile_level": profile_level,
        "profile_name": profile_name,
        "farming_context": context,
        "scope_note": scope_note,
        "documented_challenges": challenges,
        "current_signals": current_signals,
        "district_plan_url": CRIDA_DIRECTORY,
        "district_plan_note": "Open ICAR-CRIDA and select the state and district to view its agriculture profile and crop-contingency strategies for delayed monsoon, drought, excess rain, floods, heat/cold waves and other events.",
        "profile_source_name": source_name,
        "profile_source_url": source_url,
        "interpretation_note": "Documented regional constraints are not proof that the selected farm has the problem. Current signals are automated screening prompts from gridded/modelled data. Confirm on-farm conditions and consult the local Krishi Vigyan Kendra/agricultural university before crop, fertilizer, pesticide or irrigation decisions.",
    }
