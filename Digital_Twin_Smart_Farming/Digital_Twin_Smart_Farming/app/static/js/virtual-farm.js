(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const num = (v,d=2) => v === null || v === undefined || v === "" ? "—" : Number(v).toFixed(d);
  const SQFT_PER_SQM = 10.7639104167;
  let currentRegion = null, currentFarm = null, map = null, plotLayer = null, assetLayer = null, farmBoundaryLayer = null, farmMarker = null;
  let pendingBoundary = null, placeAssetMode = false, pendingAssetMarker = null, farmBoundaryMode = false;
  let mapClickHandler = null;

  async function api(url, options={}) {
    const r = await fetch(url, options); const data = await r.json();
    if (!r.ok || data.ok === false) throw new Error(data.error || `Request failed (${r.status})`);
    return data;
  }
  function status(id,msg,error=false){ const el=$(id); if(el){el.textContent=msg; el.classList.toggle("error-text",!!error);} }
  function metric(label,value,unit){return `<article class="region-metric-card"><span>${esc(label)}</span><strong>${value===null||value===undefined?"—":esc(num(value,2))}${unit?`<small>${esc(unit)}</small>`:""}</strong><em>Regional estimate</em></article>`;}
  function updateSeasonNote(){
    const season=$ ("vf-season").value;
    const definition=currentRegion?.indian_context?.season_definitions?.[season];
    $("vf-season-note").textContent=definition ? `${definition.usual_window}. Common crops listed nationally: ${definition.examples.join(", ")}. Check state/district-specific timing.` : "Choose the crop season; local sowing/harvest timing varies by state and crop.";
  }
  function currentZoneOptions(ctx, selected="") {
    const candidates = ctx?.agro_climatic_zone_candidates || [];
    const all = ctx?.all_agro_climatic_zones || [];
    const choices = candidates.length ? candidates : all;
    const sel=$("vf-zone");
    const suggested = selected || (candidates.length === 1 ? candidates[0].id : "");
    sel.innerHTML='<option value="">Choose the suggested farming region</option>' + choices.map(z=>`<option value="${esc(z.id)}" ${z.id===suggested?"selected":""}>${esc(z.id)} — ${esc(z.name)}</option>`).join("");
    status("vf-zone-note", candidates.length === 1
      ? "One likely region was pre-selected from the location search. Please confirm it if you know your local district classification."
      : candidates.length > 1
        ? `${candidates.length} possible regions match this state. Choose the one that best matches your district; ask a local agriculture officer if unsure.`
        : "No state-level suggestion was found. Choose a region only after checking an official map or asking your local agriculture office.");
  }
  function fillFromRegion(region) {
    currentRegion=region;
    const loc=region.location||{};
    $("vf-farm-name").value = $("vf-farm-name").value || `${loc.name || "Indian"} Farm`;
    $("vf-village").value = loc.name || "";
    $("vf-lat").value = Number(loc.latitude).toFixed(6);
    $("vf-lon").value = Number(loc.longitude).toFixed(6);
    currentZoneOptions(region.indian_context);
    const crops = region.crop_pattern?.crops || [];
    const list=$("indian-crops");
    const existing=new Set(Array.from(list.options).map(o=>o.value.toLowerCase()));
    crops.forEach(c=>{ if(c.crop && !existing.has(c.crop.toLowerCase())) { const o=document.createElement("option");o.value=c.crop;list.appendChild(o);existing.add(c.crop.toLowerCase()); }});
    const soil=region.soil||{};
    const mapped=soil.properties||{};
    const ph=mapped.ph?.value, sand=mapped.sand_pct?.value, clay=mapped.clay_pct?.value;
    $("vf-soil-regional-note").textContent=`Regional screening context: ${soil.texture_group_screening||"texture unavailable"}; mapped pH ${ph==null?"—":ph}; sand ${sand==null?"—":sand}%; clay ${clay==null?"—":clay}%. These are regional estimates, not plot-level soil test values.`;
    updateSeasonNote();
    const button=$("create-farm-from-region");
    if(button) button.textContent=`Create virtual farm at ${loc.name || "selected location"} →`;
  }
  window.addEventListener("regional-data-ready", e=>fillFromRegion(e.detail));

  function initMap(farm) {
    const el=$("virtual-farm-map");
    if(!window.L){ el.innerHTML='<div class="vf-map-placeholder">Map library could not load. Check internet access and reload the page.</div>'; return; }
    if(!map){
      el.innerHTML="";
      map=L.map(el,{scrollWheelZoom:true}).setView([Number(farm.latitude),Number(farm.longitude)],16);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
      farmBoundaryLayer=L.featureGroup().addTo(map); plotLayer=L.featureGroup().addTo(map); assetLayer=L.layerGroup().addTo(map);
      const drawControl=new L.Control.Draw({position:"topright",draw:{polyline:false,polygon:{allowIntersection:false,showArea:true,shapeOptions:{color:"#287c55",weight:2,fillOpacity:0.18}},rectangle:{shapeOptions:{color:"#287c55",weight:2,fillOpacity:0.18}},circle:false,circlemarker:false,marker:false},edit:false});
      map.addControl(drawControl);
      map.on(L.Draw.Event.CREATED,e=>{
        if(e.layerType!=="polygon" && e.layerType!=="rectangle") return;
        if(farmBoundaryMode){
          farmBoundaryMode=false;
          const boundaryLayer=e.layer; boundaryLayer.setStyle({color:"#2563eb",weight:3,fillColor:"#93c5fd",fillOpacity:0.13});
          farmBoundaryLayer.clearLayers(); farmBoundaryLayer.addLayer(boundaryLayer);
          const feature=boundaryLayer.toGeoJSON();
          const ring=boundaryLayer.getLatLngs()?.[0]||[];
          const areaSqft=window.L.GeometryUtil&&ring.length>=3?window.L.GeometryUtil.geodesicArea(ring)*SQFT_PER_SQM:null;
          $("vf-draw-farm-boundary").textContent="Redraw outer farm boundary";
          status("vf-boundary-status",`Outer boundary captured${areaSqft?`; drawn area ≈ ${Math.round(areaSqft).toLocaleString()} sq ft`:""}. Saving boundary…`);
          api(`/api/virtual-farms/${currentFarm.virtual_farm_id}/boundary`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({boundary_geojson:feature})})
            .then(data=>{status("vf-boundary-status",`Outer farm boundary saved${areaSqft?`; map-area estimate ${Math.round(areaSqft).toLocaleString()} sq ft`:""}. Compare with the registered area.`);renderFarm(data.farm);})
            .catch(err=>{status("vf-boundary-status",err.message,true);});
          return;
        }
        if(pendingBoundary) plotLayer.removeLayer(pendingBoundary.layer);
        const layer=e.layer; plotLayer.addLayer(layer);
        pendingBoundary={layer,geojson:layer.toGeoJSON()};
        const ring = layer.getLatLngs()?.[0] || [];
        if (window.L.GeometryUtil && ring.length >= 3 && !$ ("vf-plot-area").value) {
          const estimateSqft = window.L.GeometryUtil.geodesicArea(ring) * SQFT_PER_SQM;
          $("vf-plot-area").value = String(Math.round(estimateSqft));
        }
        $("virtual-plot-form").classList.remove("hidden"); $("vf-plot-instruction").classList.add("hidden");
        $("vf-plot-name").focus(); status("vf-plot-status","Plot boundary captured. Enter the plot details and save it to the Digital Twin.");
        if(!$ ("vf-plot-area").value && currentFarm) $("vf-plot-area").value="";
      });
      map.on("click",e=>{
        if(!placeAssetMode) return;
        const lat=e.latlng.lat, lon=e.latlng.lng;
        $("vf-asset-lat").value=lat; $("vf-asset-lon").value=lon;
        if(pendingAssetMarker) assetLayer.removeLayer(pendingAssetMarker);
        pendingAssetMarker=L.marker([lat,lon]).addTo(assetLayer).bindPopup("New asset placement").openPopup();
        $("vf-asset-location").textContent=`Asset position: ${lat.toFixed(6)}, ${lon.toFixed(6)}`;
        placeAssetMode=false; $("vf-place-asset").textContent="Place asset on map";
      });
    } else {
      setTimeout(()=>map.invalidateSize(),100);
      map.setView([Number(farm.latitude),Number(farm.longitude)],16);
    }
    if(farmMarker) map.removeLayer(farmMarker);
    farmMarker=L.marker([Number(farm.latitude),Number(farm.longitude)]).addTo(map).bindPopup(`<strong>${esc(farm.farm_name)}</strong><br>${esc(farm.village||farm.district)}, ${esc(farm.state)}<br>Farm reference point`).openPopup();
    farmBoundaryLayer.clearLayers(); plotLayer.clearLayers(); assetLayer.clearLayers();
    if(farm.boundary){L.geoJSON(farm.boundary,{style:{color:"#2563eb",weight:3,fillColor:"#93c5fd",fillOpacity:0.1}}).addTo(farmBoundaryLayer).bindTooltip("Outer farm boundary");}
    (farm.plots||[]).forEach(plot=>{
      if(plot.boundary){
        const layer=L.geoJSON(plot.boundary,{style:{color:"#287c55",weight:2,fillOpacity:0.18}}).addTo(plotLayer);
        layer.bindTooltip(`${plot.plot_code}: ${plot.plot_name}<br>${plot.crop_name||"Crop not set"} · ${plot.season||"Season not set"}`);
      }
    });
    (farm.assets||[]).forEach(a=>{
      const m=L.marker([Number(a.latitude),Number(a.longitude)]).addTo(assetLayer);
      m.bindTooltip(`${a.asset_type}: ${a.asset_name}`);
    });
    const farmBounds=farmBoundaryLayer.getBounds(); const plotBounds=plotLayer.getBounds();
    if(farmBounds.isValid()) map.fitBounds(farmBounds.pad(0.14)); else if(plotBounds.isValid()) map.fitBounds(plotBounds.pad(0.16));
    $("vf-draw-farm-boundary").textContent=farm.boundary?"Redraw outer farm boundary":"Draw outer farm boundary";
    status("vf-boundary-status",farm.boundary?"Outer farm boundary is stored. Draw individual plot polygons inside it.":"Outer farm boundary has not been drawn yet.");
    setTimeout(()=>map.invalidateSize(),150);
  }

  function renderFarm(farm){
    currentFarm=farm; $("vf-plot-instruction").classList.remove("hidden"); $("virtual-plot-form").classList.add("hidden");
    $("virtual-asset-form").classList.remove("hidden");
    const zone=farm.agro_climatic_zone_id ? `${farm.agro_climatic_zone_id} — ${farm.agro_climatic_zone_name||""}` : "Zone not assigned";
    $("vf-current-summary").innerHTML=`<div class="vf-summary-grid"><div><span>FARM</span><strong>${esc(farm.farm_name)}</strong></div><div><span>LOCATION</span><strong>${esc(farm.village||farm.district)}, ${esc(farm.state)}</strong></div><div><span>AGRO-CLIMATIC REGION</span><strong>${esc(zone)}</strong></div><div><span>REGISTERED AREA</span><strong>${num(farm.total_area_sqft,0)} sq ft</strong></div><div><span>PLOTS</span><strong>${farm.plots.length}</strong></div><div><span>MAPPED AREA</span><strong>${num(farm.mapped_plot_area_sqft,0)} sq ft</strong></div><div><span>UNALLOCATED AREA</span><strong>${num(farm.unmapped_area_sqft,0)} sq ft</strong></div><div><span>INFRASTRUCTURE</span><strong>${farm.assets.length} assets</strong></div></div>`;
    $("vf-plot-list").innerHTML = farm.plots.length ? farm.plots.map(p=>`<article class="vf-plot-card"><div><strong>${esc(p.plot_code)} · ${esc(p.plot_name)}</strong><span>${num(p.area_sqft,0)} sq ft · ${esc(p.crop_name||"Crop not set")} · ${esc(p.season||"Season not set")}</span><small>${esc(p.indian_soil_group||"Soil group not entered")} · ${esc(p.crop_stage||"Stage not entered")} · ${esc(p.irrigation_method||"Irrigation not set")} · ${p.boundary?"Mapped boundary":"No map boundary"}</small><small>Field-test values: pH ${num(p.soil_ph,2)} · OC ${num(p.organic_carbon_pct,2)}% · Available N/P/K ${num(p.available_n_kg_ha,0)}/${num(p.available_p_kg_ha,0)}/${num(p.available_k_kg_ha,0)} kg/ha</small></div></article>`).join("") : '<div class="vf-empty">No plots added yet. Draw your first field boundary on the map.</div>';
    const climate=farm.climate_profile||{}; const soil=farm.soil_profile||{}; const sp=soil.properties||{};
    $("vf-environment-summary").innerHTML=`<div class="region-section-heading"><h3>Regional climate snapshot attached to this farm</h3><span class="data-source-tag">${esc(climate.source||"Regional data")}</span></div><div class="region-metrics">${metric("Mean air temperature",climate.mean_air_temperature_c,"°C")}${metric("Mean annual rainfall",climate.mean_annual_rainfall_mm,"mm")}${metric("Mean relative humidity",climate.mean_relative_humidity_pct,"%")}${metric("Monsoon rainfall share",climate.monsoon_jun_sep_rainfall_share_pct,"%")}</div><div class="region-section-heading"><h3>Mapped regional soil context</h3><span class="data-source-tag">${esc(soil.source||"Soil map")}</span></div><div class="region-metrics">${metric("Mapped soil texture",soil.texture_group_screening||"Not available","")}${metric("Mapped pH",sp.ph?.value,sp.ph?.unit||"")}${metric("Organic carbon",sp.soil_organic_carbon_g_kg?.value,sp.soil_organic_carbon_g_kg?.unit||"")}${metric("Total nitrogen",sp.total_nitrogen_g_kg?.value,sp.total_nitrogen_g_kg?.unit||"")}</div><div class="region-section-heading"><h3>Historical district cropping pattern</h3><span class="data-source-tag">India OGD upload</span></div><p class="chart-note">${(farm.regional_context?.regional_crop_pattern?.crops||[]).length ? (farm.regional_context.regional_crop_pattern.crops.slice(0,6).map(c=>`${esc(c.crop)} (${esc((c.seasons||[]).join("/")||"season n/a")})`).join(" · ")) : "No district crop-history data was attached when this farm was created. Upload the official district crop CSV in Regional Farm Intelligence, analyze the region again, and create a refreshed farm profile."}</p><p class="chart-note">Climate, cropping and mapped soil values are regional snapshots captured when the farm was created. They are not plot-level sensor observations or field soil-test results.</p>`;
    loadSoilReports();
    const select=$("vf-select");
    if(select.value!==String(farm.virtual_farm_id)){select.value=String(farm.virtual_farm_id);}
    if (document.getElementById("farm-view")?.classList.contains("is-active")) initMap(farm);
  }

  window.addEventListener("farmer-view-shown", (event) => {
    if (event.detail !== "farm" || !currentFarm) return;
    window.requestAnimationFrame(() => {
      initMap(currentFarm);
      if (map) window.setTimeout(() => map.invalidateSize(), 120);
    });
  });

  function useCurrentDeviceLocation(){
    const button=$("vf-use-location");
    const message=$("vf-location-status");
    if(!navigator.geolocation){status("vf-location-status","Location is not available in this browser. Open “More farm details” and enter the farm coordinates if you know them.",true);return;}
    button.disabled=true;
    status("vf-location-status","Requesting location permission…");
    navigator.geolocation.getCurrentPosition(position=>{
      $("vf-lat").value=Number(position.coords.latitude).toFixed(6);
      $("vf-lon").value=Number(position.coords.longitude).toFixed(6);
      const details=button.closest("form")?.querySelector(".vf-advanced-fields");
      if(details) details.open=true;
      const accuracy=Number(position.coords.accuracy);
      status("vf-location-status",`Location filled. Estimated device accuracy: ${Number.isFinite(accuracy)?Math.round(accuracy)+" metres":"not reported"}. Use this only if you are at the farm; check the map before saving.`,false);
      button.disabled=false;
    },error=>{
      const messages={1:"Location permission was not granted. You can allow it in your browser settings or enter coordinates manually.",2:"Your device could not determine a location. Try again outdoors or enter coordinates manually.",3:"The location request timed out. Try again or enter coordinates manually."};
      status("vf-location-status",messages[error.code]||"Could not get your location. Enter coordinates manually if needed.",true);
      button.disabled=false;
    },{enableHighAccuracy:true,timeout:20000,maximumAge:0});
  }

  async function loadFarmList(preselect=null){
    const data=await api("/api/virtual-farms"); const select=$("vf-select");
    select.innerHTML=data.farms.length?data.farms.map(f=>`<option value="${f.virtual_farm_id}">${esc(f.farm_name)} — ${esc(f.district)}, ${esc(f.state)}</option>`).join(""):'<option value="">No virtual farm created yet</option>';
    if(preselect) select.value=String(preselect);
    if(data.farms.length){const id=Number(select.value); await loadFarm(id);}
    else {currentFarm=null; $("vf-current-summary").textContent="No virtual farm selected.";}
  }
  async function loadFarm(id){ if(!id) return; const data=await api(`/api/virtual-farms/${id}`); renderFarm(data.farm); }

  async function createFarmFromRegion(){
    currentRegion=window.currentRegionData||currentRegion;
    if(!currentRegion){status("vf-create-status","Analyze an Indian location in Regional Farm Intelligence first.",true);return;}
    fillFromRegion(currentRegion);
    if (window.setFarmerView) window.setFarmerView("farm");
    $("virtual-farm-builder").scrollIntoView({behavior:"smooth",block:"start"});
    $("vf-farm-name").focus();
  }
  async function createFarm(e){
    e.preventDefault();
    const region=currentRegion||window.currentRegionData;
    if(!region){status("vf-create-status","Analyze a location first so the farm is attached to an Indian district and climate context.",true);return;}
    const zoneOpt=$("vf-zone").selectedOptions[0];
    if(!zoneOpt || !zoneOpt.value){status("vf-create-status","Select the agro-climatic region after checking the local classification, or review the state/district match.",true);return;}
    const loc=region.location||{};
    const payload={farm_name:$ ("vf-farm-name").value.trim(),village:$ ("vf-village").value.trim(),total_area_sqft:$ ("vf-area").value,
      location:{...loc, latitude:$ ("vf-lat").value, longitude:$ ("vf-lon").value},agro_climatic_zone_id:zoneOpt.value,agro_climatic_zone_name:zoneOpt.textContent.replace(/^\S+\s+—\s+/,""),
      farming_system:$ ("vf-system").value,land_form:$ ("vf-landform").value,water_source:$ ("vf-water").value,primary_irrigation_method:$ ("vf-irrigation").value,
      climate_profile:region.climate||{},soil_profile:region.soil||{},indian_context:region.indian_context||{},
      crop_pattern:region.crop_pattern||{},weather_forecast:region.weather_forecast||{}};
    status("vf-create-status","Creating farm digital structure…");
    try{const data=await api("/api/virtual-farms",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      status("vf-create-status",`Created ${data.farm.farm_name}. Now map its plots and infrastructure.`); window.dispatchEvent(new CustomEvent("virtual-farm-saved", {detail:{farmId:data.farm_id}})); await loadFarmList(data.farm_id);
    }catch(err){status("vf-create-status",err.message,true);}
  }
  async function savePlot(e){
    e.preventDefault(); if(!currentFarm){status("vf-plot-status","Select a virtual farm first.",true);return;}
    const payload={plot_name:$ ("vf-plot-name").value,area_sqft:$ ("vf-plot-area").value,crop_name:$ ("vf-crop").value,crop_variety:$ ("vf-variety").value,
      season:$ ("vf-season").value,sowing_date:$ ("vf-sowing").value||null,crop_stage:$ ("vf-stage").value,indian_soil_group:$ ("vf-soil-group").value,
      soil_texture:$ ("vf-soil-texture").value,soil_ph:$ ("vf-ph").value,soil_ec_ds_m:$ ("vf-ec").value,organic_carbon_pct:$ ("vf-oc").value,
      available_n_kg_ha:$ ("vf-n").value,available_p_kg_ha:$ ("vf-p").value,available_k_kg_ha:$ ("vf-k").value,
      soil_test_source:$ ("vf-soil-source").value,soil_test_date:$ ("vf-soil-date").value||null,irrigation_method:$ ("vf-irrigation-plot").value,
      boundary_geojson:pendingBoundary?.geojson||null,notes:$ ("vf-plot-notes").value};
    status("vf-plot-status","Saving plot…");
    try{const data=await api(`/api/virtual-farms/${currentFarm.virtual_farm_id}/plots`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      if(pendingBoundary){plotLayer.removeLayer(pendingBoundary.layer);pendingBoundary=null;}
      $("virtual-plot-form").reset();$("virtual-plot-form").classList.add("hidden");$("vf-plot-instruction").classList.remove("hidden");
      status("vf-plot-status","Plot saved.");renderFarm(data.farm);
    }catch(err){status("vf-plot-status",err.message,true);}
  }
  function clearPending(){if(pendingBoundary&&plotLayer)plotLayer.removeLayer(pendingBoundary.layer);pendingBoundary=null;$("virtual-plot-form").classList.add("hidden");$("vf-plot-instruction").classList.remove("hidden");status("vf-plot-status","Pending boundary cleared.");}
  function toggleFarmBoundary(){
    if(!currentFarm || !map){status("vf-boundary-status","Create or select a virtual farm first.",true);return;}
    farmBoundaryMode=true;
    status("vf-boundary-status","Draw the outer perimeter by clicking its corners on the map, then double-click to finish.");
    $("vf-draw-farm-boundary").textContent="Drawing outer boundary…";
    new L.Draw.Polygon(map,{allowIntersection:false,showArea:true,shapeOptions:{color:"#2563eb",weight:3,fillColor:"#93c5fd",fillOpacity:0.13}}).enable();
  }
  function startPlotDrawing(){
    if(!currentFarm || !map){status("vf-plot-status","Create or select a virtual farm first.",true);return;}
    if(!currentFarm.boundary){status("vf-boundary-status","Draw and save the outer farm boundary before drawing plots.",true);return;}
    farmBoundaryMode=false;
    status("vf-boundary-status","Draw a plot inside the outer farm boundary; double-click to finish the polygon.");
    new L.Draw.Polygon(map,{allowIntersection:false,showArea:true,shapeOptions:{color:"#287c55",weight:2,fillOpacity:0.18}}).enable();
  }
  function togglePlaceAsset(){
    if(!currentFarm){status("vf-asset-status","Select a virtual farm first.",true);return;}
    if(!currentFarm.boundary){status("vf-asset-status","Draw and save the outer farm boundary before placing infrastructure.",true);return;}
    placeAssetMode=!placeAssetMode;$("vf-place-asset").textContent=placeAssetMode?"Click the map to place…":"Place asset on map";
    status("vf-asset-location",placeAssetMode?"Click on the farm map to set the asset's location.":"Asset placement cancelled.");
  }
  async function saveAsset(e){
    e.preventDefault();if(!currentFarm)return;
    const lat=$("vf-asset-lat").value,lon=$("vf-asset-lon").value;
    if(!lat||!lon){status("vf-asset-status","Place the asset on the map first.",true);return;}
    const payload={asset_type:$ ("vf-asset-type").value,asset_name:$ ("vf-asset-name").value,capacity_or_size:$ ("vf-asset-capacity").value,latitude:lat,longitude:lon};
    try{const data=await api(`/api/virtual-farms/${currentFarm.virtual_farm_id}/assets`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      $("virtual-asset-form").reset();$("vf-asset-lat").value="";$("vf-asset-lon").value="";pendingAssetMarker=null;status("vf-asset-status","Infrastructure asset saved.");renderFarm(data.farm);
    }catch(err){status("vf-asset-status",err.message,true);}
  }

  async function uploadSoilReport(e){
    e.preventDefault();
    if(!currentFarm){status("soil-report-status","Create or select your farm before uploading a report.",true);return;}
    const file=$("soil-report-file").files[0];
    if(!file){status("soil-report-status","Choose a report file first.",true);return;}
    const form=new FormData(); form.append("soil_report",file);
    form.append("report_source",$("soil-report-source").value);
    form.append("report_date",$("soil-report-date").value);
    form.append("notes",$("soil-report-notes").value);
    try{const response=await fetch(`/api/virtual-farms/${currentFarm.virtual_farm_id}/soil-reports`,{method:"POST",body:form});const data=await response.json();if(!response.ok||!data.ok)throw new Error(data.error||"Upload failed");status("soil-report-status",data.message);$("soil-report-upload-form").reset();loadSoilReports();}
    catch(err){status("soil-report-status",err.message,true);}
  }
  async function loadSoilReports(){
    if(!currentFarm)return;
    try{const response=await fetch(`/api/virtual-farms/${currentFarm.virtual_farm_id}/soil-reports`);const data=await response.json();if(!response.ok||!data.ok)throw new Error(data.error||"Could not load reports");
      $("soil-report-list").innerHTML=data.reports.length?`<strong>Saved reports</strong><ul>${data.reports.map(r=>`<li>${esc(r.original_filename)} · ${esc(r.report_source)}${r.report_date?` · ${esc(r.report_date)}`:""}</li>`).join("")}</ul>`:"No soil reports uploaded for this farm yet.";
    }catch(err){$("soil-report-list").textContent=err.message;}
  }

  $("create-farm-from-region").addEventListener("click",createFarmFromRegion);
  $("vf-use-location").addEventListener("click",useCurrentDeviceLocation);
  $("virtual-farm-create-form").addEventListener("submit",createFarm);
  $("virtual-plot-form").addEventListener("submit",savePlot);
  $("vf-clear-polygon").addEventListener("click",clearPending);
  $("vf-season").addEventListener("change",updateSeasonNote);
  $("vf-select").addEventListener("change",e=>loadFarm(Number(e.target.value)).catch(err=>status("vf-current-summary",err.message,true)));
  $("vf-place-asset").addEventListener("click",togglePlaceAsset);
  $("vf-draw-farm-boundary").addEventListener("click",toggleFarmBoundary);
  $("vf-draw-plot").addEventListener("click",startPlotDrawing);
  $("virtual-asset-form").addEventListener("submit",saveAsset);
  $("soil-report-upload-form").addEventListener("submit",uploadSoilReport);
  const initialiseVirtualFarms = () => loadFarmList().catch(err=>status("vf-current-summary",`Virtual farm records could not be loaded: ${err.message}. Please contact the service team.`,true));
  if (window.appAuthReady) window.appAuthReady.then(user => { if (user) initialiseVirtualFarms(); });
  else initialiseVirtualFarms();
})();
