(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const api = async (url, options = {}) => {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok || data.ok === false) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  };
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#39;"}[ch]));
  const fmt = (value, digits = 2) => value === null || value === undefined || value === "" ? "Not recorded" : Number(value).toFixed(digits);
  const dateFmt = value => value ? new Date(String(value).replace(" ", "T")).toLocaleString() : "Not recorded";
  const todayISO = () => {
    const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  };
  let farmers = [];
  let samples = [];
  let virtualFarms = [];
  let lastFarmerDetail = null;

  function status(id, message, error = false) {
    const node = $(id); if (!node) return;
    node.textContent = message;
    node.classList.toggle("is-error", Boolean(error));
    node.classList.toggle("is-success", !error && Boolean(message));
  }

  async function loadSummary() {
    const data = await api("/api/service/summary");
    const map = {
      "service-farmer-count": data.summary.farmers,
      "service-pending-count": data.summary.pending_samples,
      "service-verified-count": data.summary.verified_samples,
      "service-visits-count": data.summary.scheduled_visits
    };
    Object.entries(map).forEach(([id, value]) => { if ($(id)) $(id).textContent = Number(value).toLocaleString(); });
  }

  function fillFarmerSelectors() {
    ["ss-farmer", "service-farmer-select"].forEach(id => {
      const select = $(id); if (!select) return;
      const previous = select.value;
      select.innerHTML = `<option value="">${id === "ss-farmer" ? "Choose a farmer" : "Select a farmer"}</option>`;
      farmers.forEach(f => {
        const option = document.createElement("option");
        option.value = f.farmer_id;
        option.textContent = `${f.farmer_name} · ${f.village}, ${f.district} (${f.farmer_code})`;
        select.appendChild(option);
      });
      if (previous && farmers.some(f => String(f.farmer_id) === previous)) select.value = previous;
    });
  }

  async function loadVirtualFarmOptions() {
    const data = await api("/api/virtual-farms");
    virtualFarms = data.farms || [];
    const select = $("sf-vfarm");
    if (!select) return;
    const previous = select.value;
    select.innerHTML = '<option value="">Not mapped yet</option>';
    virtualFarms.forEach(farm => {
      const option = document.createElement("option");
      option.value = farm.virtual_farm_id;
      option.textContent = `${farm.farm_name} · ${farm.district}, ${farm.state}`;
      select.appendChild(option);
    });
    if (previous && virtualFarms.some(f => String(f.virtual_farm_id) === previous)) select.value = previous;
  }

  async function loadFarmers() {
    const data = await api("/api/service/farmers");
    farmers = data.farmers || [];
    fillFarmerSelectors();
    renderFarmerList();
  }

  function renderFarmerList() {
    const node = $("service-farmers-list"); if (!node) return;
    if (!farmers.length) {
      node.innerHTML = `<div class="service-empty-inline"><span>👨‍🌾</span><strong>No farmer records yet</strong><p>Register your first farmer during a village visit.</p></div>`;
      return;
    }
    node.innerHTML = farmers.slice(0, 8).map(f => `<article class="service-record-row"><div class="service-record-avatar">${esc((f.farmer_name || "F").trim().charAt(0).toUpperCase())}</div><div class="service-record-main"><strong>${esc(f.farmer_name)}</strong><span>${esc(f.village)}, ${esc(f.district)}, ${esc(f.state)}</span><small>${esc(f.farmer_code)} · ${esc(f.primary_crop || "Crop not recorded")}</small></div><span class="service-status-pill">${esc(f.latest_sample_status || "No sample yet")}</span><button type="button" class="mini-action" data-show-farmer="${Number(f.farmer_id)}">View card</button></article>`).join("");
    node.querySelectorAll("[data-show-farmer]").forEach(button => button.addEventListener("click", () => {
      if (window.setFarmerView) window.setFarmerView("farmer-card");
      $("service-farmer-select").value = button.dataset.showFarmer;
      loadFarmerCard(button.dataset.showFarmer);
    }));
  }

  async function loadSamples() {
    const data = await api("/api/service/samples");
    samples = data.samples || [];
    renderSampleQueue();
    const select = $("sl-sample");
    if (select) {
      const previous = select.value;
      select.innerHTML = `<option value="">Choose a sample from the queue</option>`;
      samples.forEach(sample => {
        const option = document.createElement("option");
        option.value = sample.sample_id;
        option.textContent = `${sample.sample_code} · ${sample.farmer_name} · ${sample.status}`;
        select.appendChild(option);
      });
      if (previous && samples.some(x => String(x.sample_id) === previous)) select.value = previous;
      if ($("sl-sample-code") && select.value) {
        const chosen = samples.find(x => String(x.sample_id) === select.value);
        $("sl-sample-code").value = chosen?.sample_code || "";
      }
    }
  }

  function renderSampleQueue() {
    const node = $("service-sample-queue"); if (!node) return;
    if (!samples.length) {
      node.innerHTML = `<div class="service-empty-inline"><span>🧪</span><strong>No samples registered</strong><p>Field staff can create a sample ID in the Field Team workspace.</p></div>`;
      return;
    }
    node.innerHTML = samples.map(s => {
      const verified = Number(s.lab_verified) === 1;
      return `<button type="button" class="service-queue-card ${verified ? "is-verified" : ""}" data-select-sample="${Number(s.sample_id)}"><span class="queue-code">${esc(s.sample_code)}</span><strong>${esc(s.farmer_name)}</strong><span>${esc(s.village)}, ${esc(s.district)}</span><small>Collected ${esc(dateFmt(s.collected_at))}</small><em>${verified ? "✓ Verified" : esc(s.status)}</em></button>`;
    }).join("");
    node.querySelectorAll("[data-select-sample]").forEach(button => button.addEventListener("click", () => {
      $("sl-sample").value = button.dataset.selectSample;
      $("sl-sample").scrollIntoView({ behavior: "smooth", block: "center" });
    }));
  }

  async function refreshAll() {
    try { await Promise.all([loadSummary(), loadFarmers(), loadSamples(), loadVirtualFarmOptions()]); }
    catch (error) {
      status("sf-status", `Could not load service records: ${error.message}`, true);
    }
  }

  async function registerFarmer(event) {
    event.preventDefault();
    const button = event.submitter; button.disabled = true;
    status("sf-status", "Saving farmer and visit…");
    const payload = {
      farmer_name: $("sf-name").value.trim(), mobile: $("sf-mobile").value.trim(),
      preferred_language: $("sf-language").value, village: $("sf-village").value.trim(),
      district: $("sf-district").value.trim(), state: $("sf-state").value,
      farm_name: $("sf-farm").value.trim(), farm_area_sqft: $("sf-area").value,
      primary_crop: $("sf-crop").value.trim(), virtual_farm_id: $("sf-vfarm").value,
      farm_latitude: $("sf-lat").value,
      farm_longitude: $("sf-lon").value, officer_name: $("sf-officer").value.trim(),
      visit_date: $("sf-visit-date").value, visit_purpose: $("sf-purpose").value,
      notes: $("sf-notes").value.trim(), consent_recorded: $("sf-consent").checked
    };
    try {
      const data = await api("/api/service/farmers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      status("sf-status", `${data.message} Farmer code: ${data.farmer_code}`);
      const activationCard = $("sf-activation-card");
      if (activationCard && data.activation_code) {
        activationCard.hidden = false;
        activationCard.innerHTML = `<span class="sample-created-icon">✓</span><div><small>HAND THIS ONE-TIME ACTIVATION SLIP DIRECTLY TO THE FARMER</small><strong>Farmer code: ${esc(data.farmer_code)}</strong><strong>Activation code: ${esc(data.activation_code)}</strong><p>Valid for 7 days. The farmer uses their mobile number, these codes and a new password on the sign-in screen. Do not share the code in a public group.</p></div><button type="button" class="soft-button" data-print-activation>Print slip</button>`;
        activationCard.querySelector("[data-print-activation]").addEventListener("click", () => window.print());
      } else if (activationCard) {
        activationCard.hidden = true;
        activationCard.textContent = "";
      }
      await refreshAll();
      $("ss-farmer").value = data.farmer_id;
      $("sf-consent").checked = false;
    } catch (error) { status("sf-status", error.message, true); }
    finally { button.disabled = false; }
  }

  async function registerSample(event) {
    event.preventDefault();
    const button = event.submitter; button.disabled = true;
    status("ss-status", "Creating sample ID…");
    const payload = {
      farmer_id: $("ss-farmer").value, collected_by: $("ss-collector").value.trim(),
      collected_at: $("ss-collected-at").value, sample_description: $("ss-description").value.trim(),
      assigned_lab_organization: $("ss-lab-destination").value.trim(),
      latitude: $("ss-lat").value, longitude: $("ss-lon").value
    };
    try {
      const data = await api("/api/service/samples", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      status("ss-status", data.message);
      $("ss-created-card").classList.remove("hidden");
      $("ss-created-card").innerHTML = `<span class="sample-created-icon">✓</span><div><small>WRITE THIS CODE ON THE SAMPLE BAG</small><strong>${esc(data.sample_code)}</strong><p>${esc(data.message)}</p></div><div class="sample-qr" aria-label="QR code for this sample"></div><button type="button" data-copy-sample-code class="soft-button">Copy code</button>`;
      if (window.QRCode) new window.QRCode($("ss-created-card").querySelector(".sample-qr"), { text: data.sample_code, width: 96, height: 96, correctLevel: window.QRCode.CorrectLevel.M });
      else $("ss-created-card").querySelector(".sample-qr").textContent = "QR unavailable";
      $("ss-created-card").querySelector("[data-copy-sample-code]").addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(data.sample_code); status("ss-status", "Sample code copied."); }
        catch (_) { status("ss-status", `Sample code: ${data.sample_code}`); }
      });
      await refreshAll();
      $("ss-farmer").value = payload.farmer_id;
    } catch (error) { status("ss-status", error.message, true); }
    finally { button.disabled = false; }
  }

  async function saveLabResults(event) {
    event.preventDefault();
    const button = event.submitter; button.disabled = true;
    status("sl-status", "Saving measured laboratory values…");
    const sampleId = $("sl-sample").value;
    if (!sampleId) { status("sl-status", "Choose a sample first.", true); button.disabled = false; return; }
    const form = new FormData();
    form.set("lab_name", $("sl-lab").value.trim()); form.set("tested_by", $("sl-technician").value.trim());
    form.set("tested_at", $("sl-date").value ? `${$("sl-date").value}T12:00` : "");
    form.set("soil_ph", $("sl-ph").value); form.set("soil_ec_ds_m", $("sl-ec").value);
    form.set("organic_carbon_pct", $("sl-oc").value); form.set("available_n_kg_ha", $("sl-n").value);
    form.set("available_p_kg_ha", $("sl-p").value); form.set("available_k_kg_ha", $("sl-k").value);
    form.set("lab_notes", $("sl-notes").value.trim()); form.set("lab_verified", $("sl-verified").checked ? "yes" : "no");
    if ($("sl-report").files[0]) form.set("lab_report", $("sl-report").files[0]);
    try {
      const data = await api(`/api/service/samples/${encodeURIComponent(sampleId)}/results`, { method: "POST", body: form });
      status("sl-status", data.message);
      await refreshAll();
      $("sl-sample").value = sampleId;
    } catch (error) { status("sl-status", error.message, true); }
    finally { button.disabled = false; }
  }

  async function loadFarmerCard(farmerId) {
    const node = $("farmer-card-content");
    if (!farmerId) {
      node.innerHTML = `<div class="farmer-card-empty"><span>🌾</span><h2>Select a farmer to view their card</h2><p>Farm details and verified soil results will appear here.</p></div>`;
      $("farmer-card-print").disabled = true; $("farmer-card-read").disabled = true; lastFarmerDetail = null; return;
    }
    node.innerHTML = `<div class="farmer-card-empty"><span>⏳</span><p>Loading farmer record…</p></div>`;
    try {
      const data = await api(`/api/service/farmers/${encodeURIComponent(farmerId)}`);
      lastFarmerDetail = data;
      const f = data.farmer, s = data.latest_sample;
      const verified = s && Number(s.lab_verified) === 1;
      const resultMarkup = verified ? `
        <div class="farmer-results-grid">
          <div><span>Soil pH</span><strong>${esc(fmt(s.soil_ph))}</strong></div>
          <div><span>Electrical conductivity (EC)</span><strong>${esc(fmt(s.soil_ec_ds_m, 3))} dS/m</strong></div>
          <div><span>Organic carbon</span><strong>${esc(fmt(s.organic_carbon_pct, 3))}%</strong></div>
          <div><span>Available nitrogen</span><strong>${esc(fmt(s.available_n_kg_ha, 1))} kg/ha</strong></div>
          <div><span>Available phosphorus</span><strong>${esc(fmt(s.available_p_kg_ha, 1))} kg/ha</strong></div>
          <div><span>Available potassium</span><strong>${esc(fmt(s.available_k_kg_ha, 1))} kg/ha</strong></div>
        </div>
        <div class="farmer-plain-note"><strong>What this means</strong><p>These are the values recorded by ${esc(s.lab_name || "the laboratory")}. Please ask the agriculture officer or KVK expert to explain what they mean for this crop and field. This application does not generate a fertiliser dose from these values.</p></div>` : `
        <div class="farmer-no-results"><strong>${s ? (Number(s.lab_verified) ? "Results saved" : "Soil test is not yet verified") : "No soil sample registered yet"}</strong><p>${s ? "The field team can check with the laboratory and return with the signed report. Unverified values are not displayed as confirmed." : "Ask the field team to collect a soil sample and give you its tracking code."}</p></div>`;
      node.innerHTML = `
        <article class="farmer-print-card">
          <div class="farmer-print-head"><div><p class="eyebrow">DIGITAL TWIN · FARMER INFORMATION CARD</p><h2>${esc(f.farmer_name)}</h2><p>${esc(f.village)}, ${esc(f.district)}, ${esc(f.state)}</p>${String(f.farmer_code).startsWith("DEMO-") ? '<span class="demo-record-tag">DEMO DATA ONLY</span>' : ""}</div><span class="farmer-card-leaf">🌱</span></div>
          <div class="farmer-quick-facts"><div><span>Farmer code</span><strong>${esc(f.farmer_code)}</strong></div><div><span>Farm</span><strong>${esc(f.farm_name || "Not recorded")}</strong></div><div><span>Farm area</span><strong>${f.farm_area_ha ? `${Math.round(Number(f.farm_area_ha) * 107639.104167).toLocaleString()} sq ft` : "Not recorded"}</strong></div><div><span>Main crop</span><strong>${esc(f.primary_crop || "Not recorded")}</strong></div><div><span>Preferred language</span><strong>${esc(f.preferred_language)}</strong></div><div><span>Mapped Digital Twin</span><strong>${f.virtual_farm_id ? "Linked" : "Not linked"}</strong></div><div><span>Farm GPS</span><strong>${f.farm_latitude && f.farm_longitude ? `${esc(f.farm_latitude)}, ${esc(f.farm_longitude)}` : "Not recorded"}</strong></div></div>
          <div class="farmer-sample-head"><div><p class="eyebrow">SOIL SAMPLE</p><h3>${esc(s ? s.sample_code : "No sample yet")}</h3></div><span class="farmer-verification ${verified ? "verified" : "pending"}">${verified ? "✓ LAB VERIFIED" : s ? "AWAITING LAB / VERIFICATION" : "NOT COLLECTED"}</span></div>
          ${s ? `<p class="farmer-sample-meta">Collected ${esc(dateFmt(s.collected_at))} · By ${esc(s.collected_by)}${s.lab_name ? ` · ${esc(s.lab_name)}` : ""}</p>${s.report_stored_filename ? `<p><a class="service-report-link" href="/api/service/samples/${Number(s.sample_id)}/report" target="_blank" rel="noopener">📄 Open attached laboratory report</a></p>` : ""}` : ""}
          ${resultMarkup}
          <div class="farmer-card-footer"><strong>Need help?</strong><p>Ask your village agriculture worker, district agriculture office or KVK for an explanation and next steps. Keep your signed Soil Health Card or laboratory report.</p><small>Record generated ${esc(new Date().toLocaleDateString())} · ${f.created_by === "DEMO DATA SEED" ? "Synthetic demonstration record; no actual farmer or consent process." : "Farmer details recorded with consent."}</small></div>
        </article>`;
      $("farmer-card-print").disabled = false;
      $("farmer-card-read").disabled = false;
    } catch (error) {
      node.innerHTML = `<div class="farmer-card-empty"><span>⚠️</span><p>${esc(error.message)}</p></div>`;
      $("farmer-card-print").disabled = true;
      $("farmer-card-read").disabled = true;
    }
  }

  function captureFarmLocation() {
    const button = $("service-use-farm-location");
    if (!navigator.geolocation) { status("sf-status", "Location is not available in this browser.", true); return; }
    button.disabled = true; button.textContent = "Getting farm location…";
    navigator.geolocation.getCurrentPosition(position => {
      $("sf-lat").value = position.coords.latitude.toFixed(6);
      $("sf-lon").value = position.coords.longitude.toFixed(6);
      status("sf-status", "Farm location captured. Check that you are standing at the correct farm.");
      button.disabled = false; button.textContent = "📍 Capture farm location (with permission)";
    }, error => {
      status("sf-status", error.code === 1 ? "Location permission was not granted." : "Could not get the location. You can leave it blank.", true);
      button.disabled = false; button.textContent = "📍 Capture farm location (with permission)";
    }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 });
  }

  function captureLocation() {
    const button = $("service-use-location");
    if (!navigator.geolocation) { status("ss-status", "Location is not available in this browser.", true); return; }
    button.disabled = true; button.textContent = "Getting location…";
    navigator.geolocation.getCurrentPosition(position => {
      $("ss-lat").value = position.coords.latitude.toFixed(6);
      $("ss-lon").value = position.coords.longitude.toFixed(6);
      status("ss-status", "Sample location captured. Check it before saving.");
      button.disabled = false; button.textContent = "📍 Capture device location (with permission)";
    }, error => {
      status("ss-status", error.code === 1 ? "Location permission was not granted." : "Could not get the location. You can leave it blank.", true);
      button.disabled = false; button.textContent = "📍 Capture device location (with permission)";
    }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 });
  }

  $("service-farmer-form")?.addEventListener("submit", registerFarmer);
  $("service-sample-form")?.addEventListener("submit", registerSample);
  $("service-lab-form")?.addEventListener("submit", saveLabResults);
  $("service-dashboard-refresh")?.addEventListener("click", refreshAll);
  $("service-farmers-refresh")?.addEventListener("click", loadFarmers);
  $("service-samples-refresh")?.addEventListener("click", loadSamples);
  $("service-farmer-select")?.addEventListener("change", e => loadFarmerCard(e.target.value));
  $("sl-sample-code")?.addEventListener("input", event => {
    const code = event.target.value.trim().toUpperCase();
    const match = samples.find(sample => String(sample.sample_code).toUpperCase() === code);
    if (match) $("sl-sample").value = String(match.sample_id);
  });
  $("sl-sample")?.addEventListener("change", event => {
    const match = samples.find(sample => String(sample.sample_id) === event.target.value);
    if ($("sl-sample-code")) $("sl-sample-code").value = match?.sample_code || "";
  });
  $("farmer-card-refresh")?.addEventListener("click", async () => {
    await refreshAll();
    if ($("service-farmer-select").value) await loadFarmerCard($("service-farmer-select").value);
  });
  $("farmer-card-print")?.addEventListener("click", () => { if (lastFarmerDetail) window.print(); });
  $("service-use-location")?.addEventListener("click", captureLocation);
  $("service-use-farm-location")?.addEventListener("click", captureFarmLocation);
  $("farmer-card-read")?.addEventListener("click", () => {
    if (!lastFarmerDetail || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const f = lastFarmerDetail.farmer;
    const s = lastFarmerDetail.latest_sample;
    const languageCodes = { Hindi: "hi-IN", Marathi: "mr-IN", Punjabi: "pa-IN", Gujarati: "gu-IN", Bengali: "bn-IN", Tamil: "ta-IN", Telugu: "te-IN", Kannada: "kn-IN", Odia: "or-IN", English: "en-IN" };
    const values = s && Number(s.lab_verified) === 1 ? ` Soil pH ${s.soil_ph ?? "not recorded"}. Electrical conductivity ${s.soil_ec_ds_m ?? "not recorded"}. Organic carbon ${s.organic_carbon_pct ?? "not recorded"} percent. Ask your agriculture officer or KVK to explain these laboratory values for your crop.` : ` Soil sample status: ${s?.status || "not collected"}. Please ask your field worker for the next update.`;
    const utterance = new SpeechSynthesisUtterance(`${f.farmer_name}. ${f.village}, ${f.district}, ${f.state}. Farm: ${f.farm_name || "not recorded"}. Preferred language: ${f.preferred_language}.${values}`);
    utterance.lang = languageCodes[f.preferred_language] || "hi-IN"; utterance.rate = 0.88;
    window.speechSynthesis.speak(utterance);
  });
  $("sf-visit-date").value = todayISO();
  $("ss-collected-at").value = todayISO();
  $("sl-date").value = todayISO().slice(0, 10);
  const initialiseServiceDesk = async (user) => {
    if (!user) return;
    if ($("sf-officer") && !$ ("sf-officer").value) $("sf-officer").value = user.display_name || "";
    if ($("ss-collector") && !$ ("ss-collector").value) $("ss-collector").value = user.display_name || "";
    if ($("sl-technician") && !$ ("sl-technician").value) $("sl-technician").value = user.display_name || "";
    await refreshAll();
    if (user.role === "farmer" && farmers.length && window.setFarmerView) {
      const ownFarmer = farmers[0];
      if ($("service-farmer-select")) $("service-farmer-select").value = String(ownFarmer.farmer_id);
      window.setFarmerView("farmer-card", { keepScroll: true });
      await loadFarmerCard(ownFarmer.farmer_id);
    }
  };
  if (window.appAuthReady) window.appAuthReady.then(initialiseServiceDesk);
  else initialiseServiceDesk(window.APP_CURRENT_USER || null);
})();
