# Trabalho de conclusão de curso Engenharia de Computação (PUC-Rio) 

### Título: Alocação preditiva de recursos em nuvem via previsão de carga com Redes Neurais para minimização de custos operacionais

- Orientador: Adriano Francisco Branco
- Coorientador: Jonatas dos Santos Grosman

### O que é

Um provedor de nuvem precisa decidir, a cada poucos minutos, quantas instâncias manter ativas.
Instâncias demais custam caro; de menos, violam o acordo de nível de serviço (SLA). A alocação
reativa só ajusta depois de ver a demanda mudar, e por isso chega atrasada nos picos. A
alternativa é prever a demanda e provisionar antes.

A pergunta do trabalho é **o quanto a qualidade da previsão de carga reduz o custo de alocação
sem aumentar as violações de SLA**, comparando redes neurais com métodos tradicionais. Para que as
diferenças possam ser atribuídas à previsão, **a política de alocação é fixa e só o previsor
muda**. 

A motivação e a revisão da literatura estão no relatório, em
[`lib/report/main.pdf`](lib/report/main.pdf)

### Instalação

Requisitos: [`uv`](https://docs.astral.sh/uv/), `make` e, opcionalmente, Docker.

```bash
git clone https://github.com/gabriellsar/predictive-cloud-autoscaling.git
cd predictive-cloud-autoscaling
make setup      # uv sync: dependências do projeto e de desenvolvimento
uv sync --group nn  # opcional: PyTorch (só CPU) para a GRU
make test       # testes
bash scripts/download_alibaba.sh # baixa machine_usage ~1,7GB compactado
```

O grupo `nn` instala o PyTorch do índice só para CPU (configurado no `pyproject.toml`, ~0,7 GB).
Sem ele, tudo roda e a GRU é omitida com um aviso. Atenção: `make setup` (`uv sync`) remove
pacotes fora dos grupos padrão, inclusive o `torch`; depois dele, rode de novo
`uv sync --group nn`.
### Como rodar

```bash
make all        # data → baselines → sim: reproduz todo o results/ a partir de data/raw/
```

Cada etapa também roda separadamente:

| Alvo | O que faz | Gera |
|---|---|---|
| `make data` | Agrega o rastro bruto em uma série de 5 min e gera o relatório de qualidade | `data/processed/`, `results/data_quality.md` |
| `make baselines` | Avalia os previsores: naive, média móvel, sazonal ingênuo, Holt-Winters, ARIMA e GRU (com o grupo `nn`) | `results/tables/forecast_metrics.csv` |
| `make sim` | Simula as políticas, escolhe os pontos de operação e gera as figuras | `results/tables/allocation_metrics.csv`, `results/figures/pareto_cost_violation.png` |
| `make lint` | `ruff check` e `ruff format --check` | — |

A lista completa de arquivos de `results/`, com o comando que gera cada um, está em
[`results/README.md`](results/README.md). Todos os parâmetros (divisão, horizontes, `n_peak`,
`L`, grades de `m` e `u*`, SLOs `ε`) ficam em [`configs/v0.toml`](configs/v0.toml), e nenhum
fica fixo no código. Os hiperparâmetros da GRU estão em `[forecast.nn]`; com 1 *thread* de CPU, o
treino leva cerca de 25 s e roda duas vezes em `make all` (uma em `baselines`, outra em `sim`).
