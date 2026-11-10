"""Composition root: único ponto que conhece as implementações concretas.

Para acoplar em outro projeto, use `build_fire_monitor(settings)` ou monte o
`FireMonitorService` manualmente injetando suas próprias implementações das portas.
"""

from __future__ import annotations

from firms_monitor.application.monitor import FireMonitorService
from firms_monitor.application.ports import AlertNotifier, OccurrenceRepository
from firms_monitor.config import ConfigurationError, Settings
from firms_monitor.domain.filters import CompositeFilter, ConfidenceFilter, MinFrpFilter
from firms_monitor.domain.risk import RiskClassifier
from firms_monitor.infrastructure.firms import (
    AreaQuery,
    CountryQuery,
    FirmsApiClient,
    FirmsCsvParser,
    FirmsHotspotProvider,
    FirmsQuery,
)
from firms_monitor.infrastructure.notification import LogAlertNotifier
from firms_monitor.infrastructure.persistence import CsvOccurrenceRepository


def build_query(settings: Settings) -> FirmsQuery:
    if settings.query_mode == "country":
        return CountryQuery(settings.source, settings.country_code, settings.day_range)
    if settings.query_mode == "area":
        if settings.bbox is None:
            raise ConfigurationError("FIRMS_QUERY_MODE=area exige FIRMS_BBOX=west,south,east,north")
        return AreaQuery(settings.source, *settings.bbox, day_range=settings.day_range)
    raise ConfigurationError(f"FIRMS_QUERY_MODE inválido: '{settings.query_mode}' (use 'country' ou 'area').")


def build_fire_monitor(
    settings: Settings,
    repository: OccurrenceRepository | None = None,
    notifier: AlertNotifier | None = None,
) -> FireMonitorService:
    client = FirmsApiClient(
        map_key=settings.map_key,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
    provider = FirmsHotspotProvider(client, FirmsCsvParser(), build_query(settings))
    hotspot_filter = CompositeFilter(
        [ConfidenceFilter(settings.min_numeric_confidence), MinFrpFilter(settings.min_frp)]
    )
    classifier = RiskClassifier.from_thresholds(
        settings.risk_medio_frp, settings.risk_alto_frp, settings.risk_critico_frp
    )
    return FireMonitorService(
        provider=provider,
        hotspot_filter=hotspot_filter,
        classifier=classifier,
        repository=repository or CsvOccurrenceRepository(settings.output_csv, settings.csv_delimiter),
        notifier=notifier or LogAlertNotifier(),
        alert_min_level=settings.alert_min_level,
    )
