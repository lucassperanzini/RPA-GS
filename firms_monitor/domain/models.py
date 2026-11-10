"""Entidades de domínio: não dependem de nenhuma biblioteca externa nem de I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum


class RiskLevel(IntEnum):
    """Níveis de risco ordenáveis (permite comparações como `level >= RiskLevel.ALTO`)."""

    BAIXO = 1
    MEDIO = 2
    ALTO = 3
    CRITICO = 4

    @property
    def label(self) -> str:
        return _RISK_LABELS[self]

    @classmethod
    def from_name(cls, name: str) -> "RiskLevel":
        normalized = name.strip().upper().replace("É", "E").replace("Í", "I")
        try:
            return cls[normalized]
        except KeyError as exc:
            valid = ", ".join(level.name for level in cls)
            raise ValueError(f"Nível de risco inválido: '{name}'. Use um de: {valid}") from exc


_RISK_LABELS = {
    RiskLevel.BAIXO: "Baixo",
    RiskLevel.MEDIO: "Médio",
    RiskLevel.ALTO: "Alto",
    RiskLevel.CRITICO: "Crítico",
}


@dataclass(frozen=True, slots=True)
class FireHotspot:
    """Foco de incêndio detectado por satélite."""

    latitude: float
    longitude: float
    acquired_at: datetime  # sempre em UTC
    satellite: str
    instrument: str
    confidence: str
    frp: float  # Fire Radiative Power, em MW
    daynight: str
    brightness: float | None
    source: str
    country: str | None = None

    @property
    def hotspot_id(self) -> str:
        """Identificador determinístico, usado para evitar registros duplicados."""
        return (
            f"{self.source}|{self.satellite}|{self.latitude:.5f}|"
            f"{self.longitude:.5f}|{self.acquired_at:%Y%m%d%H%M}"
        )

    @property
    def maps_url(self) -> str:
        return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"


@dataclass(frozen=True, slots=True)
class ClassifiedHotspot:
    """Foco de incêndio já avaliado pelas regras de negócio."""

    hotspot: FireHotspot
    risk_level: RiskLevel
    processed_at: datetime
