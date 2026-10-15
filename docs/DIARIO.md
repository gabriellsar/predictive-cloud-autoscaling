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

## 15/10/2026 — Fase 1 (dados)

**Feito**

- Agregação do `machine_usage` (8,4 GB, 246.934.820 linhas) em uma **única passagem** com DuckDB,
  gravando um intermediário por (máquina, *bucket*) em `data/interim/` (70 MB). Tudo o mais parte
  desse intermediário; o CSV bruto não é lido de novo (16 s de varredura com 8 *threads*).
- Série final em `data/processed/alibaba2018_300s.parquet`: **2.304 intervalos de 5 min**,
  **N = 4.023 máquinas** — exatamente o que a spec previa.
- `load_series()` e `split_series()` com divisão cronológica 60/20/20 (1382/460/462 intervalos).
- Relatório de qualidade (`results/data_quality.md` e `results/tables/data_quality.csv`) e as
  quatro figuras de `results/figures/`.
- 15 testes, incluindo a agregação conferida à mão sobre um CSV sintético.

**Confirmações sobre os dados**

- Esquema real bate com o registrado na spec: 9 colunas, sem cabeçalho, `mem_gps` e `mkpi` vazias.
  A contagem de linhas deu 246.934.820, contra 246.934.800 do perfil anterior (20 linhas de
  diferença; não investiguei, é irrelevante na escala do rastro).
- **Amostragem original ~10 s** por máquina (p05–p95 de 29 a 30 amostras por intervalo de 300 s),
  ou seja, na ponta baixa da faixa de 10 a 30 s que a spec estimava. Irregular, como esperado.
- **Origem dos `time_stamp` é comum** (pergunta 2 da spec): 2.348 das 4.023 máquinas começam no
  *bucket* 0, a mediana do primeiro *bucket* é 0 e a do último é 2.303. O que varia é o tempo de
  vida de cada máquina: algumas entram no rastro depois (último primeiro *bucket*: 2.067) e outras
  saem antes (primeiro último *bucket*: 190).
- **Cobertura por *bucket*** (pergunta 1 da spec) tem três regimes nítidos:
  - `t = 0..472` (1,64 dia inicial): cobertura média de **0,68** — só dois terços das máquinas
    reportam. A demanda aí é a média de ~2.700 máquinas extrapolada para 4.023.
  - `t = 473..533`: **apagão de coleta de 61 intervalos (5 h 05)**, sem nenhuma amostra. Confirmado
    no bruto: o número de máquinas cai de 750 (t=470) para 344, depois 8, e some.
  - `t = 535..2303` (6,14 dias): cobertura mínima de 0,978 e mediana de 0,998.

**Problemas encontrados e como foram contornados**

1. **Bug no preenchimento de lacunas.** `Series.interpolate(limit=3)` do pandas preenche os três
   *primeiros* pontos de *qualquer* lacuna, inclusive uma de 61 intervalos — o oposto do que a
   spec pede. Descoberto porque o relatório acusou 3 intervalos preenchidos com uma única lacuna
   de 61. Corrigido decidindo o preenchimento **por lacuna inteira**: mede-se o comprimento de
   cada sequência contígua e só as de até `max_fill_gap` são interpoladas. Há teste para os dois
   casos (lacuna de 1 interpolada, lacuna de 4 preservada).
2. **Apagão de 5 h dentro do treino.** Fica como `NaN` e está sinalizado no relatório, como a spec
   manda. Consequência para a Fase 2: ou os previsores lidam com `NaN` no treino, ou a série passa
   a começar depois do apagão. Levado ao G1.
3. **Cabeça do rastro com cobertura de 68%.** Não é lacuna, mas a demanda nesse trecho é uma
   extrapolação a partir de uma amostra incompleta e possivelmente enviesada (demanda média de
   1.442 na cabeça contra 1.552 na cauda, −7%). Implementei a regra como **parâmetros de
   configuração** (`min_coverage` e `trim_leading_missing`), com padrão que **não muda** a
   definição original, e levei a escolha ao G1 com os números das duas variantes.
4. A autocorrelação e a correlação CPU × memória são calculadas **só no treino**: elas embasam
   escolhas de modelagem (período sazonal, entrada multivariada) e cairiam na regra de vazamento
   se olhassem validação ou teste.

**O que as figuras mostram**

- Sazonalidade diária forte e um pico diário estreito: a ACF no treino tem máximo local de 0,51
  em 288 intervalos e repete em 576, confirmando `season_period = 288`.
- A demanda de memória é quase plana e alta (média de 3.541 de 4.023 máquinas equivalentes), com
  correlação fraca com a CPU (Pearson r = 0,205 no treino). Isso é argumento **contra** entrada
  multivariada automática na semana seguinte.

**Limitações registradas**

- **Demanda censurada:** a utilização por máquina tem teto de 100%, então em saturação a demanda
  observada subestima a real.
- Série de ~8 dias (ou 6,1, conforme a decisão do G1): o teste fica pequeno. Aceito no v0.
