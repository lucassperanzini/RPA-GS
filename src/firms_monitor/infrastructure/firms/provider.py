"""Adaptador que implementa a porta HotspotProvider usando a API FIRMS."""

from __future__ import annotations

import logging

from firms_monitor.domain.models import FireHotspot
from firms_monitor.infrastructure.firms.client import FirmsApiClient
from firms_monitor.infrastructure.firms.parser import FirmsCsvParser
from firms_monitor.infrastructure.firms.queries import FirmsQuery

logger = logging.getLogger(__name__)


class FirmsHotspotProvider:
    def __init__(self, client: FirmsApiClient, parser: FirmsCsvParser, query: FirmsQuery) -> None:
        self._client = client
        self._parser = parser
        self._query = query

    def fetch(self) -> list[FireHotspot]:
        csv_text = self._client.fetch_csv(self._query)
        hotspots = self._parser.parse(csv_text, source=self._query.source)
        logger.info("FIRMS retornou %d focos (fonte %s).", len(hotspots), self._query.source)
        return hotspots
