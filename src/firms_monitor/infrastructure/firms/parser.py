"""Conversão do CSV da FIRMS (VIIRS ou MODIS) em entidades de domínio."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

from firms_monitor.domain.models import FireHotspot

logger = logging.getLogger(__name__)


class FirmsCsvParser:
    # VIIRS usa bright_ti4; MODIS usa brightness.
    _BRIGHTNESS_COLUMNS = ("bright_ti4", "brightness")

    def parse(self, csv_text: str, source: str) -> list[FireHotspot]:
        reader = csv.DictReader(io.StringIO(csv_text))
        hotspots: list[FireHotspot] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                hotspots.append(self._parse_row(row, source))
            except (KeyError, ValueError) as exc:
                logger.warning("Linha %d ignorada (dado inválido: %s): %s", line_number, exc, row)
        return hotspots

    def _parse_row(self, row: dict[str, str], source: str) -> FireHotspot:
        return FireHotspot(
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            acquired_at=self._parse_datetime(row["acq_date"], row["acq_time"]),
            satellite=row.get("satellite", "").strip(),
            instrument=row.get("instrument", "").strip(),
            confidence=str(row.get("confidence", "")).strip(),
            frp=float(row["frp"]),
            daynight=row.get("daynight", "").strip(),
            brightness=self._parse_brightness(row),
            source=source,
            country=(row.get("country_id") or "").strip() or None,
            scan=self._parse_optional_float(row.get("scan")),
            track=self._parse_optional_float(row.get("track")),
        )

    @staticmethod
    def _parse_datetime(acq_date: str, acq_time: str) -> datetime:
        # acq_time vem como HHMM, podendo perder zeros à esquerda (ex.: "312" -> 03:12).
        hhmm = acq_time.strip().zfill(4)
        return datetime.strptime(f"{acq_date.strip()} {hhmm}", "%Y-%m-%d %H%M").replace(tzinfo=timezone.utc)

    def _parse_brightness(self, row: dict[str, str]) -> float | None:
        for column in self._BRIGHTNESS_COLUMNS:
            value = row.get(column)
            if value not in (None, ""):
                return float(value)
        return None

    @staticmethod
    def _parse_optional_float(value: str | None) -> float | None:
        if value is None or not value.strip():
            return None
        return float(value)
