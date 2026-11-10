"""Ponto de entrada do robô.

Uso:
    python main.py                       # executa um ciclo (ideal para Agendador de Tarefas/cron)
    python main.py --interval-minutes 30 # executa continuamente a cada 30 minutos
"""

from __future__ import annotations

import argparse
import logging
import sys

from firms_monitor import PeriodicRunner, Settings, build_fire_monitor
from firms_monitor.config import ConfigurationError
from firms_monitor.infrastructure.firms import FirmsApiError
from firms_monitor.logging_config import setup_logging


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitoramento de focos de incêndio via NASA FIRMS.")
    parser.add_argument("--interval-minutes", type=float, default=None, help="Executa em loop neste intervalo.")
    parser.add_argument("--env-file", default=".env", help="Caminho do arquivo .env (padrão: .env).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # acentos corretos no console do Windows
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    args = parse_args(argv)
    try:
        settings = Settings.from_env(dotenv_path=args.env_file)
    except ConfigurationError as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 2

    setup_logging(settings.log_level, settings.log_file)
    logger = logging.getLogger("firms_monitor")
    service = build_fire_monitor(settings)

    if args.interval_minutes:
        try:
            PeriodicRunner(service, args.interval_minutes * 60).run_forever()
        except KeyboardInterrupt:
            logger.info("Execução interrompida pelo usuário.")
        return 0

    try:
        service.run()
    except FirmsApiError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
