"""Formatação visual dos logs no console: cores, ícones, banner de alerta e resumo em caixa.

Afeta somente o console. O arquivo de log continua em texto puro (melhor para busca e auditoria).
Os dados estruturados chegam pelo `extra` do logging:
    - extra={"report": ExecutionReport}      -> caixa de resumo do ciclo
    - extra={"alert_count": int}             -> banner de alerta
    - extra={"occurrence": ClassifiedHotspot} -> linha de foco com selo de risco
Cores podem ser forçadas/desligadas pelas variáveis padrão FORCE_COLOR / NO_COLOR.
"""

from __future__ import annotations

import logging
import os
from typing import TextIO

from firms_monitor.domain.models import ClassifiedHotspot, RiskLevel

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def _fg(code: int) -> str:
    return f"\033[38;5;{code}m"


def _bg(code: int) -> str:
    return f"\033[48;5;{code}m"


# nível do log -> (estilo, ícone unicode, ícone ascii)
_LEVEL_STYLE = {
    logging.DEBUG: (_fg(244), "·", "."),
    logging.INFO: (_fg(39), "•", "*"),
    logging.WARNING: (_fg(214), "⚠", "!"),
    logging.ERROR: (_fg(196), "✖", "x"),
    logging.CRITICAL: (BOLD + _fg(196), "✖", "x"),
}

# nível de risco -> (estilo do selo, estilo do texto)
_RISK_STYLE = {
    RiskLevel.BAIXO: (_fg(16) + _bg(34), _fg(34)),
    RiskLevel.MEDIO: (_fg(16) + _bg(220), _fg(220)),
    RiskLevel.ALTO: (BOLD + _fg(16) + _bg(208), _fg(208)),
    RiskLevel.CRITICO: (BOLD + _fg(231) + _bg(160), _fg(196)),
}

_ALERT = BOLD + _fg(196)
_OK = _fg(34)
_MUTED = _fg(244)
_BAR_WIDTH = 24


