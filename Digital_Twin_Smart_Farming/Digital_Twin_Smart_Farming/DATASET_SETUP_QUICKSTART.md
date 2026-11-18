# Prediction data setup — quick guide (Mac / Docker)

For a very plain-language list of datasets and their sources, see `DATASETS_SIMPLE_GUIDE.md`.

The app has one bundled experimental prediction dataset and one India historical crop-pattern dataset that is downloaded once. Weather and mapped soil are fetched for the farm location when you run a farm outlook.

## 1. Update the existing project safely

Back up the project folder first. Copy the new project files into the existing `Digital_Twin_Smart_Farming` folder. Keep your `.env`, `uploads/`, existing MySQL Docker volume, and any files already in `data/regional/`.

Do not run `docker compose down -v`.

## 2. Rebuild only the web app

From the project folder in Terminal:

```bash
unset APP_PORT MYSQL_PORT
docker compose up -d --build web
docker compose ps
```

Wait until `web` and `db` are healthy/running.

## 3. Download and train the India crop-pattern model (once)

```bash
docker compose exec web python /app/scripts/prepare_india_crop_model.py
```

This downloads the approximately 23 MB India District Crop Dataset (1997–2015), checks the columns, performs district-grouped 5-fold validation, and saves the CSV, model and source/metrics manifest in the persistent `data/regional/` folder. The ZIP includes this downloader/trainer and full attribution, but not the 23 MB raw CSV itself; the command fetches it from the source repository on your Mac/Docker. It needs internet access inside Docker. Re-run only when you intentionally want to retrain; use `--force-download` only to fetch a fresh copy.

## 4. Generate a farm outlook

1. Open `http://127.0.0.1:5000`.
2. Find the village and save the correct farm latitude/longitude in **My Area / My Farm**.
3. Open **Farm Predictions**, choose the saved farm and crop season, and press **Generate farm outlook**.
4. The app requests NASA POWER historical climate, SoilGrids mapped soil and Open-Meteo forecast data for that location. Those live sources need an internet connection.

## 5. Area units

Enter individual farm and plot sizes in **square feet (sq ft)**. One acre is **43,560 sq ft**. The database retains hectare equivalents internally so older farm records remain compatible. Government district crop tables stay in hectares because that is the source dataset's original unit; these are district statistics, not the farmer's registered farm size.

## Data sources in plain language

- India District Crop Dataset 1997–2015: historical crop actually grown most in each district/season, combined with district soil and climate features. Used for a historical pattern ranking, not a farm-level yield forecast or recommendation. CC BY 4.0 as stated by its repository.
- Government of India DES / data.gov.in: district crop area (hectares) and production (tonnes), also usable through the CSV import.
- NASA POWER: historical weather and land-surface time series at the farm coordinate.
- ISRIC SoilGrids 2.0: mapped soil-property estimates near the coordinate; not a laboratory result.
- Open-Meteo: short-range forecast weather.
- IMD 0.25° rainfall and Cornell/ICRISAT district agriculture data are documented as reference/future cross-checks, not active inputs in the current model.

See `DATASET_SOURCES_AND_PREDICTIONS.md` for source URLs, coverage, licensing, features and limitations. The browser also has a “Where do predictions and data come from?” section.
