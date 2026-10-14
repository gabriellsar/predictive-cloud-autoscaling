# Fase 1 — Dados

**Objetivo:** transformar o rastro bruto em uma série temporal regular de demanda (CPU) e de
memória, a cada 5 minutos, com divisão cronológica e um relatório de qualidade.
**Time-box:** 1,5 dia.

## 1. Fonte

**Plano A — Alibaba Cluster Trace 2018** (`https://github.com/alibaba/clusterdata`, pasta
`cluster-trace-v2018`). Cobre cerca de 4.000 máquinas em 8 dias. Interessa a tabela
`machine_usage` (uso de recursos por máquina).

Atenção a duas incertezas que precisam ser **confirmadas pelo agente**, não assumidas:

1. **Como obter os arquivos.** Os links de download do rastro podem exigir o preenchimento de um
   formulário. Se for o caso, **pare e avise o Gabriel**. Não tente contornar.
2. **Esquema real.** As colunas esperadas do `machine_usage` são provavelmente `machine_id`,
   `time_stamp`, `cpu_util_percent`, `mem_util_percent` e outras de rede e disco. Confirme
   no `trace_2018.md` do repositório e no cabeçalho real do arquivo. Verifique também se o arquivo
   tem linha de cabeçalho, o intervalo original de amostragem e a unidade de `time_stamp`.

**Plano B (fallback)** — dados pré-processados do repositório
`https://github.com/andreareds/TowardsUncertaintyAwareWorkloadPrediction`, pasta `saved_data/`
(Google e Alibaba). Formato e granularidade são desconhecidos até abrir. Se usar o plano B,
documente no diário o formato, a granularidade e a licença, e ajuste a Seção 2 conforme o que
existir. A interface `load_series()` deve esconder a diferença entre as fontes.

Os dados brutos ficam em `data/raw/` (fora do Git). Registre a origem e a data de download em
`data/README.md` (este arquivo pode ser versionado).

## 2. Definição de demanda

Máquinas podem não reportar em todos os intervalos, então somar a utilização das máquinas
presentes subestimaria a demanda nos intervalos com lacunas. Por isso:

1. Dividir `time_stamp` em *buckets* de `interval_seconds` (300 s).
2. Em cada *bucket*, calcular a **utilização média por máquina** (média das amostras de cada
   máquina no *bucket*) e depois a **média entre as máquinas que reportaram**.
3. `demand_cpu = (utilização média do cluster / 100) × N`, onde `N` é o número total de máquinas
   distintas no rastro. A unidade é "máquinas equivalentes totalmente utilizadas".
4. Fazer o mesmo para memória (`demand_mem`), por completude.
5. Registrar, por *bucket*, a fração de máquinas que reportaram (`coverage`).

**Preencher lacunas:** *buckets* sem nenhum dado ficam como lacuna; interpolar linearmente só
lacunas de até 3 intervalos e registrar quantas foram preenchidas. Lacunas maiores devem ser
sinalizadas no relatório (e o Gabriel decide o que fazer).

**Limitação a registrar no diário:** a utilização tem teto de 100% por máquina, então em
momentos de saturação a demanda observada pode **subestimar** a demanda real (demanda censurada).

## 3. Agregação com DuckDB

- Ler o CSV com `read_csv` e **tipos e nomes de coluna explícitos** (sem inferência), em modo de
  leitura em fluxo, sem carregar tudo em memória.
- Fazer a agregação em SQL e **uma única vez**, salvando o resultado em
  `data/processed/<source>_<interval>s.parquet`. A partir daí, nada relê o arquivo bruto.
- Colunas do Parquet: `bucket_start` (inteiro, segundos desde o início do rastro), `demand_cpu`,
  `demand_mem`, `coverage`, `n_machines_reporting`, `filled` (booleano).

## 4. API em `src/tcc/data/`

```python
def build_series(raw_path, out_path, cfg) -> None: ...  # agrega e grava o Parquet
def load_series(cfg) -> pd.DataFrame: ...  # índice 0..T-1, colunas padronizadas
def split_series(df, cfg) -> dict[str, slice]: ...  # {"train", "val", "test"} por posição
```

`split_series` usa as frações de `configs/v0.toml` e retorna **fatias por posição**, em ordem
cronológica. O restante do código usa as fatias para indexar a série completa, de modo que um
previsor no início de `val` ou `test` pode olhar o passado (nunca o futuro).

## 5. Relatório de qualidade

Gerar `results/tables/data_quality.csv` e `results/data_quality.md` com:
número de máquinas, número de intervalos, duração total, intervalo original de amostragem,
fração de *buckets* com cobertura < 100%, cobertura mínima, intervalos preenchidos, lacunas
maiores que 3 intervalos, e estatísticas de `demand_cpu` e `demand_mem` (mín., média, mediana, p95, máx.).

## 6. Figuras (`results/figures/`)

1. `series_full.png` — `demand_cpu` ao longo de todo o período, com as três divisões marcadas.
2. `series_day.png` — um dia ampliado, para ver a variação intradiária.
3. `acf_cpu.png` — autocorrelação até 2 dias de *lags*, com marcação do período de 288 intervalos.
4. `cpu_vs_mem.png` — dispersão simples entre `demand_cpu` e `demand_mem` (justifica o uso, ou
   não, de entrada multivariada na semana seguinte).

Rótulos e títulos em português, eixos com unidade.

## 7. Testes (`tests/test_data.py`)

- Com um CSV sintético pequeno, `build_series` produz *buckets* corretos (conferir a média à mão).
- O Parquet tem índice de tempo estritamente crescente e espaçamento constante.
- `split_series` devolve fatias que não se sobrepõem, cobrem a série e respeitam a ordem.
- Sem `NaN` após o preenchimento, exceto nas lacunas grandes sinalizadas.

## Critérios de aceite (G1)

- [ ] Parquet gerado e `load_series()` funcionando
- [ ] relatório de qualidade e as 4 figuras geradas
- [ ] testes passando
- [ ] diário registra: origem dos dados, esquema real, problemas e limitações (demanda censurada)
- [ ] o Gabriel aprovou a definição de demanda ao olhar as figuras
