"""Notificadores de alerta. Novos canais (e-mail, Telegram...) basta implementar `notify`."""

from __future__ import annotations

import logging
from typing import Sequence

from firms_monitor.application.ports import AlertNotifier
from firms_monitor.domain.models import ClassifiedHotspot


class LogAlertNotifier:
    """Emite os alertas no log (console e/ou arquivo, conforme configuração de logging)."""

    def __init__(self, logger: logging.Logger | None = None, level: int = logging.WARNING) -> None:
        self._logger = logger or logging.getLogger("firms_monitor.alerts")
        self._level = level

    def notify(self, occurrences: Sequence[ClassifiedHotspot]) -> None:
        self._logger.log(self._level, "ALERTA: %d foco(s) de incêndio com risco elevado detectado(s).", len(occurrences))
        for occurrence in sorted(occurrences, key=lambda o: o.hotspot.frp, reverse=True):
            h = occurrence.hotspot
            self._logger.log(
                self._level,
                "[%s] FRP=%.1f MW | %s UTC | lat=%.5f lon=%.5f | conf=%s | sat=%s | %s",
                occurrence.risk_level.label.upper(),
                h.frp,
                h.acquired_at.strftime("%d/%m/%Y %H:%M"),
                h.latitude,
                h.longitude,
                h.confidence,
                h.satellite,
                h.maps_url,
            )


class CompositeNotifier:
    """Envia o mesmo alerta para vários canais; falha em um canal não impede os demais."""

    def __init__(self, notifiers: Sequence[AlertNotifier]) -> None:
        self._notifiers = tuple(notifiers)
        self._logger = logging.getLogger(__name__)

    def notify(self, occurrences: Sequence[ClassifiedHotspot]) -> None:
        for notifier in self._notifiers:
            try:
                notifier.notify(occurrences)
            except Exception:
                self._logger.exception("Falha no notificador %s", type(notifier).__name__)
