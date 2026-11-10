"""Filtros que decidem se um foco deve ser considerado ativo/válido para processamento."""

from __future__ import annotations

from typing import Iterable, Protocol

from firms_monitor.domain.models import FireHotspot
from firms_monitor.domain.territory import Territory


class HotspotFilter(Protocol):
    def accepts(self, hotspot: FireHotspot) -> bool: ...


class ConfidenceFilter:
    """Descarta detecções de baixa confiança.

    - VIIRS informa confiança categórica: l (low), n (nominal), h (high).
    - MODIS informa confiança numérica: 0 a 100.
    """

    _LOW_CATEGORICAL = frozenset({"l", "low"})

    def __init__(self, min_numeric_confidence: int = 30) -> None:
        self._min_numeric = min_numeric_confidence

    def accepts(self, hotspot: FireHotspot) -> bool:
        value = hotspot.confidence.strip().lower()
        if value.isdigit():
            return int(value) >= self._min_numeric
        return value not in self._LOW_CATEGORICAL


class MinFrpFilter:
    """Descarta focos com FRP abaixo de um valor mínimo (ruído)."""

    def __init__(self, min_frp: float = 0.0) -> None:
        self._min_frp = min_frp

    def accepts(self, hotspot: FireHotspot) -> bool:
        return hotspot.frp >= self._min_frp


class TerritoryFilter:
    """Aceita apenas focos localizados dentro do território informado (ex.: Brasil)."""

    def __init__(self, territory: Territory) -> None:
        self._territory = territory

    def accepts(self, hotspot: FireHotspot) -> bool:
        return self._territory.contains(hotspot.longitude, hotspot.latitude)


class CompositeFilter:
    """Combina filtros: o foco é aceito apenas se todos aceitarem."""

    def __init__(self, filters: Iterable[HotspotFilter]) -> None:
        self._filters = tuple(filters)

    def accepts(self, hotspot: FireHotspot) -> bool:
        return all(f.accepts(hotspot) for f in self._filters)
