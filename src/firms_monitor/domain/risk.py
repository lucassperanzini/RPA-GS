"""Regras de negócio para classificação de risco com base no FRP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from firms_monitor.domain.models import FireHotspot, RiskLevel


@dataclass(frozen=True, slots=True)
class RiskRule:
    """Um foco recebe `level` quando seu FRP é maior ou igual a `min_frp`."""

    level: RiskLevel
    min_frp: float


class RiskClassifier:
    """Classifica focos aplicando a regra de maior limiar atendido."""

    def __init__(self, rules: Iterable[RiskRule]) -> None:
        ordered = sorted(rules, key=lambda rule: rule.min_frp, reverse=True)
        if not ordered:
            raise ValueError("É necessário ao menos uma regra de risco.")
        if ordered[-1].min_frp > 0:
            raise ValueError("A menor regra precisa começar em FRP 0 para cobrir todos os focos.")
        self._rules = tuple(ordered)

    @classmethod
    def from_thresholds(cls, medio: float, alto: float, critico: float) -> "RiskClassifier":
        """Atalho para o modelo padrão de 4 níveis: Baixo < medio <= Médio < alto <= Alto < critico <= Crítico."""
        if not 0 < medio < alto < critico:
            raise ValueError("Os limiares devem satisfazer 0 < médio < alto < crítico.")
        return cls(
            [
                RiskRule(RiskLevel.BAIXO, 0.0),
                RiskRule(RiskLevel.MEDIO, medio),
                RiskRule(RiskLevel.ALTO, alto),
                RiskRule(RiskLevel.CRITICO, critico),
            ]
        )

    @property
    def rules(self) -> tuple[RiskRule, ...]:
        return self._rules

    def classify(self, hotspot: FireHotspot) -> RiskLevel:
        frp = max(hotspot.frp, 0.0)
        for rule in self._rules:
            if frp >= rule.min_frp:
                return rule.level
        return self._rules[-1].level  # inalcançável pela validação do construtor
