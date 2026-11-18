const $ = (id) => document.getElementById(id);
let activeFarm = null;
let latestTrend = [];
let lastPredictions = [];

function showAlert(message) {
  const box = $("alert"); box.textContent = message; box.classList.remove("hidden");
}
function clearAlert() { $("alert").classList.add("hidden"); }
function num(value, digits=2) { return value === null || value === undefined ? "—" : Number(value).toFixed(digits); }
function dateText(value) { return value ? new Date(value.replace(" ", "T")).toLocaleString() : "—"; }
async function getJSON(url, options={}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

async function loadFarms() {
  const data = await getJSON("/api/farms");
  const select = $("farm-select"); select.innerHTML = "";
  data.farms.forEach(farm => {
    const option = document.createElement("option");
    option.value = farm.farm_code; option.textContent = farm.display_name;
    select.appendChild(option);
  });
  if (!data.farms.length) throw new Error("No farms found. Import the CSV dataset first.");
  activeFarm = select.value;
  await loadOverview(); await loadForecastHistory();
}

async function loadOverview() {
  if (!activeFarm) return;
  clearAlert();
  const data = await getJSON(`/api/overview?farm_code=${encodeURIComponent(activeFarm)}`);
  const latest = data.latest;
  latestTrend = data.trend;
  $("farm-location").textContent = data.farm.location || "Not specified";
  $("farm-crop").textContent = data.farm.crop_name || "Not configured";
  $("latest-time").textContent = dateText(latest.observed_at);
  $("observation-count").textContent = Number(data.observation_count).toLocaleString();
  $("metric-moisture").textContent = num(latest.moisture_pct);
  $("metric-air").textContent = num(latest.atmospheric_temp_c);
  $("metric-soil").textContent = num(latest.soil_temp_c);
  $("metric-pressure").textContent = num(latest.atmospheric_pressure_inhg);
  $("threshold-input").value = num(data.threshold_pct, 1);
  $("crop-input").value = data.farm.crop_name || "";
  $("soil-input").value = data.farm.soil_type || "";
  $("area-input").value = data.farm.field_area_ha ? Math.round(Number(data.farm.field_area_ha) * 107639.104167) : "";
  renderHistoryChart(latestTrend);
}

function renderHistoryChart(rows, predicted=null) {
  const times = rows.map(x => x.observed_at);
  const trace = {x:times, y:rows.map(x => Number(x.moisture_pct)), type:"scatter", mode:"lines",
    name:"Observed", line:{color:"#28699f",width:2}, hovertemplate:"%{x}<br>%{y:.2f}%<extra>Observed</extra>"};
  const traces = [trace];
  if (predicted) {
    traces.push({x:[predicted.origin_at,predicted.target_at],y:[predicted.current_moisture,predicted.predicted],
      type:"scatter",mode:"lines+markers",name:"Forecast",line:{color:"#d18a32",width:2,dash:"dash"},
      marker:{size:7},hovertemplate:"%{x}<br>%{y:.2f}%<extra>Forecast</extra>"});
  }
  if (window.Plotly) {
    Plotly.react("history-chart",traces,{margin:{l:42,r:12,t:10,b:42},paper_bgcolor:"#fff",plot_bgcolor:"#fff",
      font:{family:"Inter, Arial, sans-serif",size:10,color:"#657386"},legend:{orientation:"h",y:1.12,x:0},
      xaxis:{gridcolor:"#edf1f5",title:"Observation time",tickfont:{size:9}},
      yaxis:{gridcolor:"#edf1f5",title:"Moisture (%)",tickfont:{size:9}},hovermode:"x unified"},{responsive:true,displayModeBar:false});
  } else { $("history-chart").textContent = "Charts could not load. Check internet access and refresh the page; the forecast values remain available in the result panel."; }
}

function renderComparison(items, selectedName) {
  $("comparison-list").innerHTML = items.map(item => `
    <div class="comparison-row">
      <div><div class="comparison-name">${escapeHTML(item.model_name)} ${item.model_name===selectedName?"· selected":""}</div>
      <div class="comparison-sub">${escapeHTML(item.description)}</div></div>
      <div class="comparison-number">${num(item.predicted)}%</div>
    </div>`).join("");
}
function escapeHTML(s) { return String(s).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }

async function generateForecast() {
  clearAlert();
  const button = $("forecast-button"); button.disabled = true; button.textContent = "Generating forecast…";
  try {
    const data = await getJSON("/api/forecast/run",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({farm_code:activeFarm,horizon_hours:Number($("horizon-select").value),
        model_name:$("model-select").value,threshold_pct:Number($("threshold-input").value)})});
    lastPredictions = data.all_model_predictions;
    const cls = data.advisory_level.includes("REVIEW")?"review":data.advisory_level==="MONITOR"?"monitor":"ok";
    $("forecast-result").classList.remove("empty-state");
    $("forecast-result").innerHTML = `
      <div class="result-top"><span class="eyebrow">${data.horizon_hours}-HOUR FORECAST</span><span class="status ${cls}">${escapeHTML(data.advisory_level)}</span></div>
      <div class="result-value">${num(data.selected_prediction)}<small>%</small></div>
      <div class="result-meta">Current ${num(data.current_moisture)}% · ${escapeHTML(data.selected_model)} · Target ${dateText(data.target_at)}</div>
      <p class="chart-note">${escapeHTML(data.advisory_text)}</p>`;
    renderComparison(data.all_model_predictions,data.selected_model);
    renderHistoryChart(latestTrend,{origin_at:data.origin_at,target_at:data.target_at,current_moisture:data.current_moisture,predicted:data.selected_prediction});
    await loadForecastHistory();
    const notice = data.notice;
    $("forecast-result").title = notice;
  } catch (err) { showAlert(err.message); }
  finally { button.disabled = false; button.innerHTML = 'Generate farm forecast <span>→</span>'; }
}

