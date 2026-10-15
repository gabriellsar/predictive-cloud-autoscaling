"""Agrega o rastro bruto em uma série regular de demanda.

Demanda, conforme a spec: em cada *bucket* de `interval_seconds`, calcula-se a utilização
média de cada máquina que reportou, depois a média entre essas máquinas, e finalmente

    d_t = (utilização média do cluster / 100) * N,

onde `N` é o número de máquinas distintas em todo o rastro. A unidade é "máquinas
equivalentes totalmente utilizadas".
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from tcc.config import load_config
from tcc.data.paths import connect, interim_path, processed_path, resolve

#: Esquema real do `machine_usage` do rastro Alibaba 2018 (arquivo sem cabeçalho).
RAW_COLUMNS: dict[str, str] = {
    "machine_id": "VARCHAR",
    "time_stamp": "BIGINT",
    "cpu_util_percent": "DOUBLE",
    "mem_util_percent": "DOUBLE",
    "mem_gps": "DOUBLE",
    "mkpi": "DOUBLE",
    "net_in": "DOUBLE",
    "net_out": "DOUBLE",
    "disk_io_percent": "DOUBLE",
}

#: Colunas finais do Parquet processado.
SERIES_COLUMNS = [
    "bucket_start",
    "demand_cpu",
    "demand_mem",
    "coverage",
    "n_machines_reporting",
    "filled",
]


def _columns_sql() -> str:
    inner = ", ".join(f"'{name}': '{dtype}'" for name, dtype in RAW_COLUMNS.items())
    return "{" + inner + "}"


def aggregate_per_machine(
    con: duckdb.DuckDBPyConnection,
    raw_path: Path,
    out_path: Path,
    interval: int,
) -> None:
    """Varre o CSV bruto uma única vez e grava uma linha por (máquina, *bucket*).

    Esta é a única etapa que lê o arquivo de 8,4 GB. Tudo o mais parte do intermediário.
    Valores de utilização nulos ou fora de [0, 100] são descartados na média e contados,
    sem descartar a linha inteira (uma CPU válida não é perdida por causa da memória).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT
                machine_id,
                (time_stamp // {interval})::BIGINT AS bucket,
                avg(CASE WHEN cpu_util_percent BETWEEN 0 AND 100
                         THEN cpu_util_percent END) AS cpu_util,
                avg(CASE WHEN mem_util_percent BETWEEN 0 AND 100
                         THEN mem_util_percent END) AS mem_util,
                count(*) AS n_samples,
                count(*) FILTER (
                    WHERE cpu_util_percent IS NULL
                       OR cpu_util_percent NOT BETWEEN 0 AND 100
                ) AS n_cpu_dropped,
                count(*) FILTER (
                    WHERE mem_util_percent IS NULL
                       OR mem_util_percent NOT BETWEEN 0 AND 100
                ) AS n_mem_dropped,
                min(time_stamp) AS t_min,
                max(time_stamp) AS t_max
            FROM read_csv(?, header = false, columns = {_columns_sql()})
            GROUP BY machine_id, bucket
        ) TO '{out_path}' (FORMAT parquet)
        """,
        [str(raw_path)],
    )


def _cluster_series(con: duckdb.DuckDBPyConnection, pmb_path: Path) -> tuple[pd.DataFrame, int]:
    """Média entre máquinas por *bucket* e o número total de máquinas do rastro."""
    n_machines = con.execute(
        f"SELECT count(DISTINCT machine_id) FROM read_parquet('{pmb_path}')"
    ).fetchone()[0]
    df = con.execute(
        f"""
        SELECT
            bucket,
            avg(cpu_util) AS cpu_util_mean,
            avg(mem_util) AS mem_util_mean,
            count(cpu_util) AS n_machines_reporting
        FROM read_parquet('{pmb_path}')
        GROUP BY bucket
        ORDER BY bucket
        """
    ).df()
    return df, int(n_machines)


def _to_regular_grid(
    df: pd.DataFrame,
    n_machines: int,
    interval: int,
    max_fill_gap: int,
    min_coverage: float = 0.0,
    trim_leading_missing: bool = False,
) -> pd.DataFrame:
    """Reindexa para a grade completa de *buckets*, converte para demanda e preenche lacunas.

    Só lacunas internas de até `max_fill_gap` intervalos são interpoladas linearmente; as
    maiores permanecem `NaN` e são sinalizadas no relatório de qualidade.

    `min_coverage` trata como lacuna todo *bucket* em que menos que essa fração das `N`
    máquinas reportou: com poucas máquinas, a média do cluster multiplicada por `N` é uma
    extrapolação ruidosa. `trim_leading_missing` descarta o trecho inicial que sobrar sem
    demanda válida. Os padrões (0.0 e falso) preservam a definição original da spec.
    """
    grid = pd.RangeIndex(0, int(df["bucket"].max()) + 1, name="bucket")
    df = df.set_index("bucket").reindex(grid)

    out = pd.DataFrame(index=grid)
    out["bucket_start"] = (grid * interval).astype("int64")
    out["demand_cpu"] = df["cpu_util_mean"] / 100.0 * n_machines
    out["demand_mem"] = df["mem_util_mean"] / 100.0 * n_machines
    out["n_machines_reporting"] = df["n_machines_reporting"].fillna(0).astype("int64")
    out["coverage"] = out["n_machines_reporting"] / n_machines

    # `interpolate(limit=max_fill_gap)` preencheria os primeiros `max_fill_gap` pontos de uma
    # lacuna longa, o que a spec proíbe. Por isso o preenchimento é decidido por lacuna:
    # só sequências contíguas de até `max_fill_gap` intervalos são interpoladas.
    if min_coverage > 0.0:
        unreliable = out["coverage"] < min_coverage
        out.loc[unreliable, ["demand_cpu", "demand_mem"]] = float("nan")

    missing = out["demand_cpu"].isna()
    run_id = (missing != missing.shift()).cumsum()
    run_length = missing.groupby(run_id).transform("size")
    fillable = missing & (run_length <= max_fill_gap)

    for col in ("demand_cpu", "demand_mem"):
        interpolated = out[col].interpolate(method="linear", limit_area="inside")
        out[col] = out[col].where(~fillable, interpolated)
    out["filled"] = fillable & out["demand_cpu"].notna()

    if trim_leading_missing:
        valid = out["demand_cpu"].notna()
        if valid.any():
            out = out.loc[valid.idxmax() :]

    return out.reset_index(drop=True)[SERIES_COLUMNS]


def build_series(
    raw_path: str | Path,
    out_path: str | Path,
    cfg: dict[str, Any],
    pmb_path: str | Path | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Agrega o rastro bruto e grava o Parquet da série. Devolve a série, por conveniência.

    `pmb_path` é o Parquet intermediário por (máquina, *bucket*). Se já existir e `force`
    for falso, ele é reaproveitado e o CSV bruto não é lido de novo.
    """
    data = cfg["data"]
    interval = int(data["interval_seconds"])
    raw_path, out_path = resolve(raw_path), resolve(out_path)
    pmb = resolve(pmb_path) if pmb_path is not None else interim_path(cfg)

    con = connect(cfg)
    try:
        if force or not pmb.exists():
            if not raw_path.exists():
                raise FileNotFoundError(f"rastro bruto não encontrado em {raw_path}")
            print(f"[dados] varrendo {raw_path} (uma única passagem)...", flush=True)
            aggregate_per_machine(con, raw_path, pmb, interval)
        else:
            print(f"[dados] reaproveitando o intermediário {pmb}", flush=True)

        raw, n_machines = _cluster_series(con, pmb)
    finally:
        con.close()

    series = _to_regular_grid(
        raw,
        n_machines,
        interval,
        int(data["max_fill_gap"]),
        float(data.get("min_coverage", 0.0)),
        bool(data.get("trim_leading_missing", False)),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    series.to_parquet(out_path, index=False)
    print(
        f"[dados] {len(series)} intervalos de {interval} s, N = {n_machines} máquinas"
        f" -> {out_path}",
        flush=True,
    )
    return series


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fase 1: constrói a série de demanda.")
    parser.add_argument("--config", default=None, help="caminho de um TOML alternativo")
    parser.add_argument(
        "--force",
        action="store_true",
        help="relê o CSV bruto mesmo que o intermediário já exista",
    )
    parser.add_argument("--skip-report", action="store_true", help="não gera relatório e figuras")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    build_series(cfg["data"]["raw_path"], processed_path(cfg), cfg, force=args.force)

    if not args.skip_report:
        from tcc.data.figures import make_figures
        from tcc.data.quality import write_quality_report

        write_quality_report(cfg)
        make_figures(cfg)


if __name__ == "__main__":
    main()
