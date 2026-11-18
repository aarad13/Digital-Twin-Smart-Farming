"""India-specific farming context for the Digital Twin.

Zone/state associations here are candidate classifications for the user to verify;
several states span more than one agro-climatic region. Exact agro-ecological
classification requires the relevant official GIS boundary layer.
"""
from __future__ import annotations

AGRO_CLIMATIC_ZONES = [
    {"id":"I","name":"Western Himalayan Region","states":["Himachal Pradesh","Jammu and Kashmir","Ladakh","Uttarakhand"],"climate":"Temperate to alpine; strong elevation gradients","typical_systems":["Horticulture","Cereals and pulses","Mixed farming"]},
    {"id":"II","name":"Eastern Himalayan Region","states":["Arunachal Pradesh","Assam","Manipur","Meghalaya","Mizoram","Nagaland","Sikkim","Tripura","West Bengal"],"climate":"Humid to per-humid; hill and valley microclimates","typical_systems":["Rice-based","Maize and pulses","Horticulture","Plantation"]},
    {"id":"III","name":"Lower Gangetic Plain Region","states":["West Bengal"],"climate":"Humid alluvial plains with monsoon rainfall","typical_systems":["Rice-based","Jute and pulses","Vegetables"]},
    {"id":"IV","name":"Middle Gangetic Plain Region","states":["Uttar Pradesh","Bihar"],"climate":"Sub-humid alluvial plains; monsoon and winter seasons","typical_systems":["Rice–wheat","Maize and pulses","Sugarcane"]},
    {"id":"V","name":"Upper Gangetic Plain Region","states":["Uttar Pradesh"],"climate":"Sub-humid to semi-arid plains; irrigated agriculture is important","typical_systems":["Rice–wheat","Sugarcane","Pulses and oilseeds"]},
    {"id":"VI","name":"Trans-Gangetic Plain Region","states":["Chandigarh","Delhi","Haryana","Punjab","Rajasthan"],"climate":"Semi-arid to sub-humid plains; high seasonal irrigation demand","typical_systems":["Rice–wheat","Cotton","Mustard and pulses"]},
    {"id":"VII","name":"Eastern Plateau and Hills Region","states":["Chhattisgarh","Jharkhand","Madhya Pradesh","Maharashtra","Odisha","West Bengal"],"climate":"Sub-humid plateau and uplands; rainfall variability","typical_systems":["Rainfed rice","Millets and pulses","Oilseeds"]},
    {"id":"VIII","name":"Central Plateau and Hills Region","states":["Madhya Pradesh","Rajasthan","Uttar Pradesh"],"climate":"Semi-arid to sub-humid plateau; seasonal monsoon dependence","typical_systems":["Soybean–wheat","Pulses","Millets and oilseeds"]},
    {"id":"IX","name":"Western Plateau and Hills Region","states":["Madhya Pradesh","Maharashtra"],"climate":"Semi-arid plateau; black-soil tracts and monsoon variability","typical_systems":["Cotton","Soybean","Sorghum and pulses"]},
    {"id":"X","name":"Southern Plateau and Hills Region","states":["Andhra Pradesh","Karnataka","Tamil Nadu","Telangana"],"climate":"Semi-arid to dry sub-humid plateau; variable monsoon influence","typical_systems":["Millets and pulses","Groundnut","Cotton and horticulture"]},
    {"id":"XI","name":"East Coast Plains and Hills Region","states":["Andhra Pradesh","Odisha","Puducherry","Tamil Nadu"],"climate":"Coastal humid and sub-humid; southwest and northeast monsoon influence varies","typical_systems":["Rice-based","Groundnut and pulses","Coconut and horticulture"]},
    {"id":"XII","name":"West Coast Plains and Ghats Region","states":["Goa","Karnataka","Kerala","Maharashtra","Tamil Nadu"],"climate":"Humid to per-humid coast and Western Ghats","typical_systems":["Rice and coconut","Spices and plantation","Horticulture"]},
    {"id":"XIII","name":"Gujarat Plains and Hills Region","states":["Gujarat","Dadra and Nagar Haveli and Daman and Diu"],"climate":"Arid to semi-arid plains and hills; monsoon concentrated rainfall","typical_systems":["Cotton","Groundnut","Millets and pulses"]},
    {"id":"XIV","name":"Western Dry Region","states":["Rajasthan"],"climate":"Hot arid; low and variable rainfall","typical_systems":["Pearl millet","Guar and pulses","Fodder and livestock systems"]},
    {"id":"XV","name":"Island Region","states":["Andaman and Nicobar Islands","Lakshadweep"],"climate":"Tropical maritime and humid","typical_systems":["Coconut","Rice and tubers","Plantation and horticulture"]},
]

