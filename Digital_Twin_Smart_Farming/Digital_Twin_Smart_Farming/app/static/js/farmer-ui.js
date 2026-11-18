(() => {
  "use strict";

  const translations = {
    en: {
      brand_subtitle: "Village agriculture support, made simple",
      nav_field_team: "Field team", nav_soil_lab: "Soil lab", nav_farmer_card: "Farmer card",
      language_label: "Language",
      nav_home: "Village desk",
      nav_location: "My area",
      nav_farm: "My farm",
      nav_outlook: "Farm predictions",
      nav_insights: "Predictions & research",
      hero_kicker: "NAMASTE · WELCOME TO YOUR FARM SPACE",
      hero_title: "Your farm, made easier to understand.",
      hero_desc: "Start with your village or district. Add your farm and fields. Keep local conditions and farm records together in one place.",
      hero_primary: "Start with my village",
      hero_secondary: "I have already added my area",
      start_eyebrow: "GET STARTED IN 3 SIMPLE STEPS",
      start_title: "You do not need to be a computer expert.",
      start_desc: "Follow these steps at your own pace. You can save your work and come back later.",
      step_one: "STEP 1", step_two: "STEP 2", step_three: "STEP 3",
      card_location_title: "Find your village",
      card_location_desc: "Enter your village, town or district to see local weather, soil and farming information.",
      card_location_action: "Find my area",
      card_farm_title: "Add your farm",
      card_farm_desc: "Give your farm a name and size. Then draw your fields and add the crops you grow.",
      card_farm_action: "Open my farm",
      card_report_title: "View reports",
      card_report_desc: "Review farm records and explore the sample research forecasts. Sample data is clearly marked.",
      card_report_action: "View reports",
      trust_simple: "Simple steps",
      trust_india: "Designed around Indian crops and seasons",
      trust_control: "You enter and manage your farm details",
      help_title: "Need help getting started?",
      help_desc: "Ask a family member, local extension worker or agriculture officer to help with the first location and farm setup. You can leave optional soil-test details blank until you have a lab report or Soil Health Card.",
      language_note: "Core navigation and getting-started guidance are available in English and Hindi. Detailed scientific reports currently use English technical terms.",
      area_eyebrow: "STEP 1 · YOUR LOCAL AREA",
      area_title: "Find local farming information",
      area_desc: "Search by village, town or district. You do not need to enter GPS coordinates.",
      region_placeholder: "Enter village, town or district name",
      find_area: "Find my area",
      farm_eyebrow: "STEP 2 · YOUR FARM AND FIELDS",
      farm_title: "Add your farm",
      farm_desc: "Start with a few basic details. You can add maps, crops and optional soil information one step at a time."
    },
    hi: {
      brand_subtitle: "गाँव में खेती की आसान सहायता",
      nav_home: "गाँव सेवा केंद्र", nav_field_team: "मैदानी टीम", nav_soil_lab: "मिट्टी जाँच", nav_farmer_card: "किसान कार्ड",
      language_label: "भाषा",
      nav_location: "मेरा क्षेत्र",
      nav_farm: "मेरा खेत",
      nav_outlook: "खेत का पूर्वानुमान",
      nav_insights: "पूर्वानुमान और शोध",
      hero_kicker: "नमस्ते · आपके खेत के डिजिटल साथी में स्वागत है",
      hero_title: "अपने खेत को समझना अब और आसान।",
      hero_desc: "अपने गाँव या ज़िले से शुरुआत करें। अपना खेत और खेत के हिस्से जोड़ें। स्थानीय जानकारी और खेती के रिकॉर्ड एक ही जगह रखें।",
      hero_primary: "अपने गाँव से शुरुआत करें",
      hero_secondary: "मैंने अपना क्षेत्र पहले ही जोड़ा है",
      start_eyebrow: "3 आसान चरणों में शुरुआत करें",
      start_title: "कंप्यूटर विशेषज्ञ होना ज़रूरी नहीं है।",
      start_desc: "अपनी सुविधा से ये चरण पूरे करें। जानकारी सहेजकर बाद में भी जारी रख सकते हैं।",
      step_one: "चरण 1", step_two: "चरण 2", step_three: "चरण 3",
      card_location_title: "अपना गाँव खोजें",
      card_location_desc: "गाँव, कस्बे या ज़िले का नाम डालें। स्थानीय मौसम, मिट्टी और खेती की जानकारी देखें।",
      card_location_action: "मेरा क्षेत्र खोजें",
      card_farm_title: "अपना खेत जोड़ें",
      card_farm_desc: "खेत का नाम और रकबा भरें। फिर खेत के हिस्से का नक्शा और उगाई जाने वाली फसल जोड़ें।",
      card_farm_action: "मेरा खेत खोलें",
      card_report_title: "रिपोर्ट देखें",
      card_report_desc: "खेत के रिकॉर्ड देखें और नमूना शोध पूर्वानुमान समझें। नमूना डेटा को अलग दिखाया गया है।",
      card_report_action: "रिपोर्ट देखें",
      trust_simple: "आसान चरण",
      trust_india: "भारतीय फसलों और मौसम के अनुसार",
      trust_control: "खेत की जानकारी आप स्वयं भरें और संभालें",
      help_title: "शुरुआत में मदद चाहिए?",
      help_desc: "पहली बार क्षेत्र और खेत की जानकारी भरने में परिवार के सदस्य, कृषि सहायक या कृषि अधिकारी की मदद लें। मिट्टी की जाँच की रिपोर्ट या Soil Health Card मिलने तक वैकल्पिक मिट्टी के आँकड़े खाली छोड़ सकते हैं।",
      language_note: "मुख्य मेनू और शुरुआत की जानकारी हिंदी और अंग्रेज़ी में उपलब्ध है। विस्तृत वैज्ञानिक रिपोर्ट में अभी अंग्रेज़ी तकनीकी शब्द हैं।",
      area_eyebrow: "चरण 1 · आपका क्षेत्र",
      area_title: "अपने क्षेत्र की खेती की जानकारी खोजें",
      area_desc: "गाँव, कस्बे या ज़िले से खोजें। GPS निर्देशांक भरने की ज़रूरत नहीं है।",
      region_placeholder: "गाँव, कस्बे या ज़िले का नाम लिखें",
      find_area: "मेरा क्षेत्र खोजें",
      farm_eyebrow: "चरण 2 · आपका खेत और खेत के हिस्से",
      farm_title: "अपना खेत जोड़ें",
      farm_desc: "कुछ ज़रूरी जानकारी से शुरुआत करें। नक्शा, फसल और मिट्टी की वैकल्पिक जानकारी धीरे-धीरे जोड़ सकते हैं।"
    }
  };

  const voiceButton = document.getElementById("voice-help-button");
  if (voiceButton) voiceButton.addEventListener("click", () => {
    if (!("speechSynthesis" in window)) { alert("Voice reading is not supported by this browser. Try Safari or Chrome."); return; }
    if (window.speechSynthesis.speaking) { window.speechSynthesis.cancel(); voiceButton.textContent = "🔊 Read aloud"; return; }
    const active = document.querySelector("[data-app-view].is-active");
    const heading = active?.querySelector("h1")?.innerText || "Smart Farming";
    const description = active?.querySelector(".view-heading p:not(.eyebrow), .welcome-copy > p:not(.welcome-kicker)")?.innerText || "Welcome to your farm dashboard.";
    const language = document.documentElement.lang === "hi" ? "hi-IN" : "en-IN";
    const utterance = new SpeechSynthesisUtterance(`${heading}. ${description}`);
    utterance.lang = language; utterance.rate = 0.9;
    utterance.onend = () => { voiceButton.textContent = "🔊 Read aloud"; };
    voiceButton.textContent = "⏹ Stop reading"; window.speechSynthesis.speak(utterance);
  });

  function applyLanguage(language) {
    const lang = translations[language] ? language : "en";
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const value = translations[lang][element.dataset.i18n];
      if (value) element.textContent = value;
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      const value = translations[lang][element.dataset.i18nPlaceholder];
      if (value) element.setAttribute("placeholder", value);
    });
    const chooser = document.getElementById("language-switch");
    if (chooser && chooser.value !== lang) chooser.value = lang;
    try { localStorage.setItem("smart-farming-language", lang); } catch (_) { /* storage may be disabled */ }
  }

  function setFarmerView(viewName, options = {}) {
    const valid = new Set(["home", "field-team", "soil-lab", "farmer-card", "location", "farm", "outlook", "insights"]);
    const view = valid.has(viewName) ? viewName : "home";
    document.querySelectorAll("[data-app-view]").forEach((panel) => {
      const active = panel.dataset.appView === view;
      panel.classList.toggle("is-active", active);
      panel.setAttribute("aria-hidden", String(!active));
    });
    document.querySelectorAll("[data-view-target]").forEach((button) => {
      const active = button.dataset.viewTarget === view;
      button.classList.toggle("is-active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    window.dispatchEvent(new CustomEvent("farmer-view-shown", { detail: view }));
    if (view === "insights") {
      window.setTimeout(() => {
        document.querySelectorAll(".js-plotly-plot").forEach((chart) => {
          if (window.Plotly) window.Plotly.Plots.resize(chart);
        });
      }, 80);
    }
    if (!options.keepScroll) window.scrollTo({ top: 0, behavior: "smooth" });
  }

  window.setFarmerView = setFarmerView;
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => setFarmerView(button.dataset.viewTarget));
  });
  document.querySelectorAll("[data-open-view]").forEach((button) => {
    button.addEventListener("click", () => setFarmerView(button.dataset.openView));
  });

  document.querySelectorAll("details").forEach((details) => {
    details.addEventListener("toggle", () => {
      if (!details.open) return;
      window.setTimeout(() => {
        details.querySelectorAll(".js-plotly-plot").forEach((chart) => {
          if (window.Plotly) window.Plotly.Plots.resize(chart);
        });
      }, 80);
    });
  });

  const languageSelect = document.getElementById("language-switch");
  if (languageSelect) languageSelect.addEventListener("change", () => applyLanguage(languageSelect.value));
  let savedLanguage = "en";
  try { savedLanguage = localStorage.getItem("smart-farming-language") || "en"; } catch (_) { /* storage may be disabled */ }
  applyLanguage(savedLanguage);
  setFarmerView("home", { keepScroll: true });
})();
