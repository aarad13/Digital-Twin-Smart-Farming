# Farm predictions, regional data and virtual farm guide

This application has several distinct types of output. They must not be treated as interchangeable.

## 1. Location / regional intelligence

1. Sign in.
2. Open **My area**.
3. Search for a village, town or district in India.
4. Choose the matching location and run the analysis.
5. Review the regional climate, forecast weather, mapped soil context, agro-climatic region candidates, Indian crop seasons, district crop history and regional problem screening.
6. Choose **Create my farm from this area** to carry the selected coordinates and available regional context into the virtual farm form.

The regional services use Open-Meteo geocoding and forecast, NASA POWER daily climate, ISRIC SoilGrids mapped soil properties, Indian agro-climatic context and a district crop CSV when one is present. Regional weather and mapped soil are grid/provider estimates, not measurements made on the farm.

## 2. District crop dataset

The platform can import the Government of India's district-wise, season-wise crop production CSV. The expected normalized fields are state, district, crop year, season, crop, area and production. In **My area**, an authorised field-team user can open the optional advanced import section and upload the CSV downloaded from the official OGD catalogue:

https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0

The application shows the file's provenance label. An uploaded CSV is marked as uploaded, not independently verified by this application. District crop-history and trend baselines show historical recorded area and production; they are not individual-farm yield or crop-suitability predictions.

For a presentation, the seed script can load a small fictional Sehore/Pune dataset. It is explicitly marked **synthetic demo data—not official Government statistics** and must never be used for agronomic decisions. An already uploaded crop dataset is preserved by the seed script.

## 3. My farm / virtual farm

1. Open **My farm**.
2. Select the farm if one already exists, or first analyse a location in **My area**.
3. Create the farm using its location, state, district and area.
4. Confirm the suggested agro-climatic zone with a local agriculture officer if uncertain.
5. Draw and save the outer farm boundary on the map.
6. Draw individual plot boundaries inside the farm, then enter crop, variety, season, crop stage, irrigation and field-tested soil results where available.
7. Add wells, ponds, tanks, pumps, channels and other infrastructure inside the saved boundary.
8. Upload the Soil Health Card or laboratory report. Uploading a document does not by itself mean the values have been extracted or laboratory-verified; authorised lab staff must enter and verify measured results.

## 4. Farm predictions

Open **Farm predictions**. The application refreshes the farms linked to the signed-in account, selects the most recently updated farm by default and runs its outlook. Select another saved farm to run that farm's outlook.

The page presents:

- **Seven-day weather forecast:** forecast temperature, rainfall, rain probability, and reference evapotranspiration for the saved farm coordinates from Open-Meteo.
- **Regional root-zone soil-moisture forecast:** an ML/regression forecast using NASA POWER historical weather and Hydrology-community root-zone moisture when sufficient daily overlap exists. The series must have at least 500 aligned daily records, a current moisture observation no more than 14 days old, and complete recent inputs. A chronological holdout compares persistence, Ridge and Random Forest; the learned model is selected only if it beats persistence on holdout RMSE. The seven-day path is recursive and grid-point scale, not plot-sensor truth.
- **District crop history and trend baseline:** based on the loaded district crop CSV. This is not a farm-level yield forecast.
- **Regional checks and next steps:** screening signals based on available regional weather, soil-map and curated state/zone profile data. These must be checked by a local agronomist or field officer.
- **Latest linked lab-verified soil test:** if a sample has been linked to the farm and marked verified by the authorised lab.

If the root-zone model cannot run because data is missing, stale or an external provider is unavailable, the page displays the reason and keeps the weather, regional and crop-history panels available where their sources responded. The application does not fabricate a soil-moisture forecast.

## 5. Reports & research (separate experimental model)

Open **Predictions & research** to run the bundled EcoIrrigate model using its two experimental Kolkata farm time series. The research page supports 1-hour and 6-hour moisture forecasts and model comparisons. This dataset has 15-minute observations from two Kolkata experimental farms only. It is not automatically transferred to the user's Indian virtual farm and must not be presented as a generalized all-India model.

## 6. If a page appears empty

- Sign in with an account linked to a farmer/farm record.
- Open **My farm** and confirm a saved virtual farm exists.
- Open **Farm predictions**; it should automatically choose the newest saved farm. If multiple farms exist, use the selector to change farms.
- For district crop rows, run the demo seed once for presentation data or import a verified OGD CSV.
- Check Docker logs with `docker compose logs --tail=100 web` if an API request or database route fails.
- Hard-refresh the browser with **Command + Shift + R** after updating the project.

Do not use `docker compose down -v`; it can remove the database volume. Preserve `.env`, `uploads/`, and any real uploaded `data/regional/crop_production.csv` when updating the project.
