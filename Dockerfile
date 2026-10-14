FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Camada de dependências (cache). O grupo dev (pytest, ruff) fica na imagem
# para que `docker compose run --rm app make test` funcione.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

COPY src ./src
COPY tests ./tests
COPY configs ./configs
COPY scripts ./scripts
COPY Makefile README.md ./
RUN uv sync --frozen

# O ambiente já está pronto e é somente leitura para o usuário não-root: `uv run` dentro do
# contêiner não deve tentar re-sincronizar o projeto (escreveria em /opt/venv e falharia).
ENV UV_NO_SYNC=1

RUN useradd -m app && mkdir -p data results && chown -R app:app /app
USER app

CMD ["make", "test"]
