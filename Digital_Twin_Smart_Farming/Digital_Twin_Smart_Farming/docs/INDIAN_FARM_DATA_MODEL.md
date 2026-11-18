# Indian Farm Digital Twin — Data Model

## Purpose

The virtual farm is represented as a geographic site with separately mapped plots and point infrastructure. It is not the same entity as the two Kolkata EcoIrrigate experimental dataset farms. The latter remain a research-data demonstration; a farmer/student creates a new Indian virtual farm from a selected village, town or district.

## Entity hierarchy

```text
Indian location (village / district / state / coordinates)
  └── Virtual farm site
        ├── Outer farm boundary (GeoJSON Polygon)
        ├── Regional climate snapshot (source + period + metrics)
        ├── Regional soil-map snapshot (source + depth + resolution)
        ├── Candidate agro-climatic region (Planning Commission 15-region scheme)
        ├── Regional crop-history snapshot (optional India OGD CSV)
        ├── Plot / field A (GeoJSON Polygon)
        │     ├── Crop and variety
        │     ├── Kharif / Rabi / Zaid / perennial season
        │     ├── Sowing date and growth stage
        │     ├── Indian broad soil group and field texture
        │     ├── Soil Health Card / lab-test values
        │     ├── Irrigation method and water source
        │     └── Field notes
        ├── Plot / field B ...
        └── Infrastructure points
              ├── Borewell / open well
              ├── Pond / tank
              ├── Pump / solar pump
              ├── Channel / drainage
              ├── Farm building / cattle shed / storage
              └── Other mapped asset
```

## MySQL tables

### `virtual_farms`

One record per user-defined farm. Stores farm name, village, district, state, coordinates, declared area, selected agro-climatic region, farming system, landform, water source, primary irrigation method, outer-boundary GeoJSON, and JSON snapshots of regional climate, mapped soil, Indian context and data provenance.

### `virtual_farm_plots`

One record per field/plot. Stores its polygon, user-confirmed area, crop/variety, Indian crop season, sowing date, crop stage, Indian broad soil group, soil texture, irrigation and water source. Optional pH, EC, organic carbon and available N/P/K values must come from a Soil Health Card or laboratory report; the app stores the source and test date.

### `virtual_farm_assets`

Stores point locations of farm infrastructure assets such as wells, ponds, tanks, pumps, channels, farm buildings and storage.

## What is measured, mapped, entered or inferred?

| Data | Origin | Interpretation |
|---|---|---|
| Farm and plot boundaries | User-drawn GeoJSON on OpenStreetMap | Approximate digital geometry; not cadastral/legal survey |
| Farm area and plot area | User-entered; map polygon can show an approximate geometry area | Must be confirmed by farmer/survey record |
| Climate history | NASA POWER at selected Indian coordinate | Gridded/reanalysis estimate, not farm-gate weather-station reading |
| Short weather forecast | Open-Meteo forecast at selected coordinate | Model forecast; not a guarantee |
| Mapped soil properties | ISRIC SoilGrids point/neighbourhood sample | Modelled regional estimate; not a field sample |
| District crop pattern | Government of India OGD CSV uploaded by user | Historical district-level recorded cultivation, not plot suitability |
| Agro-climatic region | Candidate mapping from state to the Planning Commission's 15 regions | Must be checked against district/sub-district GIS or local expert guidance |
| Plot soil fertility | Farmer enters values from Soil Health Card/lab report | Actual report values if entered accurately; not auto-filled from SoilGrids |
| Crop and season | User entry, with district historical crops offered as hints | Not automatically inferred from the village name |

## India-specific assumptions and guardrails

- The 15 Planning Commission agro-climatic regions are used as a national framework. Some states span multiple regions. A state match therefore supplies candidate zones, not a definitive spatial classification.
- The application uses Indian season names: Kharif, Rabi, Zaid and perennial. Month ranges and crop examples are broad national descriptions. Local sowing and harvest dates vary with district, crop, variety, monsoon onset, irrigation and local recommendations.
- Broad Indian soil groups are selectable for the plot. Soil taxonomy and actual field texture should be confirmed with ICAR/state soil maps or laboratory analysis.
- Total nitrogen in SoilGrids is not plant-available nitrogen. It must not be substituted for the available N result in a Soil Health Card.
- Fertilizer dose, crop suitability, irrigation volume and yield prediction are not derived from a regional mean alone. Those functions require field test data, crop/stage-specific methods, local agronomic validation and, where needed, an agricultural expert.

## References for the Indian context

1. Planning Commission, Government of India, *Agro-Climatic Regional Planning Project*. NITI Digital Library: https://digitallibrary.niti.gov.in/items/05085f17-672c-45d0-91b4-fdc09b7395b5
2. Ministry of Panchayati Raj, *RADPFI Guidelines* (2021), Appendix 3.2: Agro-climatic Regions/Zones in India. https://cdnbbsr.s3waas.gov.in/s316026d60ff9b54410b3435b403afd226/uploads/2023/02/2023022142.pdf
3. Government of India, *Agricultural Statistics at a Glance 2024–25*, crop calendar of major crops. https://nccd.gov.in/uploads/Agricultural_Statisitcs_at_a_Glance_2024_25_11da3cd37d.pdf
4. ICAR–NBSS&LUP, soil resource maps and publications. https://icar-nbsslup.org.in/
5. Government of India, Soil Health Card Portal. https://soilhealth.dac.gov.in/
