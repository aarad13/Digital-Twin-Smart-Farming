# Regional prediction data

## One-time India crop-pattern training dataset

From the project root, with Docker running, execute:

```bash
docker compose exec web python /app/scripts/prepare_india_crop_model.py
```

The script downloads the openly licensed India District Crop Dataset (1997–2015), validates its feature schema, trains a district-grouped Random Forest classifier and saves the CSV, model and evaluation manifest in this folder. This folder is bind-mounted by Docker, so those files persist after a web-container rebuild. The CSV is approximately 23 MB and is fetched from the source on first use; it is not replaced with synthetic data if the network request fails.

Source repository: https://github.com/priyanshupriyank04/india-district-crop-dataset
CSV URL: https://raw.githubusercontent.com/priyanshupriyank04/india-district-crop-dataset/main/data/final/india_district_crop_dataset_1997_2015.csv
Licence stated by source: CC BY 4.0. Attribution to the repository and its Government of India DES, ISRIC SoilGrids and NASA POWER component sources is required.

## Live regional sources

- NASA POWER Daily API: historical weather and root-zone water variables.
- Open-Meteo Forecast API: short-range forecast.
- ISRIC SoilGrids WCS: mapped soil estimates; regional estimates are not soil-test results.
- Official Government of India district crop statistics: upload a CSV through Regional Intelligence to populate district historical area and production summaries. Published area is in hectares and production in tonnes.

## Other datasets retained

- `../kolkata_unified_dataset.csv`: experimental 15-minute soil-moisture observations for two Kolkata farm series. This powers the separate 1-hour and 6-hour experimental sensor models only. It is not a national farm dataset.
- `DEMO_CROP_STATISTICS_SYNTHETIC.csv`: clearly labelled synthetic demo records only. Never use them for real field recommendations or scientific validation.

Do not commit API caches, real farmer reports or credentials to a public repository.

## Additional reviewed yield data (not currently trained in the app)

The Cornell Tata-Cornell Institute / ICRISAT district database (https://tci.cornell.edu/data/) is an open historical district-level source for 571 districts in 20 states during 1966–2017. A community-assembled crop-yield panel (https://github.com/sid09008mane/crop-yield) also exists, but contains fertilizer-use and soil-taxonomy proxy variables that do not match individual Soil Health Card measurements. Neither source is silently merged into the current classifier. A farm-level yield model requires matched local yield outcomes and compatible management/soil inputs.

The approximately 23 MB India district crop, soil and climate CSV is downloaded by `prepare_india_crop_model.py` on first use; it is not physically embedded in the ZIP.
