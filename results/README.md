# Resultados

Tudo nesta pasta é gerado por `make all` a partir de `data/raw/machine_usage.csv`, exceto este
README. Nenhum número é escrito à mão: tabelas, figuras e relatórios saem do código em `src/tcc/`
com os parâmetros de `configs/v0.toml`.

| Arquivo | Conteúdo | Gerado por |
|---|---|---|
| `data_quality.md` | Relatório de qualidade dos dados: cobertura (geral e por *split*), lacunas e como foram preenchidas, amostragem e estatísticas da demanda | `make data` |
| `tables/data_quality.csv` | As mesmas métricas de qualidade, em formato de tabela | `make data` |
| `figures/series_full.png` | Demanda de CPU no período inteiro, com a divisão treino/validação/teste, o trecho preenchido tracejado e, abaixo, a cobertura por intervalo | `make data` |
| `figures/series_day.png` | Um dia ampliado: variação intradiária de CPU e memória | `make data` |
| `figures/acf_cpu.png` | Autocorrelação da demanda até 2 dias, só no treino e sem os intervalos preenchidos, com o período de 288 marcado | `make data` |
| `figures/cpu_vs_mem.png` | Dispersão CPU × memória no treino, sem os intervalos preenchidos, com a correlação de Pearson | `make data` |
| `tables/forecast_metrics.csv` | MAE, RMSE, MAPE, viés e taxa de subestimação por previsor (cinco clássicos e GRU), horizonte e *split* | `make baselines` |
| `figures/forecast_vs_actual.png` | Previsão contra demanda real no início do teste, h = 1 | `make baselines` |
| `figures/rmse_by_model.png` | RMSE no teste por previsor e horizonte | `make baselines` |
| `sanity.md` | Verificações de sanidade do simulador (G2), com as simplificações do modelo | `make sim` |
| `tables/sanity_policies.csv` | Tabela das verificações de sanidade, no teste | `make sim` |
| `figures/sanity_policies.png` | Demanda contra capacidade alocada, por política | `make sim` |
| `tables/allocation_metrics.csv` | Uma linha por (política, previsor, parâmetro, *split*, L): C, C_norm, V, U, O, changes | `make sim` |
| `tables/operating_points.csv` | Parâmetro escolhido na validação para cada ε e suas métricas no teste | `make sim` |
| `figures/pareto_cost_violation.png` | **Figura central:** custo normalizado × violações no teste, L = 1 | `make sim` |
| `figures/pareto_cost_violation_L2.png` | A mesma figura com L = 2 (sensibilidade ao atraso) | `make sim` |
| `figures/cost_at_epsilon.png` | C_norm no teste no ponto de operação de ε = 1% e ε = 5% | `make sim` |
| `figures/rmse_vs_cost.png` | RMSE da previsão (h = L) contra C_norm no ponto de operação; um "x" marca os pontos que passam de ε no teste | `make sim` |

`make sim` depende de `data/processed/` (de `make data`) e de `tables/forecast_metrics.csv`
(de `make baselines`). A ordem é a de `make all`: `data` → `baselines` → `sim`.

A GRU (`gru` nas tabelas) só aparece se o grupo `nn` estiver instalado (`uv sync --group nn`);
sem ele, `make baselines` e `make sim` seguem com os cinco previsores clássicos e avisam a omissão.

Em `operating_points.csv`, `n/a` significa que nenhum parâmetro da grade cumpriu ε na validação.