async function loadForecastHistory() {
  if (!activeFarm) return;
  try {
    const data = await getJSON(`/api/forecast/history?farm_code=${encodeURIComponent(activeFarm)}`);
    const body = $("forecast-history");
    if (!data.forecasts.length) { body.innerHTML='<tr><td colspan="6" class="muted">No saved forecasts yet.</td></tr>'; return; }
    body.innerHTML = data.forecasts.map(f => `<tr>
      <td>${dateText(f.generated_at)}</td><td>${Math.round(Number(f.horizon_minutes)/60)} h</td>
      <td>${escapeHTML(f.model_name)}</td><td><strong>${num(f.predicted_moisture_pct)}%</strong></td>
      <td>${escapeHTML(f.advisory_level||"—")}</td><td>${escapeHTML(f.advisory_text||"—")}</td></tr>`).join("");
  } catch (err) { showAlert(err.message); }
}

async function saveProfile(event) {
  event.preventDefault();
  try {
    await getJSON("/api/farm/settings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      farm_code:activeFarm,crop_name:$("crop-input").value,soil_type:$("soil-input").value,
      field_area_sqft:$("area-input").value,threshold_pct:Number($("threshold-input").value)})});
    await loadOverview(); showAlert("Farm profile saved.");
    setTimeout(clearAlert,2500);
  } catch(err) { showAlert(err.message); }
}

$("farm-select").addEventListener("change",async e=>{activeFarm=e.target.value;lastPredictions=[];$("forecast-result").classList.add("empty-state");$("forecast-result").textContent="Select a farm and generate a forecast to view the predicted condition and advisory.";$("comparison-list").innerHTML='<p class="muted">Generate a forecast to compare methods.</p>';await loadOverview();await loadForecastHistory();});
$("forecast-button").addEventListener("click",generateForecast);
$("refresh-history").addEventListener("click",loadForecastHistory);
$("profile-form").addEventListener("submit",saveProfile);
let researchDashboardInitialised = false;
const initialiseResearchDashboard = () => {
  if (researchDashboardInitialised) return;
  researchDashboardInitialised = true;
  loadFarms().catch(err => showAlert(err.message + ". This is the separate Kolkata experimental sensor dataset; it is not the regional farm prediction. Open Farm predictions for the selected Indian virtual farm."));
};
// Do not fetch or display Kolkata experimental sensor forecasts on every login.
// Load them only when the user deliberately opens Reports & Research.
window.addEventListener("farmer-view-shown", (event) => {
  if (event.detail === "insights") initialiseResearchDashboard();
});

// Location-based regional intelligence. This is separate from the Kolkata
// experimental-farm model; regional products are never silently fed into it.
let regionLocations = [];
let currentRegion = null;

