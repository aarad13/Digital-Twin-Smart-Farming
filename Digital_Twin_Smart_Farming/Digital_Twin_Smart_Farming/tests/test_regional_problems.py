import unittest
from app.services.regional_problems import build_regional_problem_report


class RegionalProblemReportTests(unittest.TestCase):
    def test_maharashtra_state_profile(self):
        report = build_regional_problem_report(
            {"admin1": "Maharashtra", "admin2": "Pune"},
            {"agro_climatic_zone_candidates": [{"id": "IX", "name": "Western Plateau"}],
             "zone_classification_note": "State spans several zones."},
            {}, {"daily": []}, {"status": "unavailable"}, {"available": False}
        )
        self.assertEqual(report["profile_level"], "State-level ICAR profile")
        self.assertGreaterEqual(len(report["documented_challenges"]), 3)
        self.assertIn("ICAR", report["profile_source_name"])

    def test_forecast_and_soil_signals(self):
        report = build_regional_problem_report(
            {"admin1": "Madhya Pradesh", "landform": "Plain"},
            {"agro_climatic_zone_candidates": [{"id": "VIII"}], "zone_classification_note": "candidate"},
            {},
            {"daily": [{"date": "2026-11-18", "precipitation_mm": 0.0, "max_temp_c": 36.0}]},
            {"status": "available", "depth": "0-5 cm", "properties": {
                "ph": {"value": 8.7}, "sand_pct": {"value": 75}, "clay_pct": {"value": 10}
            }},
            {"available": False},
        )
        titles = [x["title"] for x in report["current_signals"]]
        self.assertTrue(any("dry and hot" in x for x in titles))
        self.assertTrue(any("pH screening" in x for x in titles))
        self.assertTrue(any("sand-dominant" in x for x in titles))

    def test_unknown_state_uses_zone_fallback(self):
        report = build_regional_problem_report(
            {"admin1": "Odisha"},
            {"agro_climatic_zone_candidates": [
                {"id": "VII", "typical_systems": ["Rainfed rice"]},
                {"id": "XI", "typical_systems": ["Rice-based"]},
            ], "zone_classification_note": "State maps across candidate zones."},
            {}, {"daily": []}, {"status": "unavailable"}, {"available": False}
        )
        self.assertEqual(report["profile_level"], "Agro-climatic-zone context")
        self.assertGreaterEqual(len(report["documented_challenges"]), 2)
        self.assertIn("district", report["district_plan_note"].lower())


if __name__ == "__main__":
    unittest.main()
