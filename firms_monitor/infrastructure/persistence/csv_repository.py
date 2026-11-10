"""Registro das ocorrências processadas em arquivo CSV."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Sequence

from firms_monitor.domain.models import ClassifiedHotspot

logger = logging.getLogger(__name__)


class CsvOccurrenceRepository:
    FIELDNAMES = (
        "id",
        "processado_em_utc",
        "detectado_em_utc",
        "latitude",
        "longitude",
        "frp_mw",
        "nivel_risco",
        "confianca",
        "satelite",
        "instrumento",
        "dia_noite",
        "brilho_k",
        "pais",
        "fonte",
        "mapa",
    )

    def __init__(self, file_path: str | Path, delimiter: str = ",", encoding: str = "utf-8-sig") -> None:
        self._path = Path(file_path)
        self._delimiter = delimiter
        self._encoding = encoding  # utf-8-sig: acentos abrem corretamente no Excel

    def existing_ids(self) -> set[str]:
        if not self._path.exists():
            return set()
        with self._path.open("r", newline="", encoding=self._encoding) as file:
            reader = csv.DictReader(file, delimiter=self._delimiter)
            return {row["id"] for row in reader if row.get("id")}

    def save_many(self, occurrences: Sequence[ClassifiedHotspot]) -> int:
        if not occurrences:
            return 0
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self._path.exists() or self._path.stat().st_size == 0
        with self._path.open("a", newline="", encoding=self._encoding) as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES, delimiter=self._delimiter)
            if write_header:
                writer.writeheader()
            writer.writerows(self._to_row(o) for o in occurrences)
        logger.info("%d ocorrências registradas em %s", len(occurrences), self._path)
        return len(occurrences)

    @staticmethod
    def _to_row(occurrence: ClassifiedHotspot) -> dict[str, object]:
        h = occurrence.hotspot
        return {
            "id": h.hotspot_id,
            "processado_em_utc": occurrence.processed_at.isoformat(timespec="seconds"),
            "detectado_em_utc": h.acquired_at.isoformat(timespec="minutes"),
            "latitude": h.latitude,
            "longitude": h.longitude,
            "frp_mw": h.frp,
            "nivel_risco": occurrence.risk_level.label,
            "confianca": h.confidence,
            "satelite": h.satellite,
            "instrumento": h.instrument,
            "dia_noite": h.daynight,
            "brilho_k": "" if h.brightness is None else h.brightness,
            "pais": h.country or "",
            "fonte": h.source,
            "mapa": h.maps_url,
        }