function metricCard(label, value, unit, note="") {
  return `<article class="region-metric-card"><span>${escapeHTML(label)}</span><strong>${value === null || value === undefined ? "—" : escapeHTML(String(value))}${unit ? `<small>${escapeHTML(unit)}</small>` : ""}</strong>${note ? `<em>${escapeHTML(note)}</em>` : ""}</article>`;
}
function showRegionError(message) {
  const box = $("region-error"); box.textContent = message; box.classList.remove("hidden");
}
function hideRegionError() { $("region-error").classList.add("hidden"); }

async function searchRegion(event) {
  event.preventDefault();
  hideRegionError();
  const query = $("region-query").value.trim();
  const button = $("region-search-button");
  button.disabled = true; button.textContent = "Searching…";
  try {
    const data = await getJSON(`/api/region/search?q=${encodeURIComponent(query)}`);
    regionLocations = data.locations || [];
    if (!regionLocations.length) throw new Error("No matching Indian locations found. Try adding the district and state.");
    const select = $("region-location-select"); select.innerHTML = "";
    regionLocations.forEach((loc, idx) => {
      const option = document.createElement("option"); option.value = String(idx);
      option.textContent = [loc.name, loc.admin2, loc.admin1, loc.country].filter(Boolean).join(", ");
      select.appendChild(option);
    });
    $("region-location-choices").classList.remove("hidden");
    if (regionLocations.length === 1) await analyzeSelectedRegion();
  } catch (err) { showRegionError(err.message); }
  finally { button.disabled = false; button.textContent = "Find location"; }
}

async function analyzeSelectedRegion() {
  hideRegionError();
  const idx = Number($("region-location-select").value || 0);
  const location = regionLocations[idx];
  if (!location) { showRegionError("Select a location before analysis."); return; }
  const button = $("region-analyze-button");
  button.disabled = true; button.textContent = "Analyzing region…";
  $("region-loading").classList.remove("hidden");
  $("region-results").classList.add("hidden");
  try {
    const data = await getJSON("/api/region/analyze", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(location)});
    currentRegion = data.region;
    window.currentRegionData = currentRegion;
    window.dispatchEvent(new CustomEvent("regional-data-ready", {detail: currentRegion}));
    renderRegion(currentRegion);
  } catch (err) { showRegionError(err.message); }
  finally {
    $("region-loading").classList.add("hidden");
    button.disabled = false; button.textContent = "Analyze selected region";
  }
}