INDIAN_SOIL_GROUPS = [
    "Alluvial", "Black / Regur", "Red and Yellow", "Laterite", "Arid / Desert",
    "Forest and Mountain", "Saline / Alkaline", "Peaty and Marshy", "Coastal Alluvial", "Other / Not classified"
]

INDIAN_SEASONS = {
    "Kharif": {"usual_window":"Monsoon season; sowing often June–July, harvest often September–November", "examples":["Rice","Maize","Bajra","Jowar","Soybean","Cotton","Groundnut","Tur/Arhar","Moong","Urad"]},
    "Rabi": {"usual_window":"Winter season; sowing often October–December, harvest often March–April", "examples":["Wheat","Barley","Gram / Chickpea","Mustard","Lentil","Peas","Rabi vegetables"]},
    "Zaid": {"usual_window":"Short summer season, commonly March–June where irrigation is available", "examples":["Summer Moong","Watermelon","Muskmelon","Cucumber","Fodder","Short-duration vegetables"]},
    "Perennial": {"usual_window":"Year-round or multi-year crop cycle; local calendar varies", "examples":["Sugarcane","Banana","Coconut","Tea","Coffee","Rubber","Mango","Spices"]},
}

IRRIGATION_METHODS = ["Canal","Tube well / Borewell","Open well","River / Lift irrigation","Tank / Farm pond","Drip","Sprinkler","Rainfed","Mixed / Other"]
WATER_SOURCES = ["Rainfed","Canal","Groundwater","Farm pond","River / Surface water","Tank","Recycled / Other"]
LAND_FORMS = ["Plain","Plateau","Hilly","Coastal","River valley / Floodplain","Arid / Desert","Other"]
FARMING_SYSTEMS = ["Rainfed","Irrigated","Mixed crop-livestock","Rice-based","Cereal-based","Pulse / Oilseed-based","Horticulture","Plantation","Agroforestry","Mixed / Other"]
CROP_STAGES = ["Land preparation","Nursery","Sowing / Planting","Germination","Vegetative growth","Flowering","Fruiting / Grain filling","Maturity","Harvested","Fallow"]


def normalise_state(value: str | None) -> str:
    return (value or "").strip().casefold().replace("&", "and")


def context_for_location(location: dict) -> dict:
    state = location.get("admin1") or location.get("state") or ""
    state_key = normalise_state(state)
    candidates = [z for z in AGRO_CLIMATIC_ZONES if any(normalise_state(s) == state_key for s in z["states"])]
    return {
        "country": "India",
        "state": state,
        "district": location.get("admin2") or location.get("district"),
        "agro_climatic_zone_candidates": [{k:v for k,v in z.items() if k != "states"} for z in candidates],
        "all_agro_climatic_zones": [{k:v for k,v in z.items() if k != "states"} for z in AGRO_CLIMATIC_ZONES],
        "zone_classification_note": "State association only. A state can span multiple agro-climatic regions; choose the zone using district/coordinate-level official mapping or local agricultural guidance.",
        "indian_seasons": INDIAN_SEASONS,
        "soil_groups": INDIAN_SOIL_GROUPS,
        "season_definitions": INDIAN_SEASONS,
        "season_note": "Season windows are broad Indian categories, not fixed dates for every district or crop. Use the state/crop-specific official crop calendar and local KVK advice.",
        "farming_systems": FARMING_SYSTEMS,
        "irrigation_methods": IRRIGATION_METHODS,
        "water_sources": WATER_SOURCES,
        "land_forms": LAND_FORMS,
        "crop_stages": CROP_STAGES,
        "sources": {
            "agro_climatic_regions": "https://digitallibrary.niti.gov.in/items/05085f17-672c-45d0-91b4-fdc09b7395b5",
            "crop_calendar": "https://nccd.gov.in/uploads/Agricultural_Statisitcs_at_a_Glance_2024_25_11da3cd37d.pdf",
            "soil_resources": "https://icar-nbsslup.org.in/",
            "soil_health_card": "https://soilhealth.dac.gov.in/"
        }
    }
