# Live demo and presentation guide

## Important demo-data label
The preloaded presentation farm is named **DEMO ONLY - Sehore Learning Farm**. Its coordinates are approximate and its weather, soil and crop values are synthetic. It is not a real farmer, a live sensor feed, a government soil report or an agronomic recommendation. Do not use these values for field decisions.

## 1. Seed a complete village-service demonstration
With Docker Compose running, open a second terminal in the project directory and run:

```bash
docker compose exec web python scripts/seed_demo_data.py
```

The script is safe to rerun. It prepares:
- A clearly labelled **DEMO ONLY - Sehore Learning Farm** virtual farm.
- A synthetic farmer profile linked to that virtual farm.
- One synthetic soil sample marked **Verified** with an illustrative lab report attached.
- One synthetic soil sample marked **Collected** and awaiting laboratory testing.
- A synthetic completed field visit.

All people, sample codes, coordinates, soil readings, and lab details are invented for a presentation. They are not actual Sehore farm or laboratory data.

## 2. Demonstrate the assisted service workflow
1. **Village desk:** show registered farmer, pending sample, verified report and field visit counts.
2. **Field team:** register another demonstration farmer. Record consent, village, district, state, crop and optional GPS. Show how the field worker creates a sample code and QR code to place on the bag.
3. **Soil lab:** select `DEMO-SOIL-PENDING-001`, enter illustrative values only if you are explicitly showing the form, and explain that real values must come from an authorised test. Mark verified only for the synthetic presentation sample.
4. **Farmer card:** choose `DEMO ONLY - Sample Farmer`. Show the simple farm details, linked Digital Twin, lab verification badge, measured values, attached PDF and print/read-aloud options.
5. **Farm intelligence:** return to Village desk and open regional information, virtual farm map and experimental forecasts. Explain their data sources and limits.

The sample PDF is bundled at:

`data/demo/SAMPLE_SOIL_HEALTH_CARD_DEMO_ONLY.pdf`

The seeder copies it to the local uploads directory and links it to the synthetic verified sample so that the Farmer Card can open it.

## 3. Suggested 7-minute presentation flow
1. **Problem (45 sec):** many farmers need a human-assisted service; digital tools should support field workers and labs, not require every farmer to operate an app.
2. **Village desk (45 sec):** overview counts and partner workflow.
3. **Field visit (90 sec):** consent-aware farmer registration, GPS capture and unique sample ID/QR.
4. **Laboratory (90 sec):** sample queue, manually entered measured values, attached report and explicit lab verification.
5. **Farmer card (60 sec):** show verified values in plain language and print/read aloud.
6. **Digital Twin (60 sec):** show linked virtual farm map and regional context.
7. **Research (30 sec):** show the separate Kolkata experimental dataset and clarify its scope.

## 4. Integration status and roadmap
- Implemented: local field-team registration, consent recording, optional farm GPS, visit scheduling, QR sample code, lab result entry, report attachment, verification state and farmer card.
- Proposed, not connected: District Agriculture Offices, Soil Health Card system, KVKs, village soil testing labs, FPOs/cooperatives and fertiliser-company field teams.
- External API integration requires formal partner approval, API documentation, credentials and data-sharing/security agreements.
- Secure staff login, organisation-level access controls, offline sync, automatic OCR and full regional-language coverage remain future/production work.


## 5. Presentation safety
Use the sample PDF only as a clearly marked demonstration document. Never present the synthetic soil values, coordinates or regional snapshots as actual measurements. Ask the audience to imagine uploading their own Soil Health Card; for real use, enter only values from a verified laboratory or government report.
