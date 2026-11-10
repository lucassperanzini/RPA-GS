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
