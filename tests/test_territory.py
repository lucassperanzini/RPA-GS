import json

import pytest

from firms_monitor.bootstrap import build_filter
from firms_monitor.config import ConfigurationError, Settings
from firms_monitor.domain import Polygon, Territory, TerritoryFilter
from firms_monitor.infrastructure.geo import GeoJsonTerritoryLoader

SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0))
HOLE = ((4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0), (4.0, 4.0))


def test_polygon_contains_respects_holes_and_bbox():
    poly = Polygon(SQUARE, holes=(HOLE,))
    assert poly.contains(1, 1)
    assert not poly.contains(5, 5)  # dentro do buraco
    assert not poly.contains(11, 5)  # fora do retângulo envolvente


@pytest.mark.parametrize(
    ("lat", "lon", "inside"),
    [
        (-15.79, -47.88, True),  # Brasília
        (-2.91594, -40.42311, True),  # Ceará
        (-3.10, -60.02, True),  # Manaus
        (-30.03, -51.23, True),  # Porto Alegre
        (-23.15, -44.25, True),  # Ilha Grande (RJ)
        (-26.11077, -60.83205, False),  # Chaco argentino
        (-17.36497, -60.34701, False),  # Bolívia
        (-25.30, -57.63, False),  # Assunção (Paraguai)
        (-12.05, -77.04, False),  # Lima (Peru)
        (-20.0, -30.0, False),  # Oceano Atlântico
    ],
)
def test_builtin_brazil_boundary(make_hotspot, lat, lon, inside):
    territory_filter = TerritoryFilter(GeoJsonTerritoryLoader().load("br"))
    assert territory_filter.accepts(make_hotspot(lat=lat, lon=lon)) is inside


def test_loader_reads_custom_geojson_file(tmp_path, make_hotspot):
    path = tmp_path / "area.geojson"
    path.write_text(json.dumps({"type": "Polygon", "coordinates": [[list(p) for p in SQUARE]]}), encoding="utf-8")
    territory = GeoJsonTerritoryLoader().load(str(path))
    assert isinstance(territory, Territory)
    assert TerritoryFilter(territory).accepts(make_hotspot(lat=5, lon=5))


def test_territory_filter_can_be_disabled_and_validates_config(make_hotspot):
    off = build_filter(Settings.from_env({"FIRMS_MAP_KEY": "k", "TERRITORY_FILTER": ""}))
    assert off.accepts(make_hotspot(lat=-12.05, lon=-77.04))  # Lima aceita quando desligado
    on = build_filter(Settings.from_env({"FIRMS_MAP_KEY": "k"}))  # padrão = BR
    assert not on.accepts(make_hotspot(lat=-12.05, lon=-77.04))
    with pytest.raises(ConfigurationError):
        build_filter(Settings.from_env({"FIRMS_MAP_KEY": "k", "TERRITORY_FILTER": "XX"}))
