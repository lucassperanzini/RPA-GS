# FIRMS Monitor – Robô de monitoramento de focos de incêndio

Automação em Python que consome a API **NASA FIRMS**, identifica focos de incêndio ativos,
classifica o risco pelo **FRP (Fire Radiative Power)**, registra as ocorrências em CSV e emite
alertas (log/console) quando o risco atinge o nível configurado.

## Fluxo

```
FIRMS API ──► Provider ──► Filtros (foco ativo) ──► Deduplicação ──► Classificador FRP
                                                                        │
                                              CSV (registro) ◄──────────┤
                                              Alertas (log)  ◄── nível ≥ ALERT_MIN_LEVEL
```

## Regras de risco (padrão, configuráveis)

| Nível   | FRP (MW)    |
|---------|-------------|
| Baixo   | < 10        |
| Médio   | 10 – < 50   |
| Alto    | 50 – < 100  |
| Crítico | ≥ 100       |

- Foco **ativo** = detecção que não seja de baixa confiança (VIIRS `l`; MODIS < `MIN_NUMERIC_CONFIDENCE`).
- O alerta é disparado para focos com nível ≥ `ALERT_MIN_LEVEL` (padrão `CRITICO`; use `ALTO` para ser avisado também de focos altos).
- Somente focos **novos** são registrados e alertados — um foco já presente no CSV não gera alerta novamente.

## Área monitorada

A consulta é feita por **área (bounding box)** via `/api/area`, pois o endpoint por país (`/api/country`)
foi descontinuado pela NASA. O padrão é o retângulo que envolve o Brasil:

```env
FIRMS_QUERY_MODE=area
FIRMS_BBOX=-74.0,-34.0,-34.7,5.3   # oeste,sul,leste,norte
```

> Por ser um retângulo, podem entrar focos de regiões de países vizinhos. Para monitorar um estado
> ou região específica, basta ajustar `FIRMS_BBOX`.

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
│   └── runner.py           # PeriodicRunner (execução em loop, resiliente a falhas)
├── infrastructure/         # Adaptadores concretos
│   ├── firms/              # queries.py, client.py (HTTP + retry), parser.py (CSV), provider.py
│   ├── persistence/        # CsvOccurrenceRepository
│   └── notification/       # LogAlertNotifier, CompositeNotifier
├── config.py               # Settings (variáveis de ambiente / .env)
├── logging_config.py       # Log em console + arquivo rotativo
└── bootstrap.py            # Composition root (injeção de dependências)
main.py                     # CLI
```

Cada classe tem responsabilidade única e a camada de aplicação depende apenas de **interfaces**
(`typing.Protocol`), então trocar CSV por banco ou log por e-mail/Telegram não exige mexer no caso de uso.

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # preencha FIRMS_MAP_KEY
```

MAP_KEY gratuita: https://firms.modaps.eosdis.nasa.gov/api/map_key/

## Uso

```bash
python main.py                        # executa um ciclo e encerra
python main.py --interval-minutes 30  # modo contínuo (Ctrl+C para parar)
python main.py --env-file outro.env   # usa outro arquivo de configuração
```

- Cada ciclo leva poucos segundos e consulta as últimas 24h (`FIRMS_DAY_RANGE`, de 1 a 5 dias).
- Intervalo recomendado: **30 a 60 minutos** — os dados NRT chegam à API cerca de 3h após a passagem do satélite.
- Para rodar sem terminal aberto, agende `python main.py` no Agendador de Tarefas do Windows (ou cron).

Códigos de saída: `0` sucesso · `1` erro na API FIRMS · `2` configuração inválida.

### Saídas

| Arquivo                   | Conteúdo                                              |
|---------------------------|-------------------------------------------------------|
| `data/ocorrencias.csv`    | Todas as ocorrências processadas, sem duplicatas       |
| `logs/firms_monitor.log`  | Log de execução e alertas (linhas `WARNING`)           |

## Configuração (`.env`)

| Variável                  | Padrão                  | Descrição                                    |
|---------------------------|-------------------------|----------------------------------------------|
| `FIRMS_MAP_KEY`           | —                       | Chave da API (obrigatória)                   |
| `FIRMS_SOURCE`            | `VIIRS_NOAA20_NRT`      | Sensor/satélite (ex.: `MODIS_NRT`)           |
| `FIRMS_QUERY_MODE`        | `area`                  | `area` (recomendado) ou `country`            |
| `FIRMS_BBOX`              | `-74.0,-34.0,-34.7,5.3` | Área monitorada (oeste,sul,leste,norte)      |
| `FIRMS_DAY_RANGE`         | `1`                     | Dias retroativos (1 a 5)                     |
| `RISK_MEDIO_FRP` / `RISK_ALTO_FRP` / `RISK_CRITICO_FRP` | `10` / `50` / `100` | Faixas de risco em MW |
| `ALERT_MIN_LEVEL`         | `CRITICO`               | `BAIXO`, `MEDIO`, `ALTO` ou `CRITICO`        |
| `MIN_NUMERIC_CONFIDENCE`  | `30`                    | Confiança mínima (sensores numéricos/MODIS)  |
| `OUTPUT_CSV`              | `data/ocorrencias.csv`  | Arquivo de registro                          |
| `LOG_FILE` / `LOG_LEVEL`  | `logs/firms_monitor.log` / `INFO` | Log                                |

## Acoplando em outro projeto

```python
from firms_monitor import Settings, build_fire_monitor

report = build_fire_monitor(Settings.from_env()).run()
print(report.summary())
```

Para enviar alertas por outro canal (voz, e-mail, Telegram, assistente pessoal...), basta criar uma
classe com o método `notify()` e injetá-la:

```python
from firms_monitor import PeriodicRunner
from firms_monitor.infrastructure.notification import CompositeNotifier, LogAlertNotifier

class MeuNotifier:
    def notify(self, occurrences):
        maior = max(occurrences, key=lambda o: o.hotspot.frp)
        print(f"{len(occurrences)} foco(s) de risco elevado; maior FRP {maior.hotspot.frp:.0f} MW")

notifier = CompositeNotifier([LogAlertNotifier(), MeuNotifier()])
service = build_fire_monitor(Settings.from_env(), notifier=notifier)
PeriodicRunner(service, interval_seconds=30 * 60).run_forever()
```

Da mesma forma, `build_fire_monitor(settings, repository=...)` aceita outro repositório
(banco de dados, planilha etc.) que implemente `existing_ids()` e `save_many()`.
