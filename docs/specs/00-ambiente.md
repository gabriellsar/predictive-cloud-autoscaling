# Fase 0 — Ambiente (uv + Docker)

**Objetivo:** ambiente reproduzível, com o mesmo resultado rodando localmente com `uv` ou dentro
de um contêiner. **Time-box:** meio dia.

## 1. Projeto com uv

- Instalar o `uv` se necessário (https://docs.astral.sh/uv/).
- Criar o projeto no repositório existente com layout `src/` e pacote `tcc`
  (por exemplo `uv init --lib --name tcc` e ajustar), Python **3.12** (`.python-version`).
- Dependências organizadas por grupos:

| Grupo | Pacotes | Observação |
|---|---|---|
| padrão | `numpy`, `pandas`, `pyarrow`, `duckdb`, `scipy`, `statsmodels`, `matplotlib` | núcleo do v0 |
| `dev` | `pytest`, `ruff`, `ipykernel` | desenvolvimento |
| `nn` | `torch` | **declarar, mas não instalar nesta semana** |

- Para a semana seguinte, quando `torch` entrar, usar o índice CPU do PyTorch pelo mecanismo de
  índices do uv (`[[tool.uv.index]]` explícito + `[tool.uv.sources]`). Confirmar a sintaxe na
  documentação atual do uv antes de usar. Nesta semana, apenas deixe um comentário no `pyproject.toml`.
- Versionar `uv.lock`.
- Configurar `ruff` (linha de 100 colunas, regras padrão mais `I` para *imports*) no `pyproject.toml`.

## 2. Parâmetros em arquivo

Criar `configs/v0.toml` (lido com `tomllib`, da biblioteca padrão) com este conteúdo inicial. Nenhum
desses valores deve ficar fixo no código.

```toml
seed = 42

[data]
source = "alibaba2018"        # alibaba2018 | rossi_saved
interval_seconds = 300
split = { train = 0.6, val = 0.2, test = 0.2 }

[forecast]
horizons = [1, 2, 3, 6]       # horizontes avaliados nas métricas de previsão
ma_window = 6
season_period = 288           # 1 dia em intervalos de 5 min
arima_order = [2, 1, 2]

[sim]
n_peak = 50                   # instâncias necessárias no pico do treino (define k)
cost_per_instance = 1.0
lead_time = 1                 # L, em intervalos
n_min = 1
margins = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
hpa_targets = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
hpa_tolerance = 0.1
hpa_scale_down_window = 6     # intervalos
epsilons = [0.01, 0.05]       # SLO de violação para os pontos de operação
```

## 3. Makefile

Alvos (cada um chama `uv run ...`; dentro do Docker, o mesmo alvo funciona porque o ambiente já está ativo):

| Alvo | Faz |
|---|---|
| `setup` | `uv sync` |
| `lint` | `ruff check` e `ruff format --check` |
| `test` | `pytest -q` |
| `data` | roda a Fase 1 e gera o Parquet |
| `baselines` | roda a Fase 2 e gera `forecast_metrics.csv` |
| `sim` | roda as Fases 3 e 4 e gera tabelas e figuras |
| `all` | `data`, `baselines`, `sim` em sequência |
| `docker-build` | `docker compose build` |
| `docker-test` | `docker compose run --rm app make test` |

## 4. Docker

- **Imagem:** base oficial do uv para Python 3.12 (`ghcr.io/astral-sh/uv:python3.12-bookworm-slim`).
- **Camadas:** copiar `pyproject.toml` e `uv.lock` primeiro e rodar `uv sync --frozen --no-dev
  --no-install-project` (camada de dependências em cache); depois copiar `src/`, `configs/`,
  `scripts/`, `Makefile` e instalar o projeto.
- Variáveis úteis: `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy`.
- **Usuário não-root** dentro do contêiner.
- **`docker-compose.yml`:** serviço `app` com volumes `./data:/app/data`, `./results:/app/results`
  e `./configs:/app/configs:ro`. Um perfil `dev` pode montar também `./src` e `./tests`.
- **Dados nunca na imagem.** `.dockerignore` exclui `data/`, `results/`, `.git`, `.venv`, `__pycache__`.
- O grupo `dev` (pytest, ruff) precisa estar disponível para `docker compose run ... make test`;
  decida entre instalar `dev` na imagem ou ter um alvo de *build* separado, e documente.
- **Memória:** a agregação do rastro pode exceder o limite padrão do Docker Desktop. Se acontecer,
  rodar a Fase 1 nativamente (é a exceção prevista), configurar `memory_limit` e `temp_directory`
  do DuckDB e registrar no diário.

## 5. `.gitignore`

`data/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.parquet`, `*.csv` fora de
`results/tables/`, `.ipynb_checkpoints/`, `.env`. Manter `results/tables/*.csv` e `results/figures/*.png` versionáveis.

## 6. Testes de fumaça

Criar `tests/test_smoke.py` que importa `tcc`, lê `configs/v0.toml` e confere as chaves principais.

## Critérios de aceite (G0)

- [ ] `make setup && make lint && make test` passa em máquina limpa
- [ ] `docker compose build` e `docker compose run --rm app make test` passam
- [ ] `uv.lock` e `.python-version` versionados
- [ ] `torch` não está instalado
- [ ] `docs/DIARIO.md` iniciado, com as decisões de ambiente
