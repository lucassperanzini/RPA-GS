"""Geometria de território: decide se uma coordenada está dentro de uma área (ex.: Brasil).

Implementação pura (sem bibliotecas externas) usando o algoritmo ray casting,
com pré-filtro por retângulo envolvente para manter a verificação rápida.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

Point = tuple[float, float]  # (longitude, latitude)
Ring = Sequence[Point]


def _point_in_ring(lon: float, lat: float, ring: Ring) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


@dataclass(frozen=True, slots=True)
class Polygon:
    """Polígono com contorno externo e buracos opcionais (padrão GeoJSON)."""

    exterior: tuple[Point, ...]
    holes: tuple[tuple[Point, ...], ...] = ()
    bbox: tuple[float, float, float, float] = field(init=False)  # min_lon, min_lat, max_lon, max_lat

    def __post_init__(self) -> None:
        if len(self.exterior) < 4:
            raise ValueError("Um polígono precisa de ao menos 4 pontos (contorno fechado).")
        lons = [p[0] for p in self.exterior]
        lats = [p[1] for p in self.exterior]
        object.__setattr__(self, "bbox", (min(lons), min(lats), max(lons), max(lats)))

    def contains(self, lon: float, lat: float) -> bool:
        min_lon, min_lat, max_lon, max_lat = self.bbox
        if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
            return False
        if not _point_in_ring(lon, lat, self.exterior):
            return False
        return not any(_point_in_ring(lon, lat, hole) for hole in self.holes)


class Territory:
    """Área composta por um ou mais polígonos (ex.: continente + ilhas)."""

    def __init__(self, name: str, polygons: Iterable[Polygon]) -> None:
        self.name = name
        self._polygons = tuple(polygons)
        if not self._polygons:
            raise ValueError(f"Território '{name}' sem polígonos.")

    @property
    def polygons(self) -> tuple[Polygon, ...]:
        return self._polygons

    def contains(self, lon: float, lat: float) -> bool:
        return any(polygon.contains(lon, lat) for polygon in self._polygons)
