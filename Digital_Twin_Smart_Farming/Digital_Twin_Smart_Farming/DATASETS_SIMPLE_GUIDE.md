# Smart Farming datasets — simple guide

This file explains the data used by the application in plain language.

## The one-time setup

Start Docker and the application first. Then run this **once** from the project folder:

```bash
docker compose exec web python /app/scripts/prepare_india_crop_model.py
```

This downloads the India district crop/soil/climate CSV (about 23 MB), checks it, trains the crop-pattern model and saves the data, model and validation report in `data/regional/`.

The download needs internet access inside Docker. If it fails, the application will tell you that the India crop-pattern model is not ready; it will not silently replace the public dataset with fake data.

## What data does the application use?

| Data | Where it comes from | What the application uses it for |
|---|---|---|
| Historical Indian crops, soil and climate (1997–2015) | India District Crop Dataset repository (link below), combining DES Government crop statistics, district boundaries, SoilGrids and NASA POWER | A season-specific ranking of crops that were historically most common in similar district conditions |
| District crop area and production | Government of India, Directorate of Economics & Statistics, data.gov.in | Historical crop patterns, district area and production summaries; CSV upload is available in My Area |
| Historical weather at the farm location | NASA POWER Daily API | Temperature, rainfall, humidity, wind and solar context near the saved farm coordinates |
| Upcoming weather | Open-Meteo Forecast API | The next seven days' forecast for the saved farm location |
| Mapped soil near the farm | ISRIC SoilGrids 2.0 (WCS) | Estimated pH, texture, organic carbon, total nitrogen and other mapped soil properties |
| Actual farm soil test | A farmer-provided Soil Health Card or laboratory report, entered/uploaded through the app | The farm's reported pH, EC, organic carbon and available N/P/K when laboratory staff enter and verify them |
| Experimental sensor readings | Bundled Kolkata experimental dataset | Existing 1-hour and 6-hour moisture research demonstrations only |

## Dataset source links

1. **India District Crop Dataset 1997–2015 (model training data)**  
   Repository: https://github.com/priyanshupriyank04/india-district-crop-dataset  
   Direct CSV: https://raw.githubusercontent.com/priyanshupriyank04/india-district-crop-dataset/main/data/final/india_district_crop_dataset_1997_2015.csv  
   Repository describes 34,903 rows, 48 columns, 652 districts, 34 States/UTs and six seasons. Its derived dataset licence is stated as CC BY 4.0. Credit this repository and the component sources below.

2. **Government of India crop production statistics**  
   Catalogue: https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0  
   Resource: https://www.data.gov.in/resource/district-wise-season-wise-crop-production-statistics-1997  
   Published by the Ministry of Agriculture and Farmers Welfare / Department of Agriculture and Farmers Welfare / Directorate of Economics & Statistics (DES). The source reports district/crop/season/year crop area in hectares and production in tonnes. Keep those units when showing district-level source data.

3. **NASA POWER daily weather and climate**  
   Documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/  
   Used for gridded historical climate at the saved farm coordinates. It is not a sensor placed in the field. NASA POWER data are public data; cite NASA POWER when using the resulting time series.

4. **ISRIC SoilGrids 2.0**  
   Main page: https://isric.org/explore/soilgrids/  
   WCS documentation: https://docs.isric.org/globaldata/soilgrids/wcs.html  
   Provides mapped global soil properties at approximately 250 m resolution and multiple depths. SoilGrids is CC BY 4.0. These are estimates, not a laboratory test.

5. **Open-Meteo forecast**  
   Documentation: https://open-meteo.com/en/docs  
   Used for the short-range forecast (temperature, rainfall and related daily values). Forecasts can change and are not guaranteed observations.

6. **India Meteorological Department (IMD) gridded rainfall — reference dataset**  
   https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html  
   Daily rainfall at 0.25° grid spacing is available for 1901–2024 on the source page. This is documented as an India-specific cross-check/reference; the current live history pipeline uses NASA POWER and does not automatically download the IMD NetCDF archive.

7. **ICAR-CRIDA district crop contingency plans**  
   https://www.icar-crida.res.in/Crop_Contingency_Plan.html  
   Used as a reference for region-specific agricultural risks and contingency planning. Local officers should verify whether a listed contingency applies to the actual field.

## What the predictions mean

- **7-day weather:** forecast for the saved farm coordinates.
- **Historical climate:** past gridded weather conditions near those coordinates.
- **Mapped soil:** regional soil estimates; not a measured sample from the farm.
- **Root-zone moisture:** a location-scale model output only when enough recent NASA POWER hydrology and weather data pass quality checks. It can be unavailable for some locations/times.
- **Historical crop-pattern ranking:** shows crops that historically dominated in similar district-season data. It is not a guarantee that a crop will succeed on this farm.
- **Kolkata 1-hour / 6-hour models:** experimental models trained on two Kolkata farm series only; they are not pan-India models.
- **Farm yield prediction:** a separate validated farm-level crop-yield model is not included. It would require reliable farm/plot yield history matched with crop, season, soil test, irrigation and management records. The application does not claim a yield forecast from district averages.

## Soil test versus mapped soil

SoilGrids total nitrogen is not the same as the available nitrogen measured on a Soil Health Card. SoilGrids does not provide a replacement for the complete Soil Health Card set (for example, available N/P/K, EC and micronutrients). A real field recommendation should use a representative soil sample and a verified laboratory report, with advice from the local KVK/agriculture officer.

## Farm area is in square feet

Enter individual farm and plot sizes in **square feet (sq ft)** throughout the application.

- 1 acre = 43,560 sq ft
- 1 hectare = 107,639.104167 sq ft

The MySQL database keeps hectare-equivalent values internally so older saved records remain compatible. The application converts at its input/output boundary. Government district crop statistics remain in hectares because that is how the official source publishes district-wide area; that does not change the farmer's own farm-area unit.

## Where files are saved

After the one-time download/training command, the CSV, model and validation manifest are saved under:

```text
data/regional/
```

Docker Compose mounts this folder from your Mac, so the downloaded files remain after rebuilding the web container. Do not delete this folder if you want to keep the downloaded dataset and trained model. Do not use `docker compose down -v` to update the application.
