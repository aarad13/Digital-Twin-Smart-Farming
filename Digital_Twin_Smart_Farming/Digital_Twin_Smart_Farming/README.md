# Digital Twin for Smart Farming

A farmer-first, institution-assisted digital twin for Indian farms. A farmer can use the simple view directly, while government/KVK extension staff, FPOs, agriculture-company field teams and authorised soil laboratories can help capture records and explain results. The system combines farm maps, location intelligence, soil reports, weather, district crop history and clearly scoped predictions.

## Start on MacBook Air M2

Install Docker Desktop for Apple silicon, open this folder in VS Code, then run:

```bash
docker compose up --build -d
docker compose ps
```

Open http://127.0.0.1:5000. The MySQL database is persisted in a named Docker volume. Never use `docker compose down -v` unless you intentionally want to erase it.

## Make Indian crop-pattern predictions available (one-time)

The app includes a downloader and training pipeline for the public India District Crop Dataset (1997–2015). After the web and database services are healthy, run:

```bash
docker compose exec web python /app/scripts/prepare_india_crop_model.py
```

It downloads the approximately 23 MB CSV from the dataset's source repository, checks the expected feature columns, trains a Random Forest model with five-fold GroupKFold validation grouped by district, and saves the model plus a validation manifest in the persistent `data/regional/` folder. The first-time download requires internet access inside Docker. If that network request fails, the crop-pattern model remains marked unavailable; no synthetic data is substituted.

## Prediction types in the application

1. **7-day weather forecast:** Open-Meteo forecast for the saved farm coordinates.
2. **Historical climate context:** NASA POWER daily weather series for the saved coordinates.
3. **Mapped soil context:** ISRIC SoilGrids WCS topsoil estimates near the farm. These are gridded estimates, not farm soil-test measurements.
4. **Regional root-zone moisture forecast:** a point-specific model using NASA POWER root-zone and weather history, only when data freshness and coverage checks pass.
5. **India historical crop-pattern model:** ranks crops historically dominant in similar district-scale environmental records by season. It is not a farm-level suitability, yield, profit or planting prescription.
6. **Experimental 1-hour / 6-hour moisture forecasts:** existing models trained on two experimental Kolkata farm series; not calibrated for all Indian farms.
7. **District crop statistics:** historical district area and production summaries from an uploaded Government of India CSV or a clearly labelled synthetic presentation dataset.

## Public data and source attribution

For the simplest explanation, follow [`DATASETS_SIMPLE_GUIDE.md`](DATASETS_SIMPLE_GUIDE.md). For the one-time setup steps, see [`DATASET_SETUP_QUICKSTART.md`](DATASET_SETUP_QUICKSTART.md). [`DATASET_SOURCES_AND_PREDICTIONS.md`](DATASET_SOURCES_AND_PREDICTIONS.md) contains the full data dictionary, origins, licences, limitations and model interpretation. Main sources include:

- Government of India DES district-wise, season-wise crop-production statistics (area in hectares; production in tonnes).
- India District Crop Dataset 1997–2015, a derived CC BY 4.0 dataset combining government crop labels, SoilGrids soil properties, NASA POWER climate and district boundaries.
- NASA POWER daily historical climate and hydrology variables.
- Open-Meteo daily forecast API.
- ISRIC SoilGrids 2.0 accessed through WCS (CC BY 4.0).
- IMD 0.25° gridded rainfall is listed as a reference dataset for future cross-checking; the current live history pipeline uses NASA POWER.

The CSV download is executed on the user's Mac/Docker because the build environment used to package this project could not reach the external dataset host. The downloader is included; the raw 23 MB CSV is created locally by the one-time command above.

## Farm area units

All individual farm and plot sizes are entered and displayed in **square feet (sq ft)**. For reference, 1 acre = 43,560 sq ft. The existing MySQL schema stores the equivalent value in hectares internally to preserve compatibility with already-saved farms; the UI and API convert at the boundary. Government district-level crop statistics continue to show area in hectares because that is the unit published by the source dataset. This does not change the farmer's farm-size unit.

## Technology stack

- Frontend: HTML, CSS, JavaScript, Plotly.js
- Backend: Python, Flask
- Database: MySQL 8.4 with PyMySQL
- Data: Pandas, NumPy, Requests
- Machine learning: scikit-learn, joblib
- Maps: Leaflet and OpenStreetMap tiles
- Development: VS Code, Git/GitHub; Docker Compose for Mac/Windows/Linux

## Verification and limitations

Run automated tests with `python -m pytest -q` and project integrity checks with `python scripts/check_project.py --core-only`. The external data download, remote APIs and a live MySQL/Docker browser workflow still require a successful run on the user's machine. A lab report is stored separately from mapped soil; SoilGrids total nitrogen is not the same measurement as Soil Health Card plant-available N, P or K. No fertiliser prescription is generated from unverified values.

See `ASSISTED_VILLAGE_SERVICE_GUIDE.md`, `AUTH_AND_ACCESS_GUIDE.md`, `FARM_PREDICTIONS_AND_REGIONAL_DATA_GUIDE.md`, and `MACBOOK_AIR_M2_SETUP.md` for operations.
