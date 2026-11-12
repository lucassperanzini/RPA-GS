"""Registro das ocorrências processadas em arquivo CSV."""

from __future__ import annotations

import csv
import logging
import os
import tempfile
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
        # Colunas novas entram sempre no FINAL: arquivos antigos são migrados automaticamente.
        "scan_km",
        "track_km",
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
        if mode == "a":
            self._ensure_current_header()
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

    def _read_header(self) -> list[str]:
        with self._path.open("r", newline="", encoding=self._encoding) as file:
            return next(csv.reader(file, delimiter=self._delimiter), [])

    def _ensure_current_header(self) -> None:
        """Garante que o arquivo existente tem o cabeçalho atual, migrando versões antigas."""
        header = self._read_header()
        if header == list(self.FIELDNAMES):
            return
        self._validate_header(header)
        unknown = [col for col in header if col not in self.FIELDNAMES]
        if unknown:
            raise OccurrenceRepositoryError(
                f"O arquivo {self._path} tem colunas desconhecidas {unknown}. "
                "Remova-as ou aponte OUTPUT_CSV para outro arquivo."
            )
        self._migrate([col for col in self.FIELDNAMES if col not in header])

    def _migrate(self, added_columns: list[str]) -> None:
        """Reescreve o arquivo no formato atual. Linhas antigas recebem as colunas novas vazias.

        Escreve num arquivo temporário e só então substitui o original, para não corromper o
        registro caso a migração seja interrompida.
        """
        with self._path.open("r", newline="", encoding=self._encoding) as source:
            rows = list(csv.DictReader(source, delimiter=self._delimiter))

        fd, temp_name = tempfile.mkstemp(dir=self._path.parent, prefix=f".{self._path.stem}-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", newline="", encoding=self._encoding) as target:
                writer = csv.DictWriter(target, fieldnames=self.FIELDNAMES, delimiter=self._delimiter, restval="")
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temp_name, self._path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise
        logger.info(
            "Arquivo %s atualizado para o novo formato (%d linhas; colunas adicionadas: %s).",
            self._path,
            len(rows),
            ", ".join(added_columns),
        )

    @staticmethod
    def _optional(value: float | None) -> object:
        return "" if value is None else value

    @classmethod
    def _to_row(cls, occurrence: ClassifiedHotspot) -> dict[str, object]:
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
            "brilho_k": cls._optional(h.brightness),
            "pais": h.country or "",
            "fonte": h.source,
            "mapa": h.maps_url,
            "scan_km": cls._optional(h.scan),
            "track_km": cls._optional(h.track),
        }
