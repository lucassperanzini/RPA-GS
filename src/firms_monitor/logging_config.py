from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from firms_monitor.presentation.console_formatter import ConsoleFormatter

_FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO", log_file: Path | None = None, use_colors: bool | None = None) -> None:
    """Console visual (cores/ícones) + arquivo rotativo em texto puro.

    use_colors=None detecta automaticamente (respeita NO_COLOR / FORCE_COLOR).
    """
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ConsoleFormatter.for_stream(sys.stdout, use_colors))
    handlers: list[logging.Handler] = [console]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
