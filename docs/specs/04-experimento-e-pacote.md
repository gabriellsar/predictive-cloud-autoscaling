# Fase 4 — Experimento principal e pacote para o orientador

**Objetivo:** produzir a figura e as tabelas centrais e reunir tudo em algo que o Gabriel possa
enviar ao orientador em 21/10. **Time-box:** 1 dia.

## 1. Experimento

Para cada política e parâmetro de `configs/v0.toml`, simular em `val` e em `test`, com `L` de
`lead_time` (padrão 1). Rodar também uma **análise de sensibilidade** com `L = 2` (a mesma
figura, em arquivo separado), pois mostra o efeito do atraso sobre a política reativa.

Previsores usados na política preditiva: `naive`, `moving_average`, `seasonal_naive`,
`holt_winters` e `arima` (os que não estiverem disponíveis para `h = L` devem ser omitidos e
a omissão registrada no diário).

## 2. Tabelas

**`results/tables/allocation_metrics.csv`** — uma linha por (política, previsor, parâmetro, split, L):

`policy, forecaster, param_name, param, L, split, C, C_norm, V, U, O, changes`

**`results/tables/operating_points.csv`** — para cada (política, previsor) e cada `ε` em `epsilons`:

1. escolher, **usando só a validação**, o parâmetro menos custoso com `V_val ≤ ε`
   (a menor margem `m`, ou o maior `u_star`);
2. reportar as métricas desse parâmetro **no teste**.

Se nenhum parâmetro cumprir `ε` na validação, marcar `n/a`. Colunas:
`policy, forecaster, epsilon, param_name, param, C_norm_test, V_test, U_test, O_test, changes_test`.

## 3. Figuras (`results/figures/`)

1. **`pareto_cost_violation.png` (a figura central).** Eixo x: `V` (fração de intervalos com
   violação) no teste. Eixo y: `C_norm`. Uma curva por previsor (variando `m`), uma curva para a
   reativa (variando `u_star`), pontos para estática e oráculo. Marcar `ε = 1%` e `ε = 5%` com linhas
   verticais. Quanto mais para baixo e para a esquerda, melhor. Legenda e rótulos em português.
2. `pareto_cost_violation_L2.png` — a mesma figura com `L = 2`.
3. `cost_at_epsilon.png` — barras com `C_norm` no teste, para cada previsor, no ponto de operação de
   `ε = 5%` (e `ε = 1%` ao lado). Mostra diretamente quanto cada previsor custa para cumprir o mesmo SLO.
4. `rmse_vs_cost.png` — dispersão com RMSE (`h = L`) no eixo x e `C_norm` no ponto de operação no
   eixo y, um ponto por previsor. Serve para discutir se menor erro de previsão leva a menor custo.

Todas legíveis em tamanho de página A4, com cores distinguíveis também em preto e branco
(estilos de linha e marcadores diferentes).

## 4. Reprodutibilidade

`make all` deve gerar, do zero e sem intervenção, todos os arquivos de `results/` a partir de
`data/raw/`. Teste isso em um clone limpo do repositório. Confirme também que
`docker compose run --rm app make sim` funciona quando `data/processed/` já existe.

## 5. Documentos finais

### `docs/DIARIO.md`

Mantido ao longo da semana. Estrutura por entrada: **data**, **o que foi feito**, **problemas
encontrados**, **como foram contornados**, **pendências**. Esses registros alimentam a seção
"Revisão do Plano de Ação" do relatório.

### `docs/RELATO.md` (rascunho para o Gabriel editar)

Segue o formato que o manual do Projeto Final I pede para cada contato com o orientador:

1. **O que foi feito desde o último relato** (com os números que vêm de `results/`).
2. **Dificuldades ou problemas encontrados.**
3. **Quais deles ainda estão sem solução.**
4. **Planejamento da próxima quinzena** (a rede neural em PyTorch, comparação na mesma tabela,
   segundo dataset se der tempo; relacionar com o cronograma até 10/11).

Em seguida, uma seção **Decisões para o orientador validar**: dataset principal, horizonte de
previsão `h = L`, lista de baselines, simulador próprio versus CloudSim Plus. Para cada uma,
inclua a recomendação do protótipo e a evidência que o suporta. Inclua também uma seção
**Limitações conhecidas**: série curta, demanda censurada, violação aproximada pela demanda
não atendida, atraso simétrico, custo único por instância.

Toda afirmação numérica deve apontar para o arquivo de `results/` de onde veio.

### `results/README.md`

Uma tabela com cada arquivo de `results/`, o que contém e qual comando o gera.

## Critérios de aceite (G3)

- [ ] as duas tabelas e as 4 figuras (mais a de `L = 2`) geradas por `make all`
- [ ] a figura central mostra estática, oráculo, reativa e pelo menos três previsores
- [ ] `make all` reproduz tudo em um clone limpo; `make test` passa local e no Docker
- [ ] `docs/DIARIO.md`, `docs/RELATO.md` e `results/README.md` redigidos
- [ ] nenhum número no relato sem fonte em `results/`
- [ ] o Gabriel revisou e aprovou antes do envio
