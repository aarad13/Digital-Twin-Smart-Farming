# Dataset sources, prediction inputs and area units

This document records where the application's public datasets come from, what each is used for, and what it does **not** prove.

## 1. India district crop, soil and climate dataset (model training download)

- Repository: https://github.com/priyanshupriyank04/india-district-crop-dataset
- CSV download used by the preparation script: https://raw.githubusercontent.com/priyanshupriyank04/india-district-crop-dataset/main/data/final/india_district_crop_dataset_1997_2015.csv
- Coverage described by the repository: 34,903 rows × 48 columns; 652 districts; 34 states/UTs; 1997–2015; six seasons.
- Licence stated by the repository: CC BY 4.0 for the derived dataset (code MIT).
- Model target: `dominant_crop`, defined by the repository as the crop with the largest recorded sown area in a district, crop year and season.
- Model inputs used in this project: SoilGrids 0–5 cm topsoil variables, seasonal and annual climate variables, elevation and season.
- One-time setup command (run from the project root while Docker is running):

  ```bash
  docker compose exec web python /app/scripts/prepare_india_crop_model.py
  ```

The raw CSV is about 23 MB. It is downloaded from the source repository on the user's first run, then stored in `data/regional/india_district_crop_dataset_1997_2015.csv`. The compose file mounts `./data/regional` so the downloaded CSV, trained model and manifest persist outside the web container. The CSV is not silently fabricated or replaced with demo values.

**Interpretation:** the output ranks historical district crop patterns for similar environmental inputs. It is not proof that a crop is suitable or profitable on an individual field, not an individual farm yield forecast, and not a planting prescription. The model uses district-grouped 5-fold validation to reduce leakage across records from the same district. Display the actual validation values from the generated manifest; do not substitute a marketing accuracy figure.

### Original component sources identified in that repository

1. Government of India, Ministry of Agriculture and Farmers Welfare / Department of Agriculture and Farmers Welfare / Directorate of Economics and Statistics (DES), `District-wise, season-wise crop production statistics` on data.gov.in. The official catalogue says area is in hectares and production is in tonnes; it is annual and district/crop/season-wise. The data.gov.in platform identifies the Government Open Data License – India for published datasets/resources.
2. District boundaries and crosswalks listed by the source repository (Census 2011 / LGD-linked boundaries).
3. ISRIC SoilGrids 2.0 for mapped soil properties.
4. NASA POWER monthly climate values for the historical training table.

Attribution: cite the source repository and the component sources above. The derived dataset is not itself an official Ministry-endorsed model.

## 2. Live location-specific weather and climate inputs

### NASA POWER Daily API

- Documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- Used by the app for location-specific historical daily climate at the saved latitude/longitude.
- Current parameters requested by this project: `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`.
- Used for historical temperature, rainfall, humidity, wind and solar-radiation features, plus historical root-zone/weather modelling where available.
- API response/cache is a modelled gridded product at/near the farm coordinate, not a sensor measurement from that field.

### Open-Meteo Forecast API

- Documentation: https://open-meteo.com/en/docs
- Used for the short-term weather forecast displayed in the farm outlook (temperature, precipitation and related daily forecast values).
- Forecast values are provider model estimates and can change. They are not guaranteed observations.

### Open-Meteo Historical Weather API (reference / optional alternative)

- Documentation: https://open-meteo.com/en/docs/historical-weather-api
- Offers reanalysis history (ERA5 and ERA5-Land) and variables including temperature, humidity, precipitation, wind, soil temperature and soil moisture. This is documented as an alternative source for future cross-checking; the current farm-outlook historical feature pipeline uses NASA POWER, not this endpoint.

## 3. Mapped soil inputs

### ISRIC SoilGrids 2.0 via WCS

- Main information: https://isric.org/explore/soilgrids/
- WCS documentation: https://docs.isric.org/globaldata/soilgrids/wcs.html
- Units/conversion table: https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html
- Access/licence notes: https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html
- Used by the application to sample mapped 0–5 cm soil estimates near the saved farm coordinate. Properties include pH, sand, clay, silt, soil organic carbon, total nitrogen, CEC, bulk density, organic-carbon density and coarse fragments when the WCS service returns them.
- SoilGrids is a spatial prediction product (nominal 250 m maps) with uncertainty, not a substitute for a farm soil test. ISRIC currently recommends WCS/WebDAV because the beta REST API has been paused; this project uses WCS.
- SoilGrids product licence is CC BY 4.0. Follow ISRIC attribution requirements when redistributing maps or derived products.

