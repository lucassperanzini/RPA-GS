"""Atalho para executar o robô a partir do código-fonte: `python main.py [opções]`."""

import sys

from firms_monitor.cli import main

if __name__ == "__main__":
    sys.exit(main())
