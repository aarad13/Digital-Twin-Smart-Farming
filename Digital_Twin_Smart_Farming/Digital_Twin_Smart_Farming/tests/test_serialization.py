from datetime import date, datetime
from decimal import Decimal
import numpy as np
from app.serialization import json_safe


def test_nested_mysql_and_numpy_values_are_json_safe():
    source = {
        "area": Decimal("1.250"),
        "created": datetime(2026, 11, 18, 10, 30),
        "date": date(2026, 11, 18),
        "nested": [{"value": np.float64(2.5), "missing": np.float64(float("nan"))}],
    }
    result = json_safe(source)
    assert result["area"] == 1.25
    assert result["created"] == "2026-11-18 10:30:00"
    assert result["date"] == "2026-11-18"
    assert result["nested"][0]["value"] == 2.5
    assert result["nested"][0]["missing"] is None
