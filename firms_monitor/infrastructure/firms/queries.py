"""Montagem dos caminhos da API FIRMS (Strategy: cada tipo de consulta sabe montar sua rota)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

MAX_DAY_RANGE = 5  # limite documentado pela API FIRMS


class FirmsQuery(Protocol):
    source: str

    def build_path(self, map_key: str) -> str: ...


def _validate_day_range(day_range: int) -> None:
    if not 1 <= day_range <= MAX_DAY_RANGE:
        raise ValueError(f"day_range deve estar entre 1 e {MAX_DAY_RANGE}.")


@dataclass(frozen=True, slots=True)
class CountryQuery:
    """GET /api/country/csv/{MAP_KEY}/{SOURCE}/{COUNTRY}/{DAY_RANGE}[/{DATE}]"""

    source: str
    country_code: str
    day_range: int = 1
    date: str | None = None  # YYYY-MM-DD; None = mais recente

    def __post_init__(self) -> None:
        _validate_day_range(self.day_range)

    def build_path(self, map_key: str) -> str:
        path = f"api/country/csv/{map_key}/{self.source}/{self.country_code}/{self.day_range}"
        return f"{path}/{self.date}" if self.date else path


@dataclass(frozen=True, slots=True)
class AreaQuery:
    """GET /api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}[/{DATE}]"""

    source: str
    west: float
    south: float
    east: float
    north: float
    day_range: int = 1
    date: str | None = None

    def __post_init__(self) -> None:
        _validate_day_range(self.day_range)
        if not (self.west < self.east and self.south < self.north):
            raise ValueError("Bounding box inválida: esperado west < east e south < north.")

    def build_path(self, map_key: str) -> str:
        bbox = f"{self.west},{self.south},{self.east},{self.north}"
        path = f"api/area/csv/{map_key}/{self.source}/{bbox}/{self.day_range}"
        return f"{path}/{self.date}" if self.date else path