**Important difference:** the SoilGrids `nitrogen` property is total soil nitrogen in g/kg after unit conversion. A Soil Health Card's available N/P/K values are different tests and commonly use kg/ha. Those values must not be substituted for the model's total-N feature without a scientifically validated conversion. This model currently uses mapped soil inputs; lab results are separately displayed as measured records.

## 4. Existing model datasets retained in this application

### Kolkata experimental sensor dataset

- File: `data/kolkata_unified_dataset.csv`
- 21,312 records from two experimental farm series at 15-minute intervals (Jan–Apr 2025), used by the existing 1-hour and 6-hour sensor-moisture models.
- It is experimental data from two Kolkata farm series. Do not represent it as a national Indian farm dataset or apply it as a calibrated model for every location.

### Government district crop statistics upload

The application also accepts the official-style district crop-production CSV for local historical summaries and district crop trends. Its supplied source unit is area in hectares and production in tonnes. That source-native unit is retained in district-level historical tables so published values are not silently altered.

## 5. Additional official rainfall dataset for future cross-checking

- India Meteorological Department, Pune, 0.25° daily gridded rainfall: https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html
- IMD page describes daily gridded rainfall from 1901 onward (latest page metadata should be checked before a research release).
- It is identified as a valuable India-focused rainfall benchmark. It is not currently auto-downloaded by this project's first-run dataset script. The app's current live historical climate features use NASA POWER.

## 6. What is and is not predicted

| Output | Source and scope | Correct interpretation |
|---|---|---|
| 7-day weather | Open-Meteo forecast | Provider weather forecast for the saved coordinate |
| Historical climate | NASA POWER daily | Gridded historical climate summary near the coordinate |
| Mapped soil | SoilGrids WCS 0–5 cm | Regional mapped soil estimates, not a lab test |
| Root-zone moisture | Regional model using historical NASA POWER root-zone/weather series, where data coverage/freshness checks pass | Location-scale estimate; not a direct probe reading |
| Historical crop pattern | India district crop/soil/climate model after one-time download/training | Ranked historically dominant district crops for similar inputs; not suitability/yield/profit |
| 1 h / 6 h moisture | Kolkata experimental models | Experimental sensor model limited to its two training farm series |
| District crop trends | Official CSV uploaded by user or explicitly labelled synthetic demo CSV | District history and baseline, not individual farm yield |

A crop-specific yield prediction for an individual farm is **not** claimed by this version. A separate yield model would need a matched and validated target dataset plus compatible farm-level inputs; district fertilizer application rates or taxonomic soil proxies must not be treated as measured farm Soil Health Card values.

### Additional yield-data sources reviewed, not silently mixed into this model

- Cornell Tata-Cornell Institute / ICRISAT District-Level Database for Indian Agriculture and Allied Sectors: https://tci.cornell.edu/data/ . It provides open district-level socioeconomic, environmental, nutrition and agriculture data for 571 districts in 20 states over 1966–2017. It is a useful source for future district-level yield/context research, but it is not a substitute for plot-level trial or farm-management data.
- A community-assembled India crop-yield panel (198,369 district × year × crop records, 1966–2017): https://github.com/sid09008mane/crop-yield . Its README describes multiple source components and features such as applied fertilizer rates and soil-taxonomy/pH proxies. These do not reliably match an individual farmer's measured Soil Health Card N/P/K values, and the assembled source/licensing and feature provenance need independent audit before use. It is therefore documented for review only and is **not** included in this application's current training pipeline.

### What is physically in the project ZIP versus fetched online

- Bundled locally: the Kolkata two-farm experimental sensor CSV, the clearly labelled synthetic demo crop-statistics CSV, existing trained experimental models, the source/preparation script and this provenance guide.
- Fetched on first setup: the approximately 23 MB India district crop/soil/climate CSV from the repository above. The ZIP includes a downloader and trainer; the raw file itself is not embedded. This avoids presenting a missing or synthetic file as real public data. A working internet connection is required for the one-time download.
- Queried by location when a farm outlook runs: NASA POWER daily history, SoilGrids WCS soil estimates and Open-Meteo forecast. These are retrieved live and cached; they are not static files bundled in the ZIP.

## 7. Farm area units

- All farmer and field-team farm/plot area entry and display uses **square feet (sq ft)**.
- The database stores the equivalent value in hectares internally to preserve compatibility with existing records and schema; the user interface converts values at the API boundary.
- Conversion: `1 hectare = 107,639.104167 sq ft`.
- Government district crop-statistics source fields remain in hectares because that is the original source unit; tables must explicitly label them as district statistics in hectares, not the farmer's farm size.
- Soil nutrient, rainfall, depth and yield units remain their scientific/source units (for example kg/ha, mm, cm and tonnes) and are not converted to square feet.
