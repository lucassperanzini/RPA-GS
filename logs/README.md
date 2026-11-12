# Logs

Amostras reais geradas pelo robô, sem dados sensíveis (a chave da API aparece sempre como `***`
e os caminhos são relativos).

| Arquivo | Conteúdo |
|---|---|
| `amostra_execucao_sucesso.log` | Dois ciclos: o 1º registra 4093 focos e emite 64 alertas; o 2º não encontra focos novos |
| `amostra_execucao_falha.log` | Ciclo interrompido por chave inválida (HTTP 400), com a chave mascarada |

## Formato

```
data e hora | nível | componente | mensagem
2026-11-12 18:40:47,064 | INFO     | firms_monitor.application.monitor | Focos coletados: 6582 | ativos após filtros: 4093
```

- `INFO`: etapas do ciclo e resumo final (relatório consolidado).
- `WARNING`: alertas de focos de risco elevado e linhas da API ignoradas por dado inválido.
- `ERROR`: falhas (API, configuração, arquivo de registro).

O log real de execução (`logs/firms_monitor.log`) não é versionado. Ele é rotativo
(até 5 MB por arquivo, 5 arquivos de histórico).
