# Plano mestre — protótipo v0

Atualize os checklists conforme avança e registre problemas em `docs/DIARIO.md`.

## Visão geral das fases

| Fase | Entrega | *Time-box* | Portão |
|---|---|---|---|
| 0. Ambiente | uv + Docker funcionando, esqueleto, testes de fumaça | ½ dia | **G0** |
| 1. Dados | série de demanda de 5 min (Parquet) + relatório de qualidade | 1,5 dia | **G1** |
| 2. Baselines | previsores simples, avaliação *walk-forward*, tabela de erros | 1 dia | — |
| 3. Simulador | simulador, políticas, métricas, testes, validação | 1,5 dia | **G2** |
| 4. Experimento e pacote | curva custo × violações, tabelas, `RELATO.md` | 1 dia | **G3** |

As fases 2 e 3 podem se sobrepor: o simulador é testável com demanda sintética antes dos
baselines ficarem prontos. As demais seguem em ordem.

**Portões de revisão:** ao chegar em G0 a G3, pare, resuma em 5 linhas o que foi feito, mostre
os artefatos pedidos e espere aprovação do Gabriel.

## Fase 0 — Ambiente (`docs/specs/00-ambiente.md`)

- [x] `uv` instalado, projeto criado com layout `src/` e Python 3.12
- [x] dependências por grupos (`default`, `dev`, `nn` declarado e **não instalado**)
- [x] `uv.lock` gerado e versionado
- [x] `Makefile` com os alvos da spec
- [x] `Dockerfile` e `docker-compose.yml` com `uv sync --frozen`
- [x] `configs/v0.toml` com os parâmetros iniciais
- [x] teste de fumaça: `uv run pytest` e `docker compose run --rm app make test` passam

**G0:** o Gabriel roda `make setup && make test` e `docker compose run --rm app make test`
na própria máquina.

## Fase 1 — Dados (`docs/specs/01-dados.md`)

- [ ] obter o `machine_usage` do rastro Alibaba 2018 (ou acionar o *fallback*, ver riscos)
- [ ] confirmar o esquema real contra o arquivo e a documentação
- [ ] agregar em intervalos de 5 min com DuckDB e salvar em Parquet
- [ ] relatório de qualidade (lacunas, máquinas ausentes, estatísticas)
- [ ] funções `load_series()` e `split_series()` com testes
- [ ] figuras: série completa, um dia ampliado, autocorrelação

**G1:** o Gabriel olha as figuras e o relatório de qualidade e aprova a definição de demanda.

## Fase 2 — Baselines de previsão (`docs/specs/02-baselines.md`)

- [ ] interface `Forecaster` e protocolo de avaliação *walk-forward*
- [ ] persistência, média móvel, sazonal ingênuo, suavização exponencial (Holt-Winters), ARIMA
- [ ] teste de ausência de olhar para o futuro (*no-lookahead*) para cada previsor
- [ ] `results/tables/forecast_metrics.csv` com MAE, RMSE, MAPE e viés

## Fase 3 — Simulador (`docs/specs/03-simulador.md`)

- [ ] simulador de tempo discreto com *lead time* `L`
- [ ] políticas: estática no pico, oráculo, reativa estilo HPA, preditiva (qualquer `Forecaster`)
- [ ] métricas `C, V, U, O, changes, C_norm`
- [ ] testes de invariantes e casos feitos à mão
- [ ] validação: oráculo com `V = 0` e `U = 0`, estática e reativa com comportamento plausível

**G2:** o Gabriel revisa os testes e as verificações de sanidade antes de qualquer experimento.

## Fase 4 — Experimento e pacote (`docs/specs/04-experimento-e-pacote.md`)

- [ ] varredura de `m` (preditiva) e `u*` (reativa) no teste e na validação
- [ ] `results/tables/allocation_metrics.csv` e `results/tables/operating_points.csv`
- [ ] figura da curva custo × violações e demais figuras
- [ ] `make all` reproduz tudo do zero
- [ ] rascunho do `docs/RELATO.md` com números reais

**G3:** o Gabriel revisa o pacote final antes de enviar ao orientador.

## Riscos e planos B

| Risco | Plano B |
|---|---|
| Download do rastro Alibaba exige formulário ou credencial | Parar e avisar. Enquanto isso, usar os dados pré-processados em `saved_data/` do repositório `andreareds/TowardsUncertaintyAwareWorkloadPrediction`, que têm Google e Alibaba. Registrar a mudança no diário. |
| Agregação estoura a memória dentro do Docker | Rodar a fase de dados nativamente com `uv run`; o Parquet resultante é pequeno e o Docker cobre o resto. |
| ARIMA lento | Limitar a `h = 1` (ajuste no treino, atualização de estado sem reestimar) e registrar. |
| Docker toma mais de 1 h | Entregar a semana só com `uv`, anotar o problema e voltar ao Docker depois. |
| Série curta (8 dias) deixa o teste pequeno | Aceitar no v0 e registrar como limitação. Segundo dataset fica para a semana seguinte. |

## Fora do escopo desta semana

Rede neural, perda quantílica, segundo dataset, CloudSim Plus, otimização de hiperparâmetros,
posicionamento de VMs em servidores, aprendizado por reforço. Se uma tarefa parecer exigir
algo disso, pare e pergunte.

## Definição de pronto da semana

1. `make all` reproduz do zero: dados → baselines → simulação → tabelas e figuras.
2. Existe uma figura de custo × violações com pelo menos: estática, oráculo, reativa e três
   previsores.
3. `uv run pytest` passa, inclusive no Docker.
4. `docs/DIARIO.md` documenta problemas e soluções.
5. `docs/RELATO.md` está redigido com números que vêm de `results/`.
