# Relatório de qualidade dos dados

Fonte: **alibaba2018** · agregação em intervalos de **300 s** · gerado por `make data`.

## Resumo

- 246,934,820 linhas brutas, 4,023 máquinas distintas (**N = 4023** na definição de demanda).
- 2,304 intervalos, cobrindo 8.0 dias.
- Amostragem original estimada em ~10.0 s por máquina (amostras por intervalo, p05–p95: 29-30), confirmando que a amostragem é irregular.
- Divisão cronológica treino/validação/teste: 1382/460/462 intervalos.

## Cobertura e lacunas

- Cobertura mediana: 0.9975; mínima: 0.0000.
- Intervalos com cobertura < 100%: 1.0000 do total.
- Intervalos sem nenhuma amostra: 61; preenchidos por interpolação: 0.
- Lacunas maiores que `max_fill_gap`: 1 (t=473 (61 intervalos)).
- Mediana de intervalos com dado por máquina: 2092.0 de 2304.
- Máquinas cujo primeiro intervalo é 0: 2348 de 4023; primeiro intervalo por máquina (mín./mediana/máx.): 0/0/2067; último: 190/2303/2303. Isso responde se os `time_stamp` compartilham a mesma origem.
- `NaN` restantes em `demand_cpu`: 61.

## Amostras descartadas

- CPU nula ou fora de [0, 100]: 6 amostras (2.43e-08 das linhas).
- Memória nula ou fora de [0, 100]: 0 amostras.

## Demanda (em máquinas equivalentes totalmente utilizadas)

| Série | mín. | média | mediana | p95 | máx. |
|---|---|---|---|---|---|
| `demand_cpu` | 670.472 | 1528.456 | 1486.912 | 2197.262 | 3156.257 |
| `demand_mem` | 3126.22 | 3540.56 | 3550.45 | 3690.827 | 3794.69 |

## Limitações

- **Demanda censurada:** a utilização por máquina tem teto de 100%, então em momentos
  de saturação a demanda observada subestima a demanda real.
- A série cobre ~8 dias, o que deixa o conjunto de teste pequeno (limitação aceita
  no v0).

Tabela completa em `results/tables/data_quality.csv`.
