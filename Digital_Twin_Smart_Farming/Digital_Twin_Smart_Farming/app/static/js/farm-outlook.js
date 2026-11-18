(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = { farms: [], lastFarmId: null, busy: false, loadToken: 0 };
  const esc = (value) => String(value ?? "—").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const number = (value, digits = 1) => value === null || value === undefined || !Number.isFinite(Number(value)) ? "—" : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
  async function requestJSON(url, options = {}) {
    const response = await fetch(url, { credentials: "same-origin", ...options });
    let payload;
    try { payload = await response.json(); } catch (_) { throw new Error(`The server returned an unreadable response (${response.status}).`); }
    if (!response.ok || payload.ok === false) throw new Error(payload.error || `Request failed (${response.status}).`);
    return payload;
  }
  function status(message, error = false) {
    const el = $("farm-outlook-status");
    if (!el) return;
    el.textContent = message;
    el.classList.toggle("is-error", error);
    el.classList.toggle("is-success", Boolean(message) && !error);
  }
  function metric(label, value, unit, hint) {
    return `<article class="farm-outlook-metric"><span>${esc(label)}</span><strong>${esc(value)}${unit ? `<small>${esc(unit)}</small>` : ""}</strong><em>${esc(hint || "")}</em></article>`;
  }
  async function loadFarms() {
    const token = ++state.loadToken;
    const select = $("farm-outlook-select");
    select.innerHTML = '<option value="">Refreshing your saved farms…</option>';
    status("Checking your saved farms and preparing the latest forecast…");
    const data = await requestJSON("/api/virtual-farms");
    if (token !== state.loadToken) return;
    state.farms = data.farms || [];
    select.innerHTML = "";
    if (!state.farms.length) {
      select.innerHTML = '<option value="">No farm saved yet</option>';
      $("farm-outlook-result").classList.add("hidden");
      status("No virtual farm is linked to this account yet. First use My Area to find your village, then My Farm to save the farm location and fields.", true);
      return;
    }
    state.farms.forEach((farm) => {
      const option = document.createElement("option");
      option.value = farm.virtual_farm_id;
      const demo = String(farm.farm_name || "").toUpperCase().includes("DEMO ONLY");
      option.textContent = `${farm.farm_name || "My farm"} · ${[farm.village, farm.district, farm.state].filter(Boolean).join(", ")}${demo ? " (synthetic demo)" : ""}`;
      select.appendChild(option);
    });
    const preferred = state.farms.find((farm) => String(farm.virtual_farm_id) === String(state.lastFarmId));
    // Farms are returned most-recently-updated first. Choose the latest farm
    // automatically so users see an outlook without hunting through controls.
    const selected = preferred || state.farms[0];
    select.value = String(selected.virtual_farm_id);
    state.lastFarmId = String(selected.virtual_farm_id);
    await generateOutlook();
  }
  function renderWeather(days) {
    const rows = days || [];
    $("farm-outlook-weather-rows").innerHTML = rows.map((day) => `<tr><td>${esc(day.date)}</td><td>${number(day.min_temp_c)}</td><td>${number(day.max_temp_c)}</td><td>${number(day.precipitation_mm)}</td><td>${day.precipitation_probability_pct == null ? "—" : `${esc(day.precipitation_probability_pct)}%`}</td><td>${number(day.et0_mm)}</td></tr>`).join("") || '<tr><td colspan="6">No forecast days were returned.</td></tr>';
    if (window.Plotly && $("farm-outlook-weather-chart")) {
      Plotly.react("farm-outlook-weather-chart", [
        { x: rows.map(x => x.date), y: rows.map(x => x.max_temp_c), type: "scatter", mode: "lines+markers", name: "Max temperature °C", yaxis: "y", line: { color: "#cf8541", width: 2 } },
        { x: rows.map(x => x.date), y: rows.map(x => x.precipitation_mm), type: "bar", name: "Rain mm", yaxis: "y2", marker: { color: "#6ca9c9", opacity: .65 } }
      ], { margin: { l: 42, r: 45, t: 12, b: 38 }, paper_bgcolor: "#fff", plot_bgcolor: "#fff", font: { size: 11, color: "#53675b" }, legend: { orientation: "h", y: 1.16 }, xaxis: { gridcolor: "#edf2ed" }, yaxis: { title: "Temperature °C", gridcolor: "#edf2ed" }, yaxis2: { title: "Rain mm", overlaying: "y", side: "right", showgrid: false } }, { responsive: true, displayModeBar: false });
    }
  }
  function renderMoisture(prediction) {
    const node = $("farm-outlook-model-summary");
    const chart = $("farm-outlook-moisture-chart");
    if (prediction && prediction.status === "available" && (prediction.forecasts || []).length) {
      const scores = prediction.validation_metrics || {};
      const scoreRows = Object.entries(scores).map(([name, item]) => `<tr><td>${esc(name)}</td><td>${number(item.mae, 4)}</td><td>${number(item.rmse, 4)}</td><td>${number(item.r2, 3)}</td></tr>`).join("");
      const forecasts = prediction.forecasts || [];
      node.innerHTML = `<div class="farm-outlook-model-badges"><span>Selected model: <b>${esc(prediction.selected_model)}</b></span><span>Last observed: <b>${esc(prediction.latest_observation_date)}</b></span><span>History: <b>${number(prediction.aligned_daily_records, 0)} days</b></span></div><div class="table-wrap"><table class="region-table"><thead><tr><th>Validation model</th><th>MAE</th><th>RMSE</th><th>R²</th></tr></thead><tbody>${scoreRows || '<tr><td colspan="4">Validation scores unavailable.</td></tr>'}</tbody></table></div>`;
      if (window.Plotly && chart) {
        Plotly.react(chart, [{ x: forecasts.map(x => x.date), y: forecasts.map(x => x.predicted_volumetric_percent), type: "scatter", mode: "lines+markers", name: "Regional root-zone estimate", line: { color: "#31835a", width: 3 }, marker: { size: 7 }, hovertemplate: "%{x}<br>%{y:.2f}%<extra>Regional model</extra>" }], { margin: { l: 48, r: 15, t: 12, b: 38 }, paper_bgcolor: "#fff", plot_bgcolor: "#fff", font: { size: 11, color: "#53675b" }, xaxis: { title: "Forecast date", gridcolor: "#edf2ed" }, yaxis: { title: prediction.target_name === "RZMC" ? "Volumetric moisture (%)" : "Relative root-zone wetness (%)", gridcolor: "#edf2ed" } }, { responsive: true, displayModeBar: false });
      }
      $("farm-outlook-model-note").textContent = `${prediction.interpretation || "Regional grid estimate only."} Validation is one-day-ahead chronological holdout; the multi-day forecast is recursive and its cumulative error is not independently validated.`;
    } else {
      node.innerHTML = `<div class="farm-outlook-unavailable"><strong>Location-specific root-zone prediction is not available right now.</strong><p>${esc(prediction?.reason || "The NASA POWER historical series did not pass data-coverage or freshness checks for this location.")}</p><p>You can still use the live weather forecast, SoilGrids context, district crop history and the virtual-farm record.</p></div>`;
      if (window.Plotly && chart) Plotly.purge(chart);
      $("farm-outlook-model-note").textContent = "The application does not substitute the Kolkata experimental sensor model for a farm in another region.";
    }
  }
  function renderCrop(crops) {
    const history = $("farm-outlook-crop-history");
    const projection = $("farm-outlook-crop-projections");
    if (!crops || !crops.available) {
      history.innerHTML = `<p class="muted">${esc(crops?.message || "District crop history is not available for this district yet.")}</p><p class="chart-note">Load the clearly labelled synthetic Sehore/Pune sample for a presentation, or import a verified Government of India district crop-production CSV in My Area.</p>`;
      projection.innerHTML = "";
      return;
    }
    const type = crops.data_type === "synthetic_demo" ? "SYNTHETIC PRESENTATION DATA" : crops.data_type === "uploaded" ? "UPLOADED DATA · ORIGIN NOT VERIFIED BY APP" : "PROVENANCE TO BE CHECKED";
    const rows = crops.crops || [];
    history.innerHTML = `<p class="chart-note">${esc(crops.district)}, ${esc(crops.state)} · ${esc(crops.period)}</p><span class="farm-outlook-provenance-pill ${crops.data_type === "synthetic_demo" ? "is-demo" : ""}">${type}</span><div class="table-wrap"><table class="region-table"><thead><tr><th>Crop</th><th>Seasons</th><th>District area (source unit: ha)</th><th>Mean annual production (t)</th></tr></thead><tbody>${rows.map(x => `<tr><td><b>${esc(x.crop)}</b></td><td>${esc((x.seasons || []).join(", "))}</td><td>${number(x.mean_annual_area_ha)}</td><td>${number(x.mean_annual_production_t)}</td></tr>`).join("")}</tbody></table></div><p class="chart-note">${esc(crops.message || "Historical district cropping pattern; not a farm-specific recommendation.")}</p>`;
    const projections = crops.trend_projections || [];
    projection.innerHTML = projections.length ? `<h3 class="farm-outlook-subhead">District historical trend baseline · ${esc(projections[0].target_year)}</h3><div class="table-wrap"><table class="region-table"><thead><tr><th>Crop</th><th>District trend area (source unit: ha)</th><th>Trend production (t)</th><th>Years used</th></tr></thead><tbody>${projections.map(x => `<tr><td>${esc(x.crop)}</td><td>${number(x.area_ha)}</td><td>${number(x.production_t)}</td><td>${esc((x.years_used || []).join(", "))}</td></tr>`).join("")}</tbody></table></div><p class="chart-note">${esc(crops.trend_note || "District trend baseline only; not an individual farm yield prediction.")}</p>` : `<p class="chart-note">At least three annual records per crop are required before a district trend baseline is shown.</p>`;
  }
  function renderCropModel(prediction) {
    const node = $("farm-outlook-crop-model");
    if (!node) return;
    if (prediction?.status === "available") {
      const items = prediction.top_historical_crops || [];
      const metrics = prediction.validation || {};
      const repo = prediction.source_repository_url || "https://github.com/priyanshupriyank04/india-district-crop-dataset";
      node.innerHTML = `<div class="farm-outlook-crop-ranking">${items.map((item, index) => `<article class="farm-outlook-crop-rank"><span>${index + 1}</span><div><strong>${esc(item.crop)}</strong><small>Historical model vote share · Not a suitability score</small></div><b>${number(item.model_vote_share_pct ?? item.similarity_probability_pct, 1)}%</b></article>`).join("")}</div><p class="chart-note">Season: ${esc(prediction.season)} · Training records: ${number(prediction.training_rows, 0)} across ${number(prediction.training_districts, 0)} districts · Crop classes: ${number(prediction.crop_classes, 0)}</p><p class="chart-note">District-grouped 5-fold validation: mean accuracy ${number(metrics.mean_accuracy, 3)}; macro-F1 ${number(metrics.mean_macro_f1, 3)}. The displayed percentages are uncalibrated classifier vote shares used to rank classes, not success probabilities. Grouped validation metrics are not confidence that a crop will succeed on this farm.</p><p class="chart-note">${esc(prediction.reason || "")}</p><div class="farm-outlook-source-links"><a href="${esc(repo)}" target="_blank" rel="noopener">Dataset & methodology source ↗</a></div><p class="chart-note">Dataset licence: ${esc(prediction.license || "CC BY 4.0")}. Cite the source repository and its original government, SoilGrids and NASA POWER components.</p>`;
      return;
    }
    const command = prediction?.prepare_command || "docker compose exec web python /app/scripts/prepare_india_crop_model.py";
    const reason = prediction?.reason || "The model needs its open Indian crop/soil/climate dataset to be downloaded and prepared once.";
    const repo = prediction?.source_dataset_url || "https://github.com/priyanshupriyank04/india-district-crop-dataset";
    node.innerHTML = `<div class="farm-outlook-unavailable"><strong>Indian crop-pattern model is not ready yet.</strong><p>${esc(reason)}</p><p>Run this one-time command in the project Terminal while Docker is running:</p><pre class="command-copy">${esc(command)}</pre><p class="chart-note">The download is about 23 MB. It is stored in data/regional so it remains after a web-container rebuild.</p><div class="farm-outlook-source-links"><a href="${esc(repo)}" target="_blank" rel="noopener">Dataset & methodology source ↗</a></div><p class="chart-note">Dataset licence: ${esc(prediction?.license || "CC BY 4.0")}. District-level history only; not farm-specific suitability or yield.</p></div>`;
  }

  function renderProblems(region) {
    const report = region.regional_problem_report || {};
    const challenges = report.documented_challenges || [];
    const signals = report.current_signals || [];
    const actions = region.next_actions || [];
    const items = [...signals.map(x => ({ level: x.level || "Watch", title: x.title, detail: `${x.evidence || ""} ${x.response || ""}` })), ...actions.map(x => ({ level: x.level || "Review", title: x.title, detail: x.detail || x.response || "Discuss this point with the local agriculture officer." }))];
    $("farm-outlook-problems").innerHTML = challenges.length ? challenges.map(x => `<article class="region-problem-card"><div class="region-problem-meta"><span class="region-problem-category">${esc(x.category || "Regional challenge")}</span><span class="region-problem-scope">${esc(x.evidence_scope || "Regional")}</span></div><strong>${esc(x.problem)}</strong><p>${esc(x.response)}</p><p class="region-problem-verify"><b>Verify:</b> ${esc(x.verify)}</p></article>`).join("") : '<p class="muted">No curated regional challenge profile was matched. Ask the local agriculture officer to verify field conditions.</p>';
    $("farm-outlook-actions").innerHTML = items.length ? items.map(x => `<article class="region-action"><span class="region-action-level">${esc(x.level)}</span><div><strong>${esc(x.title)}</strong><p>${esc(x.detail)}</p></div></article>`).join("") : '<p class="muted">No additional regional screening signal was returned.</p>';
  }
  function renderSoil(sample, soil) {
    const node = $("farm-outlook-lab-record");
    if (sample) {
      const fields = [["pH", sample.soil_ph, ""], ["EC", sample.soil_ec_ds_m, "dS/m"], ["Organic carbon", sample.organic_carbon_pct, "%"], ["Available N", sample.available_n_kg_ha, "kg/ha"], ["Available P", sample.available_p_kg_ha, "kg/ha"], ["Available K", sample.available_k_kg_ha, "kg/ha"]];
      node.innerHTML = `<span class="farm-outlook-provenance-pill">LAB VERIFIED RECORD</span><p><b>${esc(sample.sample_code)}</b> · ${esc(sample.lab_name || "Laboratory not recorded")} · ${esc(sample.tested_at || "Date not recorded")}</p><div class="farm-outlook-soil-grid">${fields.map(x => metric(x[0], number(x[1], 2), x[2], "Laboratory measurement")).join("")}</div><p class="chart-note">This is the latest linked record marked laboratory-verified in this prototype.</p>`;
    } else {
      const status = soil?.status === "available" ? "Mapped SoilGrids estimates are available for this area, but they are not a field test." : "No lab-verified soil sample is linked to this farm yet.";
      node.innerHTML = `<p>${esc(status)}</p><p class="chart-note">Ask the field team to collect a representative soil sample and assign it to an authorised laboratory. Do not treat mapped soil estimates as measured farm values.</p>`;
    }
  }
  function renderSources(region, response) {
    const sources = response.sources || {};
    const items = Object.entries(sources).filter(([, value]) => typeof value === "string" && value.startsWith("http"));
    const notes = region.data_notes || [];
    const errors = response.source_errors || [];
    const errorBlock = errors.length ? `<div class="farm-outlook-unavailable"><b>Some regional providers were unavailable:</b><ul>${errors.map(item => `<li>${esc(item.source)}: ${esc(item.reason)}</li>`).join("")}</ul></div>` : "";
    $("farm-outlook-sources").innerHTML = `${errorBlock}${items.map(([key, url]) => `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(key.replaceAll("_", " "))}</a>`).join(" · ")}<ul>${notes.map(note => `<li>${esc(note)}</li>`).join("")}</ul>`;
  }
  function render(data) {
    const farm = data.farm || {};
    const region = data.region || {};
    const climate = region.climate || {};
    const weather = region.weather_forecast || {};
    const soil = region.soil || {};
    $("farm-outlook-result").classList.remove("hidden");
    $("farm-outlook-name").textContent = farm.farm_name || "Selected farm";
    $("farm-outlook-location").textContent = [farm.village, farm.district, farm.state, farm.country].filter(Boolean).join(", ") + ` · ${number(farm.latitude, 4)}, ${number(farm.longitude, 4)}`;
    const isDemo = String(farm.farm_name || "").toUpperCase().includes("DEMO ONLY");
    $("farm-outlook-provenance").textContent = isDemo ? "Synthetic demo farm" : "Saved farm location";
    $("farm-outlook-metrics").innerHTML = [
      metric("Mean air temperature", climate.mean_air_temperature_c, "°C", `NASA POWER · ${climate.period || "historical"}`),
      metric("Mean annual rainfall", climate.mean_annual_rainfall_mm, "mm", "Gridded climate average"),
      metric("7-day forecast rain", weather.total_precipitation_mm, "mm", "Open-Meteo forecast"),
      metric("Mapped soil texture", soil.texture_group_screening || "Unavailable", "", "SoilGrids screening estimate")
    ].join("");
    renderMoisture(region.regional_prediction || {});
    renderWeather(weather.daily || []);
    renderCrop(region.crop_pattern || {});
    renderCropModel(region.crop_pattern_prediction || {});
    renderProblems(region);
    renderSoil(data.verified_soil_sample, soil);
    renderSources(region, region);
    const plots = (farm.plots || []).map(x => `${x.plot_name || "Plot"}: ${x.crop_name || "Crop not set"} (${number(x.area_sqft, 0)} sq ft)`).join(" · ");
    status(`Outlook ready. ${plots ? `Farm plots: ${plots}. ` : "No mapped crop plots have been added yet. "}Check the data labels before using any information for field decisions.`);
  }
  async function generateOutlook() {
    if (state.busy) return;
    const farmId = $("farm-outlook-select").value;
    if (!farmId) { status("Choose or create a saved virtual farm first.", true); return; }
    state.busy = true;
    const button = $("farm-outlook-run");
    button.disabled = true;
    button.textContent = "Checking location data…";
    $("farm-outlook-result").classList.add("hidden");
    status("Loading historical climate, 7-day weather, mapped soil, district crop data and the regional prediction model. This may take a little while on the first request.");
    try {
      const data = await requestJSON(`/api/virtual-farms/${encodeURIComponent(farmId)}/outlook`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ season: $("farm-outlook-season")?.value || "Kharif" }) });
      render(data);
      state.lastFarmId = String(farmId);
    } catch (error) {
      status(`${error.message} You can still open My Area to run location analysis separately.`, true);
    } finally {
      state.busy = false;
      button.disabled = false;
      button.textContent = "Generate farm outlook →";
    }
  }
  const runButton = $("farm-outlook-run");
  if (runButton) runButton.addEventListener("click", generateOutlook);
  const select = $("farm-outlook-select");
  if (select) select.addEventListener("change", () => {
    state.lastFarmId = String(select.value || "");
    generateOutlook();
  });
  window.addEventListener("virtual-farm-saved", (event) => {
    if (event.detail?.farmId) state.lastFarmId = String(event.detail.farmId);
  });
  window.addEventListener("farmer-view-shown", (event) => {
    if (event.detail === "outlook") loadFarms().catch(error => status(error.message, true));
  });
  window.appAuthReady?.then((user) => { if (user && document.querySelector('[data-app-view="outlook"]')?.classList.contains("is-active")) loadFarms().catch(error => status(error.message, true)); });
})();
