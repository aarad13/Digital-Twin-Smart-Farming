# Project overview

## Intended use
Academic prototype demonstrating a software Digital Twin-like state record for
an experimental farm series, with observed soil-moisture history, short-horizon
forecasts, and rule-based advisory persistence.

## What makes this more than a chart
- Each farm has a persistent identity/profile in MySQL.
- Observations are stored against a farm and timestamp.
- Forecast records retain forecast origin, target time, horizon, model and feature
  set.
- Advisory records retain the threshold and explanation used at generation time.
- Historical observations are not overwritten when new readings are imported.

## Dataset-to-project mapping
- Farm identity: `Farm_ID`
- State variable: `Volumetric_Moisture_Pct`
- Environmental context: atmospheric temperature, atmospheric pressure, soil
  temperature, sensor-board temperature
- Temporal context: hour/day cyclic features and derived lagged/rolling features
- Missing in the current CSV: rainfall, relative humidity, crop stage, soil class,
  irrigation amount and live sensor messages

## Demonstration sequence
1. Select Kolkata_Farm_1 or Kolkata_Farm_2.
2. Inspect the latest observed state and the historical moisture series.
3. Choose a horizon (1 h / 6 h) and method.
4. Generate a forecast and compare the outputs of the available methods.
5. Review the rule-based advisory and its stated threshold.
6. Configure optional crop, soil and field-area metadata.
7. Review saved forecasts/advisories in the history table.

## Important interpretation
The data are historical readings from two experimental sites, not the user's
own farm and not a live sensor connection. The configured moisture threshold is
only a demonstration setting. The application does not execute irrigation,
measure water savings, predict crop yield, or generalize to all Indian farms.


## Location-based regional intelligence (additional module)
The app includes a separate regional view that searches Indian locations and
combines NASA POWER climate/history, Open-Meteo forecasts, SoilGrids WCS soil
property estimates, optional official district crop-production CSV data, and a
location-specific NASA root-zone soil-moisture model. The regional ML model is
validated against a chronological holdout and compared with persistence before
7-day forecasts are displayed. Regional crop records are summarized by crop
and season, with mean annual area/production over recent available years. Soil
outputs include mapped texture and fertility-related indicators, but not a
complete field soil test or definitive fertility grade. Rule-based next-step
cards are prompts for field review, not prescriptions. Regional moisture is a
coarse gridded estimate, not a farm sensor. The original EcoIrrigate models are
not applied outside their two experimental Kolkata sites. See README.md,
REGIONAL_INTELLIGENCE_GUIDE.md and FARM_PREDICTIONS_AND_REGIONAL_DATA_GUIDE.md for data sources, user steps and limitations.

## Indian virtual farm structure (new core layer)
The MySQL schema now includes `virtual_farms`, `virtual_farm_plots`, and
`virtual_farm_assets`. A farm site records its selected Indian location, farm
area, candidate agro-climatic region, farming system, landform, water source,
primary irrigation method, and regional climate/soil snapshots with provenance.
Each plot stores its map polygon, area, crop, Indian season, crop stage, broad
Indian soil group, irrigation method, and optional field-test values for pH, EC,
organic carbon and available N/P/K. Point infrastructure assets include wells,
ponds, tanks, pumps, channels, farm buildings and storage.

This is a virtual structure and profile model, not a land-record/cadastral
survey. Geometry is map-drawn by the user; areas are entered or checked in
hectares. Regional estimates must not be copied into field soil-test values.
See README.md and REGIONAL_INTELLIGENCE_GUIDE.md.


## Regional farmer problems and solution guidance (added)

The location analysis now includes a regional problem/response report. It combines source-backed state or agro-climatic context with short-term weather and mapped-soil screening signals. The initial state-level ICAR profiles cover Madhya Pradesh, Maharashtra, Haryana, Andhra Pradesh and Puducherry; other locations use broad agro-climatic candidate-zone context and a direct link to the ICAR-CRIDA district contingency plan directory. The report deliberately separates common regional constraints from current signals and from field-confirmed farm conditions. See `docs/REGIONAL_PROBLEM_SOLUTION_SOURCES.md`.


## Assisted village service and role-based access (November 2026)

The application now supports separate local sign-in types for farmers, government agriculture/extension officers, agriculture company/FPO field teams, soil laboratory staff and platform administrators. Field staff can register farmers after consent, schedule visits, capture approved farm data, issue one-time farmer activation codes and create traceable soil sample IDs assigned to an exact destination lab organisation. Lab staff can view and update only samples assigned to their matching lab organisation. Company workspaces are filtered to their provisioned organisation name. Farmer accounts see only their linked farmer profile, virtual farm and samples.

Farmers can self-register or activate an account handed over by a field officer. Activation codes expire after seven days; SMS/OTP delivery is not integrated. The previous Digital Twin regional intelligence, My Area location analysis, virtual farm map, farm-specific outlook, research forecasts, experimental telemetry and charts remain available according to the logged-in role. The Farm Predictions view refreshes farm choices on entry and automatically generates the latest saved farm outlook; research forecasts remain separate and clearly limited to the two Kolkata experimental farms. The header-level MySQL connected badge has been removed; `/health` remains for Docker container health checks.

This is a local pilot implementation, not a live government/company integration or production identity solution. See `AUTH_AND_ACCESS_GUIDE.md` and `ASSISTED_VILLAGE_SERVICE_GUIDE.md` for account issuance, sample routing, demo credentials and security limitations.


## Public datasets, predictions and square-foot entry

The project now includes a one-time downloader/trainer for the India District Crop Dataset (1997–2015), with attribution and limitations in `DATASET_SOURCES_AND_PREDICTIONS.md`. Live regional inputs are drawn from NASA POWER, Open-Meteo and ISRIC SoilGrids WCS; district crop history can also be uploaded from the Government of India DES dataset. The live IMD gridded rainfall page is documented as a potential cross-check, but is not yet part of the automatic pipeline.

All individual farm and plot areas are entered and displayed in square feet. MySQL stores the equivalent in hectares internally for backward compatibility. District-level government crop area tables retain the source unit (hectares), and are labelled as district statistics rather than individual farm areas.
