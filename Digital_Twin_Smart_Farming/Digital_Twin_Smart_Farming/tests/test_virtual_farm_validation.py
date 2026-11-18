import pytest
from app.services.virtual_farm import _safe_india_point, _validate_polygon_feature, _nullable_float, _ensure_inside_farm


def feature(coords):
    return {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [coords]}}


def test_indian_coordinates_are_accepted():
    assert _safe_india_point(18.5204, 73.8567) == (18.5204, 73.8567)


def test_coordinates_outside_india_are_rejected():
    with pytest.raises(ValueError):
        _safe_india_point(51.5, -0.12)


def test_closed_polygon_near_farm_is_accepted():
    polygon = feature([[73.8560,18.5200],[73.8570,18.5200],[73.8570,18.5210],[73.8560,18.5210],[73.8560,18.5200]])
    saved = _validate_polygon_feature(polygon, 18.5205, 73.8565)
    assert '"Polygon"' in saved


def test_unclosed_polygon_is_rejected():
    polygon = feature([[73.8560,18.5200],[73.8570,18.5200],[73.8570,18.5210],[73.8560,18.5210]])
    with pytest.raises(ValueError, match="closed"):
        _validate_polygon_feature(polygon, 18.5205, 73.8565)


def test_invalid_soil_ph_is_rejected():
    with pytest.raises(ValueError):
        _nullable_float(15, "Soil pH", 0, 14)


def test_plot_polygon_must_be_inside_outer_farm_boundary():
    outer = feature([[73.8550,18.5190],[73.8580,18.5190],[73.8580,18.5220],[73.8550,18.5220],[73.8550,18.5190]])
    inner = feature([[73.8560,18.5200],[73.8570,18.5200],[73.8570,18.5210],[73.8560,18.5210],[73.8560,18.5200]])
    _ensure_inside_farm(inner, outer, "plot boundary")
    outside = feature([[73.8590,18.5200],[73.8600,18.5200],[73.8600,18.5210],[73.8590,18.5210],[73.8590,18.5200]])
    with pytest.raises(ValueError, match="inside the saved outer farm boundary"):
        _ensure_inside_farm(outside, outer, "plot boundary")


def test_infrastructure_point_must_be_inside_outer_farm_boundary():
    outer = feature([[73.8550,18.5190],[73.8580,18.5190],[73.8580,18.5220],[73.8550,18.5220],[73.8550,18.5190]])
    _ensure_inside_farm({"type": "Point", "coordinates": [73.8565,18.5205]}, outer, "infrastructure asset")
    with pytest.raises(ValueError, match="inside the saved outer farm boundary"):
        _ensure_inside_farm({"type": "Point", "coordinates": [73.8595,18.5205]}, outer, "infrastructure asset")
