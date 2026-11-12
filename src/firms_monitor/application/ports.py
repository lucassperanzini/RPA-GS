"""Portas (interfaces) que a camada de aplicação espera da infraestrutura.

Qualquer implementação que respeite estes contratos pode ser plugada
(ex.: trocar CSV por banco de dados, log por e-mail/Telegram) sem alterar o caso de uso.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from firms_monitor.domain.models import ClassifiedHotspot, FireHotspot


class HotspotProvider(Protocol):
    """Fonte de focos de incêndio."""

    def fetch(self) -> list[FireHotspot]: ...


class OccurrenceRepository(Protocol):
    """Armazena as ocorrências processadas."""

    def existing_ids(self) -> set[str]: ...

    def save_many(self, occurrences: Sequence[ClassifiedHotspot]) -> int: ...


class AlertNotifier(Protocol):
    """Canal de envio de alertas."""

    def notify(self, occurrences: Sequence[ClassifiedHotspot]) -> None: ...
