import pytest

from firms_monitor.bootstrap import build_fire_monitor, build_query
from firms_monitor.config import ConfigurationError, Settings
from firms_monitor.domain import RiskLevel
from firms_monitor.infrastructure.firms import AreaQuery, CountryQuery


def test_settings_defaults():
    s = Settings.from_env({"FIRMS_MAP_KEY": "abc"})
    assert s.source == "VIIRS_NOAA20_NRT"
    assert s.country_code == "BRA"
    assert s.alert_min_level is RiskLevel.CRITICO
    assert isinstance(build_query(s), CountryQuery)
    assert build_fire_monitor(s) is not None


def test_settings_requires_map_key():
    with pytest.raises(ConfigurationError):
        Settings.from_env({})


def test_area_mode():
    s = Settings.from_env({"FIRMS_MAP_KEY": "abc", "FIRMS_QUERY_MODE": "area", "FIRMS_BBOX": "-74,-34,-34.7,5.3"})
    assert isinstance(build_query(s), AreaQuery)


def test_area_mode_without_bbox_fails():
    s = Settings.from_env({"FIRMS_MAP_KEY": "abc", "FIRMS_QUERY_MODE": "area"})
    with pytest.raises(ConfigurationError):
        build_query(s)