class ConsoleFormatter(logging.Formatter):
    def __init__(self, use_colors: bool = True, use_unicode: bool = True) -> None:
        super().__init__()
        self._colors = use_colors
        self._unicode = use_unicode

    @classmethod
    def for_stream(cls, stream: TextIO, use_colors: bool | None = None) -> "ConsoleFormatter":
        encoding = (getattr(stream, "encoding", "") or "").lower()
        if use_colors is None:
            use_colors = _colors_supported(stream)
        return cls(use_colors=use_colors, use_unicode="utf" in encoding)

    # ------------------------------------------------------------------ roteamento
    def format(self, record: logging.LogRecord) -> str:
        report = getattr(record, "report", None)
        occurrence = getattr(record, "occurrence", None)
        alert_count = getattr(record, "alert_count", None)

        if report is not None:
            text = self._format_report(record, report)
        elif occurrence is not None:
            text = self._format_occurrence(record, occurrence)
        elif alert_count is not None:
            text = self._format_alert_banner(record, alert_count)
        else:
            text = self._format_default(record)

        if record.exc_info:
            text += "\n" + self._paint(_fg(196), self.formatException(record.exc_info))
        return text

    # ------------------------------------------------------------------ linhas
    def _format_default(self, record: logging.LogRecord) -> str:
        style, icon_u, icon_a = _LEVEL_STYLE.get(record.levelno, _LEVEL_STYLE[logging.INFO])
        icon = icon_u if self._unicode else icon_a
        component = _component_name(record.name)
        message = record.getMessage()
        if record.levelno >= logging.WARNING:
            message = self._paint(style, message)
        return f"{self._time(record)}  {self._paint(style, icon)} {self._paint(_MUTED, f'{component:<10}')} {message}"

    def _format_alert_banner(self, record: logging.LogRecord, count: int) -> str:
        line = "━" if self._unicode else "="
        fire = "🔥 " if self._unicode else ""
        title = f" {fire}ALERTA: {count} foco(s) de incêndio com risco elevado "
        return f"\n{self._time(record)}  " + self._paint(_ALERT, f"{line * 6}{title}{line * 6}")

    def _format_occurrence(self, record: logging.LogRecord, occurrence: ClassifiedHotspot) -> str:
        h = occurrence.hotspot
        badge_style, text_style = _RISK_STYLE[occurrence.risk_level]
        badge = self._paint(badge_style, f" {occurrence.risk_level.label.upper():<7} ")
        arrow = "↳" if self._unicode else "->"
        details = (
            f"{self._paint(BOLD + text_style, f'{h.frp:>7.1f} MW')}  "
            f"{h.acquired_at:%d/%m %H:%M} UTC  "
            f"({h.latitude:.5f}, {h.longitude:.5f})  "
            f"{self._paint(_MUTED, f'conf={h.confidence} sat={h.satellite}')}"
        )
        indent = " " * 10
        return (
            f"{self._time(record)}  {badge} {details}\n"
            f"{indent}  {self._paint(_MUTED, f'{arrow} {h.maps_url}')}"
        )

    # ------------------------------------------------------------------ resumo
    def _format_report(self, record: logging.LogRecord, report) -> str:
        duration = (report.finished_at - report.started_at).total_seconds()
        alert_style = _ALERT if report.alerts_sent else _OK

        rows: list[tuple[str, str]] = [  # (texto puro, texto colorido)
            self._row("Coletados", str(report.fetched)),
            self._row("Ativos", str(report.accepted)),
            self._row("Novos", str(report.new_occurrences), BOLD),
            self._row("Alertas", str(report.alerts_sent), alert_style),
            self._row("Duração", f"{duration:.1f}s"),
            ("", ""),
        ]
        rows.extend(self._level_rows(report.by_level))
        title = f" Resumo do ciclo · {self.formatTime(record, '%H:%M:%S')} "
        return self._box(title, rows)

    def _row(self, label: str, value: str, style: str = "") -> tuple[str, str]:
        plain = f"{label:<11}{value}"
        colored = self._paint(_MUTED, f"{label:<11}") + (self._paint(style, value) if style else value)
        return plain, colored

    def _level_rows(self, by_level: dict[RiskLevel, int]) -> list[tuple[str, str]]:
        biggest = max(by_level.values(), default=0)
        block = "█" if self._unicode else "#"
        rows = []
        for level in RiskLevel:
            qty = by_level.get(level, 0)
            size = 0 if not biggest else max(1 if qty else 0, round(qty / biggest * _BAR_WIDTH))
            bar = block * size
            label = f"{level.label:<9}{qty:>6}  "
            plain = label + bar
            colored = self._paint(_RISK_STYLE[level][1], label) + self._paint(_RISK_STYLE[level][1], bar)
            rows.append((plain, colored))
        return rows

    def _box(self, title: str, rows: list[tuple[str, str]]) -> str:
        tl, tr, bl, br, h, v = ("╭", "╮", "╰", "╯", "─", "│") if self._unicode else ("+", "+", "+", "+", "-", "|")
        width = max(40, len(title) + 4, *(len(plain) + 2 for plain, _ in rows))
        top = f"{tl}{h}{title}{h * (width - len(title) - 1)}{tr}"
        body = [f"{v} {colored}{' ' * (width - len(plain) - 2)} {v}" for plain, colored in rows]
        bottom = f"{bl}{h * width}{br}"
        lines = [self._paint(_MUTED, top), *body, self._paint(_MUTED, bottom)]
        return "\n" + "\n".join(lines)

    # ------------------------------------------------------------------ util
    def _time(self, record: logging.LogRecord) -> str:
        return self._paint(DIM, self.formatTime(record, "%H:%M:%S"))

    def _paint(self, style: str, text: str) -> str:
        return f"{style}{text}{RESET}" if self._colors and style else text


_COMPONENT_ALIASES = {
    "firms_monitor": "main",
    "csv_repository": "csv",
    "provider": "firms",
    "client": "firms",
    "parser": "parser",
}


def _component_name(logger_name: str) -> str:
    last = logger_name.rsplit(".", 1)[-1]
    return _COMPONENT_ALIASES.get(last, last)[:10]


def _colors_supported(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return _enable_windows_ansi() or True
    if not (hasattr(stream, "isatty") and stream.isatty()):
        return False
    return _enable_windows_ansi()


def _enable_windows_ansi() -> bool:
    """Ativa sequências ANSI no console do Windows (no-op em outros sistemas)."""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        return False
