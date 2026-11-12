# Testes

## Como executar

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

Os testes não acessam a internet nem usam a chave da API: a NASA FIRMS é simulada e os arquivos
são criados em pastas temporárias.

## Cobertura (57 testes automatizados)

| Arquivo | Tipo | O que verifica |
|---|---|---|
| `test_domain.py` | Decisão | Classificação nos limites de FRP (9,99 / 10 / 49,9 / 50 / 99,9 / 100), filtros de confiança |
| `test_territory.py` | Decisão | Pontos dentro (Brasília, Manaus, Porto Alegre) e fora do Brasil (Assunção, Lima, Bolívia, oceano) |
| `test_firms.py` | Sucesso / falha | Leitura do CSV da FIRMS (VIIRS e MODIS), linhas inválidas, erro da API com chave mascarada |
| `test_monitor.py` | Sucesso / decisão / falha | Ciclo completo, deduplicação, nível mínimo de alerta, CSV sem cabeçalho, migração de formato, robô contínuo após falha |
| `test_config.py` | Falha | Configuração sem chave, modos de consulta |

## Evidências (`evidencias/`)

Saídas reais geradas em 12/11/2026 (sem chave nem dados pessoais):

| Arquivo | Cenário | Resultado |
|---|---|---|
| `resultado_pytest.txt` | Testes automatizados | 57 aprovados |
| `cenario_01_sucesso_com_alertas.txt` | Execução real | 6582 focos coletados, 4093 no Brasil, 64 alertas (44 Alto + 20 Crítico), código 0 |
| `cenario_02_deduplicacao.txt` | Segunda execução | 0 novos, 0 alertas repetidos, código 0 |
| `cenario_03_falha_api.txt` | Chave inválida | Erro registrado, chave mascarada (`***`), código 1 |
| `cenario_04_falha_configuracao.txt` | Sem chave configurada | Mensagem clara, código 2 |

As imagens correspondentes estão em [`../assets/`](../assets/).
