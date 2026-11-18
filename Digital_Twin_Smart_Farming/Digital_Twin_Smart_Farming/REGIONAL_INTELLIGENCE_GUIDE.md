# Regional Farm Intelligence — User Guide

This module extends the original two-farm EcoIrrigate prototype. It is designed
for regional exploration across India; it does not treat the two Kolkata
experimental-farm models as universal models for every location.

## 1. Search and analyse a region

1. Start the Flask application and open the dashboard.
2. In **Regional farm intelligence**, enter a village, town or district (for
   example, `Sehore, Madhya Pradesh`).
3. Choose the correct geocoding result. Check the district/state shown before
   proceeding, since one place name can match multiple locations.
4. Select **Analyze selected region**.

The module retrieves:

- A 2016–2025 climate summary from NASA POWER daily gridded agroclimate data.
- A 7-day weather outlook from Open-Meteo.
- Mapped topsoil properties from ISRIC SoilGrids WCS (where that service is
  reachable): pH, sand, clay, derived silt, soil organic carbon, total nitrogen,
  and cation-exchange capacity.
- A point-specific root-zone moisture history from NASA POWER Hydrology, if a
  sufficiently complete and recent series is available. The app compares
  persistence, Ridge and Random Forest on a chronological holdout before it
  decides whether to use a learned model for the 7-day forecast.

## 2. Load the local crop history

The district crop section requires the official Government of India district-
wise, season-wise crop-production CSV. Download it from:

https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0

Upload the CSV in the dashboard. The importer expects equivalents of these
columns:

- Required: `State_Name`, `District_Name`, `Season`, `Crop`
- Optional but recommended: `Crop_Year`, `Area`, `Production`

After uploading, run the location analysis again. The dashboard shows crops
recorded in the selected district, their recorded seasons, and mean annual area
and production over the most recent available years (up to five). This is a
historical cropping-pattern summary, not a forecast of what farmers will plant
next season and not proof that a crop is suitable or profitable at a specific
field.

## 3. Understand the soil profile and fertility indicators

SoilGrids is a mapped/modelled product. Its 0–5 cm topsoil values are regional
estimates, not a field sample. The coarse texture label is a screening aid based
on the sand/clay fractions; it is not a formal soil-series classification.

The mapped profile may show pH, soil organic carbon, total nitrogen and CEC.
Total nitrogen is not the same as plant-available nitrogen. SoilGrids does not
provide a full field-specific available N-P-K and micronutrient diagnosis in
this screen. For fertilizer and amendment decisions, use a representative
laboratory report or Soil Health Card from the Government of India's portal:

https://soilhealth.dac.gov.in/

The app does not calculate a definitive fertility grade or prescribe fertilizer
rates.

## 4. Interpret “What to review next”

The action cards are rule-based review prompts generated from the weather
outlook, available mapped soil indicators and district cropping records. They
may suggest monitoring field moisture, checking drainage after rain, verifying
pH with a laboratory test, or reviewing the established local crop-season
pattern. They are not agronomic prescriptions, automatic irrigation commands,
or guaranteed yield/water-saving recommendations. Confirm decisions with field
observations and local agricultural expertise.

## 5. Understand regional prediction

The location-specific model uses the nearest NASA POWER grid point. Its target
is RZMC (root-zone volumetric moisture) where available; GWETROOT (relative
root-zone wetness) is a separately labelled fallback and has a different unit.
The model is trained on the selected point's own historical NASA series and
compared with persistence using a chronological holdout. The app withholds a
forecast when the latest observation is too old or the aligned data are
insufficient.

This prediction is a coarse gridded land-surface-model estimate. It is not a
sensor reading from the selected farm, and its holdout score is not evidence of
field-level accuracy. The EcoIrrigate models remain limited to their two
experimental Kolkata farms.

## 6. Data sources

- Open-Meteo Geocoding: https://open-meteo.com/en/docs/geocoding-api
- Open-Meteo Forecast: https://open-meteo.com/en/docs
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NASA POWER Hydrology: https://power.larc.nasa.gov/docs/methodology/data/sources_hydrology/
- ISRIC SoilGrids WCS: https://docs.isric.org/globaldata/soilgrids/wcs.html
- India OGD crop-production statistics: https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0
- Soil Health Card portal: https://soilhealth.dac.gov.in/

Regional analysis requires internet access. API/service availability can vary.
If a source cannot be reached or does not return a sufficiently complete data
series, the module reports that source as unavailable rather than filling the
gap with fabricated values.

## 7. Create the virtual structure of an Indian farm

After analysing a selected Indian location, choose **Create virtual farm from
this region**. Enter the farm's own area and replace the geocoding reference
coordinates with the actual farm coordinates. Select the agro-climatic zone
only after checking the district/sub-district mapping; a state can intersect
more than one of the Planning Commission's 15 regions.

Draw the outer farm perimeter first, then use the polygon drawing tool to map separate plots/fields inside it. For each plot, enter
its crop and variety, Kharif/Rabi/Zaid/perennial season, sowing date, crop stage,
broad Indian soil group, irrigation method and water source. Soil pH, EC,
organic carbon and available N/P/K can be entered only from a field Soil Health
Card/laboratory report. Add borewells, open wells, ponds, tanks, pumps, channels,
buildings or storage as point assets on the farm map.

The outer farm and plot geometries are user-drawn and are not cadastral boundaries. Plot area is
entered/confirmed by the user. The regional soil profile remains a mapped
estimate; the app does not silently copy it into the plot's test values.

## Regional farmer-problem diagnosis and response layer

After a user selects a location, the application now separates regional context from current signals:

- **Documented regional challenges:** sourced state-level issues and the responses described by ICAR. The initial curated coverage includes Madhya Pradesh, Maharashtra, Haryana, Andhra Pradesh and Puducherry. For other states, broad agro-climatic-zone context is shown where a candidate zone is available.
- **Current location signals:** the application checks the 7-day forecast and SoilGrids screening values for possible short-term concerns. A dry/hot forecast, a forecast daily rainfall amount at or above the IMD heavy-rainfall threshold, mapped pH outside a broad screening range, sand-dominant texture, or clay-rich texture can produce a prompt.
- **District contingency plans:** the ICAR-CRIDA directory is linked so the user can select the actual district and review the official district agriculture profile and contingency tables.

### Critical interpretation rules

- A documented state/zone issue means that the issue is reported in that region; it does not prove that it exists on the selected farm.
- Weather forecast prompts are not IMD warnings. The application checks official IMD criteria as a reference but does not issue official alerts.
- SoilGrids is a gridded estimate and must not be presented as a laboratory test.
- Mapped pH/texture signals prompt field verification, not automatic lime/gypsum/fertilizer prescriptions.
- Available N, P, K, S, micronutrients, irrigation-water quality and crop symptoms require field-specific records or expert diagnosis.
- Use KVK/State Agricultural University and ICAR-CRIDA district contingency plans for crop-, season- and district-specific actions.

The report is produced by `app/services/regional_problems.py` and attached to the regional analysis response as `regional_problem_report`.
