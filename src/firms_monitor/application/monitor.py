"""Caso de uso principal: coletar, filtrar, classificar, registrar e alertar."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from firms_monitor.application.ports import AlertNotifier, HotspotProvider, OccurrenceRepository
from firms_monitor.domain.filters import HotspotFilter
from firms_monitor.domain.models import ClassifiedHotspot, RiskLevel
from firms_monitor.domain.risk import RiskClassifier

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    started_at: datetime
    finished_at: datetime
    fetched: int
    accepted: int
    new_occurrences: int
    alerts_sent: int
    by_level: dict[RiskLevel, int] = field(default_factory=dict)

    def summary(self) -> str:
        levels = ", ".join(f"{lvl.label}={qty}" for lvl, qty in sorted(self.by_level.items())) or "nenhum"
        duration = (self.finished_at - self.started_at).total_seconds()
        return (
            f"coletados={self.fetched} | ativos={self.accepted} | novos={self.new_occurrences} | "
            f"alertas={self.alerts_sent} | níveis[{levels}] | duração={duration:.1f}s"
        )


class FireMonitorService:
    """Orquestra o fluxo do robô. Depende apenas de abstrações (portas)."""

    def __init__(
        self,
        provider: HotspotProvider,
        hotspot_filter: HotspotFilter,
        classifier: RiskClassifier,
        repository: OccurrenceRepository,
        notifier: AlertNotifier,
        alert_min_level: RiskLevel = RiskLevel.CRITICO,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._provider = provider
        self._filter = hotspot_filter
        self._classifier = classifier
        self._repository = repository
        self._notifier = notifier
        self._alert_min_level = alert_min_level
        self._clock = clock

    def run(self) -> ExecutionReport:
        started_at = self._clock()
        logger.info("Iniciando ciclo de monitoramento.")

        hotspots = self._provider.fetch()
        active = [h for h in hotspots if self._filter.accepts(h)]
        logger.info("Focos coletados: %d | ativos após filtros: %d", len(hotspots), len(active))

        known_ids = self._repository.existing_ids()
        unique_new = {h.hotspot_id: h for h in active if h.hotspot_id not in known_ids}

        processed_at = self._clock()
        classified = [
            ClassifiedHotspot(hotspot=h, risk_level=self._classifier.classify(h), processed_at=processed_at)
            for h in unique_new.values()
        ]

        saved = self._repository.save_many(classified) if classified else 0

        alerts = [c for c in classified if c.risk_level >= self._alert_min_level]
        if alerts:
            self._notifier.notify(alerts)

        report = ExecutionReport(
            started_at=started_at,
            finished_at=self._clock(),
            fetched=len(hotspots),
            accepted=len(active),
            new_occurrences=saved,
            alerts_sent=len(alerts),
            by_level=dict(Counter(c.risk_level for c in classified)),
        )
        logger.info("Ciclo finalizado: %s", report.summary(), extra={"report": report})
        return report
