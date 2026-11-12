from firms_monitor.application import FireMonitorService, PeriodicRunner
from firms_monitor.domain import ConfidenceFilter, RiskClassifier, RiskLevel
from firms_monitor.infrastructure.persistence import CsvOccurrenceRepository


class FakeProvider:
    def __init__(self, hotspots):
        self.hotspots = hotspots

    def fetch(self):
        return list(self.hotspots)


class SpyNotifier:
    def __init__(self):
        self.calls = []

    def notify(self, occurrences):
        self.calls.append(list(occurrences))


def _service(provider, repository, notifier, alert_min=RiskLevel.CRITICO):
    return FireMonitorService(
        provider=provider,
        hotspot_filter=ConfidenceFilter(),
        classifier=RiskClassifier.from_thresholds(10, 50, 100),
        repository=repository,
        notifier=notifier,
        alert_min_level=alert_min,
    )


def test_full_cycle_registers_classifies_alerts_and_deduplicates(tmp_path, make_hotspot):
    hotspots = [
        make_hotspot(frp=5, lat=-1),
        make_hotspot(frp=60, lat=-2),
        make_hotspot(frp=250, lat=-3),
        make_hotspot(frp=500, lat=-4, confidence="l"),  # descartado pelo filtro
        make_hotspot(frp=250, lat=-3),  # duplicado na mesma resposta
    ]
    repository = CsvOccurrenceRepository(tmp_path / "out" / "ocorrencias.csv")
    notifier = SpyNotifier()
    service = _service(FakeProvider(hotspots), repository, notifier)

    report = service.run()

    assert report.fetched == 5
    assert report.accepted == 4
    assert report.new_occurrences == 3
    assert report.alerts_sent == 1
    assert report.by_level == {RiskLevel.BAIXO: 1, RiskLevel.ALTO: 1, RiskLevel.CRITICO: 1}
    assert notifier.calls[0][0].hotspot.frp == 250
    assert len(repository.existing_ids()) == 3

    second = service.run()  # mesma resposta da API -> nada novo
    assert second.new_occurrences == 0
    assert second.alerts_sent == 0
    assert len(notifier.calls) == 1

    lines = (tmp_path / "out" / "ocorrencias.csv").read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].startswith("id,")
    assert len(lines) == 4


def test_alert_min_level_is_configurable(tmp_path, make_hotspot):
    notifier = SpyNotifier()
    service = _service(
        FakeProvider([make_hotspot(frp=60)]),
        CsvOccurrenceRepository(tmp_path / "o.csv"),
        notifier,
        alert_min=RiskLevel.ALTO,
    )
    assert service.run().alerts_sent == 1


def test_periodic_runner_survives_failures():
    class Boom:
        calls = 0

        def run(self):
            Boom.calls += 1
            raise RuntimeError("falha")

    sleeps = []
    PeriodicRunner(Boom(), 1, sleep=sleeps.append).run_forever(max_cycles=3)
    assert Boom.calls == 3
    assert sleeps == [1, 1]


def test_blank_file_with_bom_gets_header(tmp_path, make_hotspot):
    from datetime import datetime, timezone
    from firms_monitor.domain import ClassifiedHotspot

    path = tmp_path / "o.csv"
    path.write_bytes(b"\xef\xbb\xbf")  # arquivo "esvaziado" no editor
    repo = CsvOccurrenceRepository(path)
    assert repo.existing_ids() == set()
    repo.save_many([ClassifiedHotspot(make_hotspot(), RiskLevel.BAIXO, datetime.now(timezone.utc))])
    assert path.read_text(encoding="utf-8-sig").startswith("id,")
    assert len(repo.existing_ids()) == 1


def test_file_without_header_fails_instead_of_realerting(tmp_path):
    import pytest
    from firms_monitor.infrastructure.persistence import OccurrenceRepositoryError

    path = tmp_path / "o.csv"
    path.write_text("VIIRS|N20|1.0|2.0|202611080418,2026-11-10,...\n", encoding="utf-8-sig")
    with pytest.raises(OccurrenceRepositoryError):
        CsvOccurrenceRepository(path).existing_ids()


# ---------------------------------------------------------------- scan/track no CSV
def _classified(make_hotspot, **kwargs):
    from dataclasses import replace
    from datetime import datetime, timezone
    from firms_monitor.domain import ClassifiedHotspot

    return ClassifiedHotspot(replace(make_hotspot(), **kwargs), RiskLevel.ALTO, datetime.now(timezone.utc))


def _read_rows(path):
    import csv

    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_csv_grava_scan_e_track(tmp_path, make_hotspot):
    path = tmp_path / "o.csv"
    CsvOccurrenceRepository(path).save_many([_classified(make_hotspot, scan=0.4, track=0.37)])
    row = _read_rows(path)[0]
    assert (row["scan_km"], row["track_km"]) == ("0.4", "0.37")


def test_csv_grava_vazio_quando_nao_ha_pixel(tmp_path, make_hotspot):
    path = tmp_path / "o.csv"
    CsvOccurrenceRepository(path).save_many([_classified(make_hotspot, scan=None, track=None)])
    row = _read_rows(path)[0]
    assert (row["scan_km"], row["track_km"]) == ("", "")


def test_csv_antigo_e_migrado_sem_perder_dados(tmp_path, make_hotspot):
    old_fields = [f for f in CsvOccurrenceRepository.FIELDNAMES if f not in ("scan_km", "track_km")]
    path = tmp_path / "o.csv"
    path.write_text(
        ",".join(old_fields) + "\r\n" + ",".join(["ID-ANTIGO"] + ["x"] * (len(old_fields) - 1)) + "\r\n",
        encoding="utf-8-sig",
    )
    repo = CsvOccurrenceRepository(path)
    assert repo.existing_ids() == {"ID-ANTIGO"}  # leitura funciona antes da migração

    repo.save_many([_classified(make_hotspot, latitude=-1.0, scan=0.5, track=0.4)])

    rows = _read_rows(path)
    assert list(rows[0].keys()) == list(CsvOccurrenceRepository.FIELDNAMES)
    assert rows[0]["id"] == "ID-ANTIGO" and rows[0]["scan_km"] == ""  # antigo preservado, coluna nova vazia
    assert rows[1]["scan_km"] == "0.5"  # novo com o valor
    assert len(repo.existing_ids()) == 2
    assert not list(tmp_path.glob("*.tmp"))  # nenhum temporário esquecido


def test_csv_com_coluna_desconhecida_nao_e_alterado(tmp_path, make_hotspot):
    import pytest
    from firms_monitor.infrastructure.persistence import OccurrenceRepositoryError

    path = tmp_path / "o.csv"
    path.write_bytes("id,coluna_minha\r\nA,1\r\n".encode("utf-8-sig"))
    original = path.read_bytes()
    with pytest.raises(OccurrenceRepositoryError):
        CsvOccurrenceRepository(path).save_many([_classified(make_hotspot)])
    assert path.read_bytes() == original  # arquivo intacto
