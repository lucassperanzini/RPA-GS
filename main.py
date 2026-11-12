"""Atalho para executar o robô a partir do código-fonte: `python main.py [opções]`.

O código fica em `src/firms_monitor/`. Este atalho adiciona `src/` ao caminho de importação,
então funciona mesmo sem instalar o pacote.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from firms_monitor.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
