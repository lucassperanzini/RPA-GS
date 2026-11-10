from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from firms_monitor.infrastructure.firms import (
    AreaQuery,
    CountryQuery,
    FirmsApiClient,
    FirmsApiError,
    FirmsCsvParser,
    FirmsHotspotProvider,
)

VIIRS_CSV = """country_id,latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
BRA,-9.12345,-55.54321,345.2,0.4,0.37,2026-11-10,312,N20,VIIRS,n,2.0NRT,290.1,12.5,N
BRA,-10.0,-56.0,367.0,0.5,0.4,2026-11-10,1545,N20,VIIRS,h,2.0NRT,300.0,150.3,D
BRA,abc,-56.0,367.0,0.5,0.4,2026-11-10,1545,N20,VIIRS,h,2.0NRT,300.0,150.3,D
"""


def test_country_query_path():
    assert CountryQuery("VIIRS_NOAA20_NRT", "BRA", 2).build_path("KEY") == "api/country/csv/KEY/VIIRS_NOAA20_NRT/BRA/2"


def test_area_query_path_and_validation():
    q = AreaQuery("MODIS_NRT", -74.0, -34.0, -34.7, 5.3, day_range=1, date="2026-11-01")
    assert q.build_path("K") == "api/area/csv/K/MODIS_NRT/-74.0,-34.0,-34.7,5.3/1/2026-11-01"
    with pytest.raises(ValueError):
        AreaQuery("MODIS_NRT", 10, 0, 5, 1)
    with pytest.raises(ValueError):
        CountryQuery("MODIS_NRT", "BRA", day_range=11)


def test_parser_reads_viirs_and_skips_invalid_rows():
    hotspots = FirmsCsvParser().parse(VIIRS_CSV, source="VIIRS_NOAA20_NRT")
    assert len(hotspots) == 2
    first = hotspots[0]
    assert first.acquired_at == datetime(2026, 11, 10, 3, 12, tzinfo=timezone.utc)
    assert first.frp == 12.5
    assert first.brightness == 345.2
    assert first.country == "BRA"


def _client_returning(text: str) -> FirmsApiClient:
    session = MagicMock()
    session.get.return_value.text = text
    session.get.return_value.raise_for_status.return_value = None
    return FirmsApiClient("SECRET", session=session)


def test_client_detects_error_message_in_200_response():
    with pytest.raises(FirmsApiError):
        _client_returning("Invalid MAP_KEY.").fetch_csv(CountryQuery("VIIRS_NOAA20_NRT", "BRA"))


def test_provider_end_to_end_with_fake_session():
    provider = FirmsHotspotProvider(
        _client_returning(VIIRS_CSV), FirmsCsvParser(), CountryQuery("VIIRS_NOAA20_NRT", "BRA")
    )
    assert len(provider.fetch()) == 2
