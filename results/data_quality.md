# Relatório de qualidade dos dados

Fonte: **alibaba2018** · agregação em intervalos de **300 s** · gerado por `make data`.

## Resumo

- 246.934.820 linhas brutas, 4.023 máquinas distintas (**N = 4023** na definição de demanda).
- 1.769 intervalos, cobrindo 6,142 dias, a partir de t = 160.500 s do rastro.
- Amostragem original estimada em ~10 s por máquina (amostras por intervalo, p05–p95: 29-30), confirmando que a amostragem é irregular.
- Divisão cronológica treino/validação/teste: 1061/353/355 intervalos.

## Cobertura e lacunas

- Cobertura mediana: 0,9978; mínima: 0,9779.
- Intervalos com cobertura < 100%: 1.769 de 1.769.
- Regra em vigor: `min_coverage = 0.9` (intervalos com cobertura abaixo disso viram lacuna), `trim_leading_missing = true` e `max_fill_gap = 3`.
- Intervalos sem nenhuma amostra: 0; preenchidos por interpolação: 0.
- Lacunas maiores que `max_fill_gap`: 0 (nenhuma).

As estatísticas por máquina abaixo são do **rastro completo** (2.304 intervalos), antes do corte:

- Mediana de intervalos com dado por máquina: 2.092 de 2.304.
- Máquinas cujo primeiro intervalo é 0: 2.348 de 4.023; primeiro intervalo por máquina (mín./mediana/máx.): 0/0/2067; último: 190/2303/2303. Os `time_stamp` compartilham a mesma origem; o que varia é o tempo de vida de cada máquina no rastro.
- `NaN` restantes em `demand_cpu`: 0.

## Amostras descartadas

- CPU nula ou fora de [0, 100]: 6 amostras (2.43e-08 das linhas).
- Memória nula ou fora de [0, 100]: 0 amostras.

## Demanda (em máquinas equivalentes totalmente utilizadas)

| Série | mín. | média | mediana | p95 | máx. |
|---|---|---|---|---|---|
| `demand_cpu` | 839,795 | 1.551,759 | 1.521,762 | 2.208,684 | 3.156,257 |
| `demand_mem` | 3.126,22 | 3.566,153 | 3.572,283 | 3.700,132 | 3.794,69 |

## Limitações

- **Demanda censurada:** a utilização por máquina tem teto de 100%, então em momentos
  de saturação a demanda observada subestima a demanda real.
- A série cobre 6,142 dias, o que deixa o conjunto de teste
  pequeno (limitação aceita no v0).

Tabela completa em `results/tables/data_quality.csv`.
