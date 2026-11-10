"""Registro das ocorrências processadas em arquivo CSV."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Sequence

from firms_monitor.domain.models import ClassifiedHotspot

logger = logging.getLogger(__name__)


class OccurrenceRepositoryError(RuntimeError):
    """Arquivo de registro em estado inconsistente (ex.: sem cabeçalho)."""


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
        if self._is_blank():
            return set()
        with self._path.open("r", newline="", encoding=self._encoding) as file:
            reader = csv.DictReader(file, delimiter=self._delimiter)
            self._validate_header(reader.fieldnames)
            return {row["id"] for row in reader if row.get("id")}

    def save_many(self, occurrences: Sequence[ClassifiedHotspot]) -> int:
        if not occurrences:
            return 0
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Arquivo inexistente ou "vazio" (só BOM/espaços, ex.: esvaziado no editor) é recriado com cabeçalho.
        mode = "w" if self._is_blank() else "a"
        with self._path.open(mode, newline="", encoding=self._encoding) as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES, delimiter=self._delimiter)
            if mode == "w":
                writer.writeheader()
            writer.writerows(self._to_row(o) for o in occurrences)
        logger.info("%d ocorrências registradas em %s", len(occurrences), self._path)
        return len(occurrences)

    def _is_blank(self) -> bool:
        if not self._path.exists():
            return True
        with self._path.open("r", encoding=self._encoding) as file:
            return not file.read(4096).strip()

    def _validate_header(self, fieldnames: Sequence[str] | None) -> None:
        # Sem cabeçalho válido não há como deduplicar: falhar é melhor que re-alertar tudo em silêncio.
        if not fieldnames or "id" not in fieldnames:
            raise OccurrenceRepositoryError(
                f"O arquivo {self._path} não possui o cabeçalho esperado (coluna 'id'). "
                "Corrija o cabeçalho ou apague o arquivo para recriá-lo."
            )

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