function renderRegion(region) {
  const loc = region.location, climate = region.climate, forecast = region.weather_forecast, soil = region.soil;
  $("region-results").classList.remove("hidden");
  $("region-name").textContent = [loc.name, loc.admin2, loc.admin1, loc.country].filter(Boolean).join(", ");
  $("region-coordinates").textContent = `Latitude ${num(loc.latitude,4)} · Longitude ${num(loc.longitude,4)} · Climate period ${climate.period}`;
  const indianContext=region.indian_context||{};
  const zoneCandidates=indianContext.agro_climatic_zone_candidates||[];
  $("region-agro-context").innerHTML = zoneCandidates.length
    ? zoneCandidates.map(z=>`<article class="region-zone-card"><strong>Zone ${escapeHTML(z.id)} · ${escapeHTML(z.name)}</strong><span>${escapeHTML(z.climate||"")}</span><small>Typical farming systems: ${escapeHTML((z.typical_systems||[]).join(", "))}</small></article>`).join("") + `<p class="chart-note">${escapeHTML(indianContext.zone_classification_note||"")}</p>`
    : `<p class="muted">No state-level candidate was matched. Select an agro-climatic region only after checking the official regional map.</p>`;
  const seasonDefs=indianContext.season_definitions||{};
  $("region-season-calendar").innerHTML = Object.entries(seasonDefs).map(([name,d])=>`<article class="region-season-card"><strong>${escapeHTML(name)}</strong><span>${escapeHTML(d.usual_window||"")}</span><small>Examples: ${escapeHTML((d.examples||[]).join(", "))}</small></article>`).join("");
  $("region-climate-metrics").innerHTML = [
    metricCard("MEAN AIR TEMPERATURE", climate.mean_air_temperature_c, "°C", "NASA POWER daily mean"),
    metricCard("MEAN ANNUAL RAINFALL", climate.mean_annual_rainfall_mm, "mm", "Mean across complete years"),
    metricCard("MEAN RELATIVE HUMIDITY", climate.mean_relative_humidity_pct, "%", "Daily gridded estimate"),
    metricCard("MONSOON RAINFALL SHARE", climate.monsoon_jun_sep_rainfall_share_pct, "%", climate.rainfall_regime)
  ].join("");

  const months = climate.monthly || [];
  if (window.Plotly) {
    Plotly.react("region-climate-chart", [
      {x:months.map(x=>x.month),y:months.map(x=>x.mean_monthly_rainfall_mm),type:"bar",name:"Mean monthly rainfall",marker:{color:"#2a83a7"},yaxis:"y",hovertemplate:"%{x}: %{y:.1f} mm<extra></extra>"},
      {x:months.map(x=>x.month),y:months.map(x=>x.mean_temp_c),type:"scatter",mode:"lines+markers",name:"Mean temperature",line:{color:"#c27b2c",width:2},yaxis:"y2",hovertemplate:"%{x}: %{y:.1f} °C<extra></extra>"}
    ], {margin:{l:48,r:52,t:12,b:32},paper_bgcolor:"#fff",plot_bgcolor:"#fff",font:{family:"Inter, Arial, sans-serif",size:10,color:"#657386"},legend:{orientation:"h",y:1.15},xaxis:{gridcolor:"#edf1f5"},yaxis:{title:"Rainfall (mm)",gridcolor:"#edf1f5"},yaxis2:{title:"Temperature (°C)",overlaying:"y",side:"right",showgrid:false}}, {responsive:true,displayModeBar:false});
  } else { $("region-climate-chart").textContent = "Climate chart library unavailable. The climate metrics and tables remain available above."; }

  const regionalPred = region.regional_prediction || {};
  if (regionalPred.status === "available") {
    const metrics = regionalPred.validation_metrics || {};
    const metricRows = Object.entries(metrics).map(([name,m])=>`<tr><td>${escapeHTML(name)}</td><td>${num(m.mae,4)}</td><td>${num(m.rmse,4)}</td><td>${num(m.r2,3)}</td></tr>`).join("");
    const moisturePercentLabel = regionalPred.target_name === "RZMC" ? "Volumetric moisture (%)" : "Relative root-zone wetness (%)";
    const moistureTableLabel = regionalPred.target_name === "RZMC" ? "Volumetric moisture (%)" : "Relative saturation (%)";
    $("region-moisture-prediction").innerHTML = `
      <div class="region-prediction-summary">
        <div><span class="metric-label">SELECTED MODEL</span><strong>${escapeHTML(regionalPred.selected_model||"—")}</strong></div>
        <div><span class="metric-label">ROOT-ZONE TARGET</span><strong>${escapeHTML(regionalPred.target_description||"—")}</strong></div>
        <div><span class="metric-label">HISTORICAL RECORDS</span><strong>${Number(regionalPred.aligned_daily_records||0).toLocaleString()}</strong></div>
        <div><span class="metric-label">LATEST MOISTURE RECORD</span><strong>${escapeHTML(regionalPred.latest_observation_date||"—")}</strong></div>
      </div>
      <div class="table-wrap"><table class="region-table"><thead><tr><th>Chronological holdout model</th><th>MAE (${escapeHTML(regionalPred.unit||"")})</th><th>RMSE (${escapeHTML(regionalPred.unit||"")})</th><th>R²</th></tr></thead><tbody>${metricRows}</tbody></table></div>
      <p class="chart-note">Validation scores are chronological one-day-ahead holdout metrics using prior-day weather features. The displayed ${Number(regionalPred.forecast_horizon_days||0)}-day path is recursive and uses forecast weather plus predicted moisture lags; its cumulative error has not been independently validated. Scores are for this NASA grid point and target product, not farm-level validation.</p>
      <div class="table-wrap"><table class="region-table"><thead><tr><th>Forecast date</th><th>Predicted root-zone moisture</th><th>${escapeHTML(moistureTableLabel)}</th></tr></thead><tbody>${(regionalPred.forecasts||[]).map(x=>`<tr><td>${escapeHTML(x.date)}</td><td>${num(x.predicted_rootzone_moisture,4)} ${escapeHTML(regionalPred.unit||"")}</td><td>${num(x.predicted_volumetric_percent,2)}%</td></tr>`).join("")}</tbody></table></div>`;
    const pred = regionalPred.forecasts || [];
    if (window.Plotly) Plotly.react("region-moisture-chart", [{x:pred.map(x=>x.date),y:pred.map(x=>x.predicted_volumetric_percent),type:"scatter",mode:"lines+markers",name:"Predicted root-zone moisture",line:{color:"#3478b6",width:2},marker:{size:6},hovertemplate:"%{x}<br>%{y:.2f}%<extra>Prediction</extra>"}], {margin:{l:48,r:15,t:10,b:36},paper_bgcolor:"#fff",plot_bgcolor:"#fff",font:{family:"Inter, Arial, sans-serif",size:10,color:"#657386"},xaxis:{title:"Forecast date",gridcolor:"#edf1f5"},yaxis:{title:moisturePercentLabel,gridcolor:"#edf1f5"}}, {responsive:true,displayModeBar:false});
    else $("region-moisture-chart").textContent = "Prediction values are available in the table above. The chart library could not load.";
  } else {
    $("region-moisture-prediction").innerHTML = `<p class="muted">Location-specific soil-moisture prediction is unavailable for this request.</p><p class="chart-note">${escapeHTML(regionalPred.reason||"NASA POWER root-zone moisture data could not be obtained for this location.")}</p>`;
    if (window.Plotly) Plotly.purge("region-moisture-chart");
  }

  $("region-weather-rows").innerHTML = (forecast.daily||[]).map(day=>`<tr><td>${escapeHTML(day.date||"—")}</td><td>${num(day.min_temp_c,1)}</td><td>${num(day.max_temp_c,1)}</td><td>${num(day.precipitation_mm,1)}</td><td>${day.precipitation_probability_pct==null?"—":escapeHTML(day.precipitation_probability_pct+"%")}</td><td>${num(day.et0_mm,1)}</td></tr>`).join("") || '<tr><td colspan="6">No forecast data returned.</td></tr>';

  const props = soil.properties || {};
  const soilMetricItems = [
    ["ESTIMATED TEXTURE",soil.texture_group_screening||"Not available","", "Sand/clay screening only"],
    ["SOIL pH",props.ph?.value,props.ph?.unit,"Modelled 0–5 cm"],
    ["ORGANIC CARBON",props.soil_organic_carbon_g_kg?.value,props.soil_organic_carbon_g_kg?.unit,"Modelled 0–5 cm"],
    ["TOTAL NITROGEN",props.total_nitrogen_g_kg?.value,props.total_nitrogen_g_kg?.unit,"Not plant-available N"],
    ["CLAY",props.clay_pct?.value,props.clay_pct?.unit,"Texture fraction"],
    ["SAND",props.sand_pct?.value,props.sand_pct?.unit,"Texture fraction"],
    ["CEC",props.cation_exchange_capacity_cmol_kg?.value,props.cation_exchange_capacity_cmol_kg?.unit,"Cation exchange capacity"]
  ];
  $("region-soil-summary").innerHTML = soilMetricItems.map(x=>metricCard(x[0],x[1],x[2],x[3])).join("");
  $("region-soil-note").textContent = soil.status === "available" ? `${soil.limitations} Source depth: ${soil.depth}; nominal grid resolution: ${soil.spatial_resolution_m} m.` : `SoilGrids could not return a sample for this location. ${soil.limitations}`;

  const crops = region.crop_pattern || {};
  if (crops.available) {
    const seasonSummary = (crops.seasonal_patterns||[]).map(s=>`${escapeHTML(s.season)}${s.area_ha==null?"":` (${Number(s.mean_annual_area_ha).toLocaleString()} ha)`}`).join(" · ");
    const cropSourceLabel = crops.data_type === "synthetic_demo" ? "SYNTHETIC DEMO DATA — NOT OFFICIAL" : crops.data_type === "uploaded" ? "UPLOADED CSV — ORIGIN NOT VERIFIED BY APP" : "DATA SOURCE TO BE VERIFIED";
    const trendRows = (crops.trend_projections||[]).map(x=>`<tr><td>${escapeHTML(x.crop)}</td><td>${Number(x.target_year)}</td><td>${x.area_ha==null?"—":Number(x.area_ha).toLocaleString()}</td><td>${x.production_t==null?"—":Number(x.production_t).toLocaleString()}</td></tr>`).join("");
    $("region-crop-pattern").innerHTML = `<p class="chart-note">${escapeHTML(crops.district)}, ${escapeHTML(crops.state||"")} · ${escapeHTML(crops.period||"")}</p><span class="farm-outlook-provenance-pill ${crops.data_type === "synthetic_demo" ? "is-demo" : ""}">${cropSourceLabel}</span><p><strong>Largest recorded seasonal area:</strong> ${escapeHTML(crops.dominant_historical_season||"Not available")}</p><p class="chart-note">Recorded district seasonal area (source unit: ha): ${seasonSummary||"Not available"}</p><div class="table-wrap"><table class="region-table"><thead><tr><th>Crop</th><th>Recorded seasons</th><th>District area (source unit: ha)</th><th>Mean annual production (t)</th></tr></thead><tbody>${crops.crops.map(c=>`<tr><td><strong>${escapeHTML(c.crop)}</strong></td><td>${escapeHTML((c.seasons||[]).join(", "))}</td><td>${c.mean_annual_area_ha==null?"—":Number(c.mean_annual_area_ha).toLocaleString()}</td><td>${c.mean_annual_production_t==null?"—":Number(c.mean_annual_production_t).toLocaleString()}</td></tr>`).join("")}</tbody></table></div>${trendRows?`<h4>District trend baseline · ${Number(crops.trend_projections[0].target_year)}</h4><div class="table-wrap"><table class="region-table"><thead><tr><th>Crop</th><th>Year</th><th>District trend area (source unit: ha)</th><th>Trend production (t)</th></tr></thead><tbody>${trendRows}</tbody></table></div><p class="chart-note">${escapeHTML(crops.trend_note||"District historical trend only; not a farm yield forecast.")}</p>`:""}<p class="chart-note">${escapeHTML(crops.source||"")} · ${escapeHTML(crops.message||"")}</p>`;
  } else {
    $("region-crop-pattern").innerHTML = `<p class="muted">${escapeHTML(crops.message||"Crop pattern not available.")}</p><p class="chart-note">Upload the official district-wise crop production CSV below. The application will then show recorded crops by area and production.</p>`;
  }

  const problemReport = region.regional_problem_report || {};
  const challengeCards = (problemReport.documented_challenges || []).map(item=>`
    <article class="region-problem-card">
      <div class="region-problem-meta"><span class="region-problem-category">${escapeHTML(item.category || "Regional challenge")}</span><span class="region-problem-scope">${escapeHTML(item.evidence_scope || problemReport.profile_level || "Regional context")}</span></div>
      <strong>${escapeHTML(item.problem)}</strong>
      <p><b>Possible response:</b> ${escapeHTML(item.response)}</p>
      <p class="region-problem-verify"><b>Before acting:</b> ${escapeHTML(item.verify)}</p>
    </article>`).join("");
  const profileLink = problemReport.profile_source_url ? `<a href="${escapeHTML(problemReport.profile_source_url)}" target="_blank" rel="noopener">${escapeHTML(problemReport.profile_source_name || "Regional source")}</a>` : "";
  const districtLink = problemReport.district_plan_url ? `<a href="${escapeHTML(problemReport.district_plan_url)}" target="_blank" rel="noopener">Open ICAR-CRIDA district contingency plans ↗</a>` : "";
  $("region-problem-context").innerHTML = `
    <div class="region-problem-intro"><strong>${escapeHTML(problemReport.profile_name || "Regional agriculture profile")}</strong><p>${escapeHTML(problemReport.farming_context || "A state-specific farming profile was not matched. Use the district contingency plan directory for a more specific profile.")}</p><small>${escapeHTML(problemReport.scope_note || "Regional profile; verify at district and farm level.")}</small></div>
    <div class="region-problem-grid">${challengeCards || '<p class="muted">No curated profile is available for this state/zone yet. Open the district contingency plan directory for official local issues and contingency actions.</p>'}</div>
    <div class="region-problem-sources">Profile source: ${profileLink || "Not matched"} · ${districtLink}<p>${escapeHTML(problemReport.district_plan_note || "")}</p></div>`;
  const liveSignals = (problemReport.current_signals || []).map(item=>`<article class="region-action"><span class="region-action-level">${escapeHTML(item.level || "Watch")}</span><div><strong>${escapeHTML(item.title)}</strong><p>${escapeHTML(item.evidence || "")}</p><p>${escapeHTML(item.response || "")}</p><em>${escapeHTML(item.basis || "")}</em></div></article>`).join("");
  $("region-live-problems").innerHTML = liveSignals || '<p class="muted">No regional weather/soil screening signal was triggered by the current data. This does not mean that the farm has no problems; inspect the field and consult local advisories.</p>';
  $("region-actions").innerHTML = (region.next_actions||[]).map(action=>`<article class="region-action"><span class="region-action-level">${escapeHTML(action.level)}</span><div><strong>${escapeHTML(action.title)}</strong><p>${escapeHTML(action.detail)}</p></div></article>`).join("");
  const src = region.sources || {};
  const indiaSources=indianContext.sources||{};
  const providerErrors = (region.source_errors||[]).map(item=>`${escapeHTML(item.source)}: ${escapeHTML(item.reason)}`).join(" · ");
  $("region-sources").innerHTML = `${providerErrors?`<p class="chart-note"><strong>Some data providers did not respond:</strong> ${providerErrors}</p>`:""}Data sources: <a href="${escapeHTML(src.climate||"#")}" target="_blank" rel="noopener">NASA POWER</a> · <a href="${escapeHTML(src.forecast||"#")}" target="_blank" rel="noopener">Open-Meteo</a> · <a href="${escapeHTML(src.soil||"#")}" target="_blank" rel="noopener">ISRIC SoilGrids</a> · <a href="${escapeHTML(src.crops||"#")}" target="_blank" rel="noopener">India OGD crop statistics</a> · <a href="${escapeHTML(src.soil_health||"#")}" target="_blank" rel="noopener">Soil Health Card</a> · <a href="${escapeHTML(src.district_contingency_plans||"#")}" target="_blank" rel="noopener">ICAR-CRIDA district plans</a> · <a href="${escapeHTML(indiaSources.agro_climatic_regions||"#")}" target="_blank" rel="noopener">Planning Commission agro-climatic regions</a> · <a href="${escapeHTML(indiaSources.crop_calendar||"#")}" target="_blank" rel="noopener">Indian crop calendar</a> · <a href="${escapeHTML(indiaSources.soil_resources||"#")}" target="_blank" rel="noopener">ICAR-NBSS&amp;LUP soil resources</a>`;
}

