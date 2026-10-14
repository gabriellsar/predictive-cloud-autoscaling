# TCC — Projeto Final I: protótipo v0

> Leia este arquivo inteiro e depois `docs/PLANO.md`. Se o seu agente usar `AGENTS.md`
> em vez de `CLAUDE.md`, copie este conteúdo para lá.

## Contexto

Trabalho de conclusão de Engenharia de Computação (PUC-Rio), etapa **Projeto Final I**.
O relatório é escrito em LaTeX no Overleaf, **fora deste repositório**. Este repositório
guarda só o protótipo, que serve como **evidência de viabilidade** para o relatório.

**Título:** Alocação preditiva de recursos em nuvem via previsão de carga com Redes
Neurais para minimização de custos operacionais.

**Pergunta central:** dado o histórico de utilização de um *cluster*, o quanto a qualidade
da previsão de carga reduz o custo de alocação (instâncias ativas) sem aumentar as violações
de SLA, comparando redes neurais com métodos tradicionais **sob a mesma política de decisão**?

Isso significa que a **política de alocação é fixa** e só o previsor muda. É isso que permite
atribuir diferenças de custo e de violações à qualidade da previsão.

## Objetivo desta semana (prazo: 21/10/2026)

Protótipo **v0 de ponta a ponta com previsores simples, sem rede neural**:

```
rastro do Alibaba → séries de 5 min → baselines de previsão → simulador de alocação
→ curva custo × violações → relato para o orientador
```

A rede neural (GRU/LSTM em PyTorch) é a semana seguinte. **Não a implemente agora**, mas
deixe a interface de previsores pronta para recebê-la (ver `docs/specs/02-baselines.md`).

## Como trabalhar

1. Siga `docs/PLANO.md` fase por fase, na ordem. Marque `[x]` nos checklists ao concluir.
2. Cada fase tem uma especificação em `docs/specs/`. Ela define o que entregar e o critério
   de aceite. Se discordar de uma decisão técnica, **proponha a alternativa e peça confirmação**
   em vez de mudar em silêncio.
3. Há **portões de revisão (G0 a G3)** no plano. Ao chegar em um, pare, resuma o que foi feito
   e espere o Gabriel aprovar antes de seguir.
4. Registre tudo em `docs/DIARIO.md`: data, o que foi feito, problemas encontrados e como foram
   contornados. Esse diário vira a seção "Revisão do Plano de Ação" do relatório, então
   seja concreto e inclua os problemas, não só os sucessos.
5. Commits pequenos e frequentes, uma mudança lógica por commit, mensagens em português ou inglês
   mas consistentes. Uma branch por fase (`fase-0-ambiente`, `fase-1-dados`, ...).

## Pare e pergunte quando

- o download dos dados exigir formulário, cadastro ou credencial;
- o esquema do arquivo real divergir do esperado nas specs;
- qualquer resultado parecer suspeito (por exemplo, o oráculo com violações > 0);
- uma etapa estourar o tempo reservado no plano (ver *time-box* de cada fase);
- for baixar algo grande (> 2 GB) ou instalar algo fora de `pyproject.toml`.

## Regras que não podem ser quebradas

- **Divisão cronológica** (treino → validação → teste), nunca aleatória.
- **Sem vazamento:** normalização, parâmetros e escolha de hiperparâmetros usam só treino
  (e validação). Uma previsão feita na origem `τ` só pode usar dados até `τ`.
- **Reprodutibilidade:** sementes fixas (`seed = 42` em `configs/v0.toml`), versões travadas
  em `uv.lock`, parâmetros em arquivo de configuração e nunca espalhados no código.
- **Dados nunca entram no Git** (`data/` no `.gitignore`). Tabelas e figuras pequenas de
  `results/` podem ser versionadas.
- **Não invente resultados.** Se algo não rodou, diga. Números no relato vêm de arquivos em
  `results/`.

## Idioma e estilo

- Código, nomes de funções e variáveis em **inglês**.
- Documentação, comentários explicativos, rótulos de gráficos e texto de relato em **português**.
- Python 3.12, `ruff` para formatação e *lint*, tipagem leve (type hints nas funções públicas).

## Notação (idêntica à do relatório; mantenha nos docstrings e nos gráficos)

| Símbolo | Significado |
|---|---|
| `t` | índice do intervalo (duração Δ = 5 min) |
| `d_t` | demanda no intervalo `t`, em unidades de capacidade |
| `k` | capacidade de uma instância |
| `n_t` | instâncias ativas no intervalo `t` |
| `c` | custo de uma instância por intervalo (usar `c = 1`) |
| `L` | *lead time*: intervalos entre a última observação e o intervalo em que a decisão vale (`L = 1 + atraso de inicialização`) |
| `h` | horizonte de previsão; na alocação, `h = L` |
| `m` | margem de segurança da política preditiva |
| `τ` | quantil (uso futuro, com perda quantílica) |
| `ε` | fração máxima tolerada de intervalos com violação |

**Métricas de alocação** (calculadas sobre os `T` intervalos de um *split*):

```
C       = Σ c · n_t                              custo total
V       = (1/T) Σ 1[ d_t > k·n_t ]               fração de intervalos com violação
U       = Σ max(0, d_t − k·n_t) / Σ d_t          fração da demanda não atendida
O       = Σ max(0, k·n_t − d_t) / Σ k·n_t        fração da capacidade ociosa
changes = Σ 1[ n_t ≠ n_{t−1} ]                   número de alterações em n_t
C_norm  = C / C_oracle                           custo relativo ao oráculo
```

**Métricas de previsão:** MAE, RMSE, MAPE (com máscara para `y` próximo de zero e informando
a cobertura da máscara) e **viés** (erro médio com sinal). O viés é importante: ele mostra se
o modelo tende a subestimar ou superestimar, e os dois erros têm custos diferentes na alocação.

## Estrutura do repositório

```
.
├── CLAUDE.md
├── pyproject.toml, uv.lock, .python-version
├── Dockerfile, docker-compose.yml, .dockerignore, .gitignore
├── Makefile
├── configs/v0.toml
├── data/            raw/ interim/ processed/    (fora do Git)
├── docs/            PLANO.md, DIARIO.md, RELATO.md, specs/
├── results/         tables/ figures/
├── scripts/         pontos de entrada finos (chamam src/)
├── src/tcc/         data/ forecast/ sim/ eval/
└── tests/
```
