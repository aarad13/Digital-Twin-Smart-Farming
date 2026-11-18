from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "app/templates/index.html"


class InterfaceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.view_targets = []
        self.views = []
        self.details_count = 0
        self.details_open = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if attrs.get("data-view-target"):
            self.view_targets.append(attrs["data-view-target"])
        if attrs.get("data-app-view"):
            self.views.append(attrs["data-app-view"])
        if tag == "details":
            self.details_count += 1


def parse_html():
    parser = InterfaceParser()
    parser.feed(HTML.read_text(encoding="utf-8"))
    return parser


def test_assisted_service_navigation_is_simple_and_legacy_tools_remain_available():
    parser = parse_html()
    assert set(parser.view_targets) == {"home", "field-team", "soil-lab", "farmer-card", "location", "farm", "outlook", "insights"}
    assert set(parser.views) == {"home", "field-team", "soil-lab", "farmer-card", "location", "farm", "outlook", "insights"}


def test_farmer_interface_has_unique_ids_and_keeps_required_api_hooks():
    parser = parse_html()
    duplicates = [key for key, count in Counter(parser.ids).items() if count > 1]
    assert not duplicates
    required_ids = {
        "region-search-form", "region-results", "virtual-farm-create-form",
        "virtual-farm-map", "virtual-plot-form", "virtual-asset-form",
        "farm-select", "forecast-button", "forecast-history", "language-switch",
        "service-farmer-form", "service-sample-form", "service-lab-form", "service-farmer-select",
        "farmer-card-content", "service-sample-queue", "sf-consent", "sl-sample-code",
        "farm-outlook-select", "farm-outlook-run", "farm-outlook-result", "farm-outlook-moisture-chart",
        "farm-outlook-weather-chart", "farm-outlook-crop-history", "farm-outlook-lab-record",
    }
    assert required_ids.issubset(set(parser.ids))


def test_longer_technical_sections_are_collapsible():
    html = HTML.read_text(encoding="utf-8")
    assert '<details class="farmer-more-details">' in html
    assert 'class="farmer-more-details admin-details"' in html
    assert '<details class="vf-advanced-fields">' in html


def test_english_hindi_first_run_copy_exists():
    script = (ROOT / "app/static/js/farmer-ui.js").read_text(encoding="utf-8")
    assert 'hi: {' in script
    assert 'hero_title:' in script
    assert 'area_title:' in script


def test_device_location_is_user_initiated_and_not_automatic():
    html = HTML.read_text(encoding="utf-8")
    script = (ROOT / "app/static/js/virtual-farm.js").read_text(encoding="utf-8")
    assert 'id="vf-use-location"' in html
    assert 'addEventListener("click",useCurrentDeviceLocation)' in script
    assert 'navigator.geolocation.getCurrentPosition' in script
    assert 'enableHighAccuracy:true' in script


def test_assisted_service_has_clear_data_consent_and_provenance_language():
    html = HTML.read_text(encoding="utf-8")
    assert "Consent confirmed" in html
    assert "Do not enter Aadhaar numbers" in html
    assert "no government, laboratory or company system is connected yet" in html
    assert "Only checked results are shown as verified" in html


def test_service_desk_javascript_has_all_expected_api_workflows():
    script = (ROOT / "app/static/js/service-desk.js").read_text(encoding="utf-8")
    for route in ("/api/service/summary", "/api/service/farmers", "/api/service/samples", "/results"):
        assert route in script
    assert "lab_verified" in script
    assert "window.print()" in script
    assert "new window.QRCode" in script
    assert "farmer-card-read" in script


def test_service_api_routes_cover_field_lab_and_farmer_workspaces():
    app_source = (ROOT / "app/app.py").read_text(encoding="utf-8")
    for route in (
        "/api/service/summary", "/api/service/farmers",
        "/api/service/farmers/<int:farmer_id>", "/api/service/samples",
        "/api/service/samples/<int:sample_id>/results",
        "/api/service/samples/<int:sample_id>/report",
    ):
        assert route in app_source
    assert "consent_recorded" in app_source
    assert "Only checked results are shown" not in app_source  # verification gate lives in the UI
    assert '"Verified" if verified else "Tested - pending verification"' in app_source


def test_saved_farm_outlook_uses_location_specific_regional_api():
    html = HTML.read_text(encoding="utf-8")
    script = (ROOT / "app/static/js/farm-outlook.js").read_text(encoding="utf-8")
    app_source = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert 'data-view-target="outlook"' in html
    assert '/api/virtual-farms/${encodeURIComponent(farmId)}/outlook' in script
    assert '@app.post("/api/virtual-farms/<int:farm_id>/outlook")' in app_source
    assert "regional.analyze_region(location)" in app_source
    assert "The separate Kolkata sensor model is not used to predict an Indian virtual farm" in html


def test_research_sensor_forecast_is_loaded_only_when_research_view_opens():
    script = (ROOT / "app/static/js/dashboard.js").read_text(encoding="utf-8")
    assert 'event.detail === "insights"' in script
    assert "if (user) initialiseResearchDashboard()" not in script


def test_demo_crop_statistics_are_explicitly_synthetic_and_have_trend_projection():
    regional = (ROOT / "app/services/regional.py").read_text(encoding="utf-8")
    data = (ROOT / "data/demo/DEMO_CROP_STATISTICS_SYNTHETIC.csv").read_text(encoding="utf-8")
    assert "SYNTHETIC PRESENTATION DATA" in regional
    assert "trend_projections" in regional
    assert "2024,Kharif,Soybean" in data
    assert '"data_type": "synthetic_demo"' in regional


def test_farm_outlook_automatically_uses_latest_saved_farm_and_refreshes_on_entry():
    script = (ROOT / "app/static/js/farm-outlook.js").read_text(encoding="utf-8")
    assert 'const selected = preferred || state.farms[0]' in script
    assert 'await generateOutlook()' in script
    assert 'if (event.detail === "outlook") loadFarms()' in script
    assert 'window.addEventListener("virtual-farm-saved"' in script
    assert 'state.loaded' not in script


def test_farm_outlook_explains_weather_and_regional_ml_predictions_separately():
    html = HTML.read_text(encoding="utf-8")
    script = (ROOT / "app/static/js/farm-outlook.js").read_text(encoding="utf-8")
    assert "This is the seven-day forecast for the saved farm coordinates" in html
    assert "root-zone prediction is not available right now" in script
    assert "Kolkata experimental sensor model" in script
    assert "District crop-history trends describe recorded area and production" in html


def test_location_and_farm_shortcuts_are_available_from_prediction_view():
    html = HTML.read_text(encoding="utf-8")
    outlook = html.split('id="outlook-view"', 1)[1].split('</section>', 1)[0]
    assert 'data-open-view="location"' in outlook
    assert 'data-open-view="farm"' in outlook
