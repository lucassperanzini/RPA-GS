"""Execução periódica do robô (útil quando não há agendador externo como Task Scheduler/cron)."""

from __future__ import annotations

import logging
import time
from typing import Callable

from firms_monitor.application.monitor import FireMonitorService

logger = logging.getLogger(__name__)


class PeriodicRunner:
    def __init__(
        self,
        service: FireMonitorService,
        interval_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("O intervalo deve ser maior que zero.")
        self._service = service
        self._interval = interval_seconds
        self._sleep = sleep

    def run_forever(self, max_cycles: int | None = None) -> None:
        cycle = 0
        while max_cycles is None or cycle < max_cycles:
            cycle += 1
            try:
                self._service.run()
            except Exception:  # o robô não deve morrer por uma falha pontual
                logger.exception("Falha no ciclo %d. Nova tentativa no próximo intervalo.", cycle)
            if max_cycles is None or cycle < max_cycles:
                logger.info("Aguardando %.0f segundos até o próximo ciclo.", self._interval)
                self._sleep(self._interval)
