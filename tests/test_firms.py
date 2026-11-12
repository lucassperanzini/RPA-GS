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


def test_le_o_tamanho_do_pixel():
    focos = FirmsCsvParser().parse(VIIRS_CSV, "VIIRS_NOAA20_NRT")
    assert [(f.scan, f.track) for f in focos] == [(0.4, 0.37), (0.5, 0.4)]


def test_sem_as_colunas_fica_vazio():
    sem_colunas = (
        "latitude,longitude,bright_ti4,acq_date,acq_time,satellite,instrument,confidence,frp,daynight\n"
        "-9.1,-55.5,345.2,2026-11-10,312,N20,VIIRS,n,12.5,N\n"
    )
    foco = FirmsCsvParser().parse(sem_colunas, "VIIRS_NOAA20_NRT")[0]
    assert (foco.scan, foco.track) == (None, None)


def test_colunas_presentes_mas_vazias_ficam_none():
    vazias = VIIRS_CSV.replace(",0.4,0.37,", ",,,", 1)
    foco = FirmsCsvParser().parse(vazias, "VIIRS_NOAA20_NRT")[0]
    assert (foco.scan, foco.track) == (None, None)
    assert foco.frp == 12.5  # o resto da linha continua correto


def test_le_o_tamanho_do_pixel_no_modis():
    modis = (
        "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
        "-10.5,-52.1,320.4,1.2,1.1,2026-11-10,1340,Aqua,MODIS,78,6.1NRT,295.0,40.2,D\n"
    )
    foco = FirmsCsvParser().parse(modis, "MODIS_NRT")[0]
    assert (foco.scan, foco.track) == (1.2, 1.1)
    assert foco.brightness == 320.4


def test_scan_invalido_descarta_a_linha():
    invalido = VIIRS_CSV.replace(",0.4,0.37,", ",x,0.37,", 1)
    focos = FirmsCsvParser().parse(invalido, "VIIRS_NOAA20_NRT")
    assert len(focos) == 1  # só a 2ª linha válida sobra (a 1ª tem scan inválido, a 3ª latitude inválida)


def test_pixel_nao_altera_o_id_do_foco(make_hotspot):
    from dataclasses import replace

    foco = make_hotspot()
    assert replace(foco, scan=0.4, track=0.37).hotspot_id == foco.hotspot_id


def _client_returning(text: str, status_code: int = 200) -> FirmsApiClient:
    session = MagicMock()
    session.get.return_value.text = text
    session.get.return_value.status_code = status_code
    return FirmsApiClient("SECRET", session=session)


def test_client_reports_http_error_body_and_masks_key():
    with pytest.raises(FirmsApiError) as exc:
        _client_returning("Invalid API call.", status_code=400).fetch_csv(CountryQuery("VIIRS_NOAA20_NRT", "BRA"))
    assert "Invalid API call." in str(exc.value)
    assert "SECRET" not in str(exc.value)


def test_client_detects_error_message_in_200_response():
    with pytest.raises(FirmsApiError):
        _client_returning("Invalid MAP_KEY.").fetch_csv(CountryQuery("VIIRS_NOAA20_NRT", "BRA"))


def test_provider_end_to_end_with_fake_session():
    provider = FirmsHotspotProvider(
        _client_returning(VIIRS_CSV), FirmsCsvParser(), CountryQuery("VIIRS_NOAA20_NRT", "BRA")
    )
    assert len(provider.fetch()) == 2