async function uploadCropStats(event) {
  event.preventDefault();
  const file = $("crop-stats-file").files[0];
  if (!file) return;
  const status = $("crop-upload-status"); status.textContent = "Importing CSV…";
  const form = new FormData(); form.append("crop_stats", file);
  try {
    const response = await fetch("/api/region/crop-stats/upload", {method:"POST",body:form});
    const data = await response.json();
    if (!response.ok || data.ok === false) throw new Error(data.error || `Upload failed (${response.status})`);
    status.textContent = `Imported ${Number(data.summary.rows).toLocaleString()} rows across ${data.summary.districts} districts. Run regional analysis again.`;
  } catch (err) { status.textContent = err.message; }
}

$("region-search-form").addEventListener("submit", searchRegion);
$("region-analyze-button").addEventListener("click", analyzeSelectedRegion);
$("crop-stats-form").addEventListener("submit", uploadCropStats);
const demoCropButton = $("load-demo-crop-stats");
if (demoCropButton) demoCropButton.addEventListener("click", async () => {
  const status = $("crop-upload-status");
  demoCropButton.disabled = true;
  status.textContent = "Loading clearly labelled synthetic district crop data…";
  try {
    const data = await getJSON("/api/region/crop-stats/demo", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    status.textContent = `${data.message} ${data.summary.rows} rows loaded for ${data.summary.districts} districts.`;
    if (currentRegion?.location) {
      const refreshed = await getJSON("/api/region/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(currentRegion.location) });
      currentRegion = refreshed.region;
      window.currentRegionData = currentRegion;
      renderRegion(currentRegion);
    }
  } catch (error) {
    status.textContent = error.message;
  } finally {
    demoCropButton.disabled = false;
  }
});
