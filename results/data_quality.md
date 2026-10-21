# Relatório de qualidade dos dados

Fonte: **alibaba2018** · agregação em intervalos de **300 s** · gerado por `make data`.

## Resumo

- 246.934.820 linhas brutas, 4.023 máquinas distintas (**N = 4023** na definição de demanda).
- 2.304 intervalos, cobrindo 8 dias, a partir de t = 0 s do rastro.
- Amostragem original estimada em ~10 s por máquina (amostras por intervalo, p05–p95: 29-30), confirmando que a amostragem é irregular.
- Divisão cronológica treino/validação/teste: 1382/460/462 intervalos.

## Cobertura e lacunas

- Cobertura dos intervalos observados (não preenchidos): mediana 0,9978; mínima: 0,5372.
- Cobertura por *split* (mín./mediana/média, só intervalos observados): no treino 0,5372/0,9978/0,8858; na validação 0,9843/0,9978/0,9965; no teste 0,9779/0,9975/0,9961.
- Intervalos com cobertura < 100%: 2.304 de 2.304.
- Regra em vigor: `min_coverage = 0.5` (intervalos com cobertura abaixo disso viram lacuna), `trim_leading_missing = false`, `max_fill_gap = 3` (lacunas curtas: interpolação linear) e `long_gap_fill = "seasonal"` (lacunas longas).
- Intervalos sem nenhuma amostra: 61; com amostras, mas abaixo de `min_coverage`: 4; preenchidos: 65, dos quais 65 pelo método sazonal.
- Lacunas maiores que `max_fill_gap`: 1 — t=470..534 (65 intervalos, preenchida).
- Método sazonal: cada intervalo da lacuna recebe a demanda do mesmo horário do dia anterior (`s = 288` intervalos antes), somada a uma correção que varia linearmente entre a diferença observada na borda esquerda e a observada na borda direita. Toda lacuna preenchida assim fica no treino (conferido em `make data`), de modo que nenhuma previsão da validação ou do teste usa dado posterior à sua origem.

As estatísticas por máquina abaixo são do **rastro completo** (2.304 intervalos), independentemente de qualquer corte:

- Mediana de intervalos com dado por máquina: 2.092 de 2.304.
- Máquinas cujo primeiro intervalo é 0: 2.348 de 4.023; primeiro intervalo por máquina (mín./mediana/máx.): 0/0/2067; último: 190/2303/2303. Os `time_stamp` compartilham a mesma origem; o que varia é o tempo de vida de cada máquina no rastro.
- `NaN` restantes em `demand_cpu`: 0.

## Amostras descartadas

- CPU nula ou fora de [0, 100]: 6 amostras (2.43e-08 das linhas).
- Memória nula ou fora de [0, 100]: 0 amostras.

## Demanda (em máquinas equivalentes totalmente utilizadas)

Só intervalos observados; os preenchidos ficam de fora das estatísticas.

| Série | mín. | média | mediana | p95 | máx. |
|---|---|---|---|---|---|
| `demand_cpu` | 670,472 | 1.528,723 | 1.486,912 | 2.197,451 | 3.156,257 |
| `demand_mem` | 3.126,22 | 3.540,494 | 3.550,45 | 3.690,644 | 3.794,69 |

## Limitações

- **Demanda censurada:** a utilização por máquina tem teto de 100%, então em momentos
  de saturação a demanda observada subestima a demanda real.
- **Cobertura desigual:** onde a cobertura é menor, a demanda é a média das máquinas que
  reportaram vezes N, isto é, uma extrapolação que supõe que as ausentes se comportam
  como as presentes.
- **Intervalos preenchidos:** 65 intervalos são estimativas, não medições;
  entram no ajuste dos previsores, mas não nas métricas de previsão nem de alocação.
- A série cobre 8 dias, o que deixa o conjunto de teste
  pequeno (limitação aceita no v0).

Tabela completa em `results/tables/data_quality.csv`.
