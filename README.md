# FIRMS Monitor – Robô de monitoramento de focos de incêndio

Automação em Python que consome a API **NASA FIRMS**, identifica focos de incêndio ativos,
classifica o risco pelo **FRP (Fire Radiative Power)**, registra as ocorrências em CSV e emite
alertas (log/console) para situações críticas.

## Fluxo

```
FIRMS API ──► Provider ──► Filtros (foco ativo) ──► Deduplicação ──► Classificador FRP
                                                                        │
                                              CSV (registro) ◄──────────┤
                                              Alertas (log)  ◄── nível ≥ ALERT_MIN_LEVEL
```

## Regras de risco (padrão, configuráveis)

| Nível   | FRP (MW)        |
|---------|-----------------|
| Baixo   | < 10            |
| Médio   | 10 – < 50       |
| Alto    | 50 – < 100      |
| Crítico | ≥ 100 (alerta)  |

Foco "ativo" = detecção que não seja de baixa confiança (VIIRS `l`; MODIS < `MIN_NUMERIC_CONFIDENCE`).

## Arquitetura

```
firms_monitor/
├── domain/                 # Regras de negócio puras (sem I/O)
│   ├── models.py           # FireHotspot, ClassifiedHotspot, RiskLevel
│   ├── risk.py             # RiskRule, RiskClassifier
│   └── filters.py          # ConfidenceFilter, MinFrpFilter, CompositeFilter
├── application/            # Casos de uso
│   ├── ports.py            # Interfaces: HotspotProvider, OccurrenceRepository, AlertNotifier
│   ├── monitor.py          # FireMonitorService (orquestração) + ExecutionReport
│   └── runner.py           # PeriodicRunner (execução em loop)
├── infrastructure/         # Adaptadores concretos
│   ├── firms/              # queries.py, client.py (HTTP + retry), parser.py (CSV), provider.py
│   ├── persistence/        # CsvOccurrenceRepository
│   └── notification/       # LogAlertNotifier, CompositeNotifier
├── config.py               # Settings (variáveis de ambiente / .env)
├── logging_config.py
└── bootstrap.py            # Composition root (injeção de dependências)
main.py                     # CLI
```

Cada classe tem responsabilidade única e a camada de aplicação depende apenas de **interfaces**
(`typing.Protocol`), então trocar CSV por banco ou log por e-mail não exige mexer no caso de uso.

## Instalação e uso

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # preencha FIRMS_MAP_KEY
python main.py                        # um ciclo (ideal para Agendador de Tarefas do Windows / cron)
python main.py --interval-minutes 30  # modo contínuo
```

MAP_KEY gratuita: https://firms.modaps.eosdis.nasa.gov/api/map_key/

Saídas: `data/ocorrencias.csv` (sem duplicatas entre execuções) e `logs/firms_monitor.log`.

## Acoplando em outro projeto

```python
from firms_monitor import Settings, build_fire_monitor

report = build_fire_monitor(Settings.from_env()).run()
print(report.summary())
```

Com implementações próprias (ex.: alerta por e-mail):

```python
class EmailNotifier:
    def notify(self, occurrences): ...   # basta respeitar o contrato AlertNotifier

service = build_fire_monitor(settings, notifier=EmailNotifier())
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```
