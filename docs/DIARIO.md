# Diário

## 14/10/2026 — Fase 0 (ambiente)

**Feito**

- Esqueleto criado com `bootstrap.sh`: projeto `uv` com layout `src/` (pacote `tcc`), Python 3.12
  (`.python-version`), `Makefile`, `Dockerfile`, `docker-compose.yml`, `configs/v0.toml`.
- Dependências por grupos no `pyproject.toml`: padrão (`numpy`, `pandas`, `pyarrow`, `duckdb`,
  `scipy`, `statsmodels`, `matplotlib`), `dev` (`pytest`, `ruff`, `ipykernel`) e `nn` (`torch`).
- `uv.lock` versionado; `ruff` configurado (100 colunas, regras `E`, `F`, `I`).
- `data/interim/` criado (faltava na estrutura) e `.gitignore` ajustado: ignora `*.csv` exceto
  em `results/tables/`, além de `data/`, caches e `*.parquet`.
- Perfil `dev` no `docker-compose.yml`, que monta `src/` e `tests/` para iterar sem reconstruir
  a imagem (`docker compose run --rm dev make test`).
- Teste de fumaça: importa `tcc`, lê `configs/v0.toml` e confere as chaves principais.

**Decisões de ambiente**

- **Grupo `nn` declarado e travado, mas não instalado.** `uv sync` instala só o grupo padrão e o
  `dev`; `torch` só entra com `uv sync --group nn`. Verificado que `import torch` falha tanto no
  ambiente local quanto no contêiner. *Efeito colateral a resolver na semana seguinte:* como ainda
  não configuramos o índice CPU do PyTorch, o `uv.lock` resolveu `torch 2.14.1` com as *wheels*
  CUDA (os pacotes `nvidia-*`). Isso não ocupa espaço porque nada disso é instalado, mas quando o
  índice CPU entrar (`[[tool.uv.index]]` + `[tool.uv.sources]`) o *lock* será re-resolvido.
- **Grupo `dev` dentro da imagem Docker** (em vez de um estágio de *build* separado), porque o
  critério de aceite exige `docker compose run --rm app make test`, e `pytest`/`ruff` vivem nesse
  grupo. A imagem é de desenvolvimento, não de produção; o custo em tamanho é aceitável.
- **Usuário não-root (`app`) e ambiente em `/opt/venv`**, fora de `/app`, para que os volumes
  montados não escondam o ambiente.
- Dados nunca entram na imagem: `.dockerignore` exclui `data/`, `results/`, `.git`, `.venv` e caches.

**Problemas encontrados e como foram contornados**

1. **`ruff format --check` reescrevia as especificações.** O `ruff` 0.17 também formata blocos de
   código Python dentro de Markdown, e por isso o `make lint` falhava apontando
   `docs/specs/01-dados.md` (comentários alinhados à mão nas assinaturas de função).
   *Solução:* `extend-exclude = ["docs"]` no `[tool.ruff]`. O formatador cuida de código em
   `src/`, `tests/` e `scripts/`; a documentação fica como escrita.
2. **`make test` falhava dentro do contêiner:** `uv run` revalidava o projeto e tentava reinstalá-lo,
   escrevendo em `/opt/venv`, ao qual o usuário não-root não tem acesso
   (`failed to remove file /opt/venv/.../_editable_impl_tcc.pth: Permission denied`).
   *Solução:* `ENV UV_NO_SYNC=1` na imagem, depois dos `uv sync` de *build*. O mesmo alvo do
   `Makefile` passa a funcionar nos dois lugares, que era a intenção da spec. A alternativa
   (`chown` do ambiente para `app`) foi descartada para manter o ambiente imutável em execução.
   A variável foi colocada depois das camadas de dependência para não invalidar o *cache*.
3. **`load_config` dependia do diretório de trabalho** (`Path("configs/v0.toml")`), o que quebraria
   qualquer execução fora da raiz do repositório. *Solução:* o caminho padrão é resolvido a partir
   da raiz do projeto, com recurso ao diretório atual (cobre instalação não-editável no contêiner),
   e há um teste que carrega a configuração de dentro de um diretório temporário.

**Verificação (G0)**

- Local: `make setup`, `make lint` e `make test` passam (3 testes).
- Docker: `docker compose build`, `docker compose run --rm app make test` e
  `docker compose run --rm app make lint` passam; o perfil `dev` também.
- `uv.lock` e `.python-version` versionados; `torch` ausente dos dois ambientes.
