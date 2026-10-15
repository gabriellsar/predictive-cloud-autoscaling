"""Relatório de qualidade dos dados (Fase 1, seção 5 da spec).

Gera `results/tables/data_quality.csv` (métrica, valor, descrição) e
`results/data_quality.md` (leitura humana, em português). Todos os números saem dos
Parquet em `data/`, nunca de valores escritos à mão.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from tcc.data.paths import connect, interim_path, resolve
from tcc.data.series import load_series, split_series


def _gap_runs(no_data: pd.Series) -> list[tuple[int, int]]:
    """Sequências contíguas de *buckets* sem dado, como (início, comprimento)."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for t, missing in enumerate(no_data):
        if missing and start is None:
            start = t
        elif not missing and start is not None:
            runs.append((start, t - start))
            start = None
    if start is not None:
        runs.append((start, len(no_data) - start))
    return runs


def collect_metrics(cfg: dict[str, Any]) -> pd.DataFrame:
    """Reúne as métricas de qualidade a partir do intermediário e da série processada."""
    data = cfg["data"]
    interval = int(data["interval_seconds"])
    max_fill_gap = int(data["max_fill_gap"])
    pmb = interim_path(cfg)
    series = load_series(cfg)

    con = connect(cfg)
    try:
        totals = (
            con.execute(
                f"""
            SELECT
                count(DISTINCT machine_id) AS n_machines,
                sum(n_samples) AS n_rows,
                sum(n_cpu_dropped) AS n_cpu_dropped,
                sum(n_mem_dropped) AS n_mem_dropped,
                median(n_samples) AS median_samples_per_bucket,
                quantile_cont(n_samples, 0.05) AS p05_samples_per_bucket,
                quantile_cont(n_samples, 0.95) AS p95_samples_per_bucket
            FROM read_parquet('{pmb}')
            """
            )
            .df()
            .iloc[0]
        )
        per_machine = (
            con.execute(
                f"""
            SELECT
                min(first_bucket) AS min_first_bucket,
                max(first_bucket) AS max_first_bucket,
                median(first_bucket) AS median_first_bucket,
                min(last_bucket) AS min_last_bucket,
                max(last_bucket) AS max_last_bucket,
                median(last_bucket) AS median_last_bucket,
                count(*) FILTER (WHERE first_bucket = 0) AS n_starting_at_zero,
                median(n_buckets) AS median_buckets_per_machine
            FROM (
                SELECT machine_id,
                       min(bucket) AS first_bucket,
                       max(bucket) AS last_bucket,
                       count(*) AS n_buckets
                FROM read_parquet('{pmb}')
                GROUP BY machine_id
            )
            """
            )
            .df()
            .iloc[0]
        )
    finally:
        con.close()

    n_machines = int(totals["n_machines"])
    n_rows = int(totals["n_rows"])
    t = len(series)
    no_data = series["n_machines_reporting"] == 0
    runs = _gap_runs(no_data)
    big_runs = [r for r in runs if r[1] > max_fill_gap]
    splits = split_series(series, cfg)

    rows: list[tuple[str, Any, str]] = [
        ("source", data["source"], "fonte dos dados"),
        ("n_rows_raw", n_rows, "linhas lidas do CSV bruto"),
        ("n_machines", n_machines, "máquinas distintas no rastro (N da definição de demanda)"),
        ("n_intervals", t, f"intervalos de {interval} s na série final"),
        ("interval_seconds", interval, "duração de um intervalo (Δ)"),
        ("duration_days", round(t * interval / 86400, 3), "duração total coberta"),
        (
            "sampling_seconds_median",
            round(interval / float(totals["median_samples_per_bucket"]), 1),
            "intervalo original de amostragem, estimado pela mediana de amostras por bucket",
        ),
        (
            "samples_per_bucket_p05_p95",
            f"{totals['p05_samples_per_bucket']:.0f}-{totals['p95_samples_per_bucket']:.0f}",
            "amostras por (máquina, bucket): p05 a p95, mostra a amostragem irregular",
        ),
        (
            "n_cpu_dropped",
            int(totals["n_cpu_dropped"]),
            "amostras de CPU nulas ou fora de [0, 100] ignoradas na média",
        ),
        (
            "frac_cpu_dropped",
            float(totals["n_cpu_dropped"]) / n_rows,
            "fração das linhas com CPU descartada",
        ),
        (
            "n_mem_dropped",
            int(totals["n_mem_dropped"]),
            "amostras de memória nulas ou fora de [0, 100] ignoradas na média",
        ),
        (
            "frac_buckets_coverage_below_1",
            float((series["coverage"] < 1.0).mean()),
            "fração de intervalos em que não todas as N máquinas reportaram",
        ),
        ("coverage_min", float(series["coverage"].min()), "cobertura mínima entre os intervalos"),
        (
            "coverage_median",
            float(series["coverage"].median()),
            "cobertura mediana entre os intervalos",
        ),
        ("n_buckets_no_data", int(no_data.sum()), "intervalos sem nenhuma amostra"),
        (
            "n_buckets_filled",
            int(series["filled"].sum()),
            "intervalos preenchidos por interpolação",
        ),
        (
            "n_gaps_above_max_fill",
            len(big_runs),
            f"lacunas contíguas maiores que max_fill_gap = {max_fill_gap} (ficaram NaN)",
        ),
        (
            "gaps_above_max_fill_detail",
            "; ".join(f"t={s} ({n} intervalos)" for s, n in big_runs) or "nenhuma",
            "posição e tamanho das lacunas não preenchidas",
        ),
        ("n_nan_demand_cpu", int(series["demand_cpu"].isna().sum()), "NaN restantes em demand_cpu"),
        (
            "n_machines_starting_at_bucket_0",
            int(per_machine["n_starting_at_zero"]),
            "máquinas cujo primeiro bucket é 0 (origem comum dos time_stamp)",
        ),
        (
            "machine_first_bucket_min_median_max",
            f"{per_machine['min_first_bucket']:.0f}/"
            f"{per_machine['median_first_bucket']:.0f}/"
            f"{per_machine['max_first_bucket']:.0f}",
            "primeiro bucket por máquina: mín./mediana/máx.",
        ),
        (
            "machine_last_bucket_min_median_max",
            f"{per_machine['min_last_bucket']:.0f}/"
            f"{per_machine['median_last_bucket']:.0f}/"
            f"{per_machine['max_last_bucket']:.0f}",
            "último bucket por máquina: mín./mediana/máx.",
        ),
        (
            "median_buckets_per_machine",
            float(per_machine["median_buckets_per_machine"]),
            "mediana de buckets com dado por máquina (de n_intervals possíveis)",
        ),
        (
            "split_sizes",
            "/".join(str(len(series[sl])) for sl in splits.values()),
            "tamanho de treino/validação/teste (divisão cronológica)",
        ),
    ]

    for col in ("demand_cpu", "demand_mem"):
        s = series[col].dropna()
        unit = "máquinas equivalentes"
        rows += [
            (f"{col}_min", round(float(s.min()), 3), f"mínimo de {col} ({unit})"),
            (f"{col}_mean", round(float(s.mean()), 3), f"média de {col} ({unit})"),
            (f"{col}_median", round(float(s.median()), 3), f"mediana de {col} ({unit})"),
            (f"{col}_p95", round(float(s.quantile(0.95)), 3), f"p95 de {col} ({unit})"),
            (f"{col}_max", round(float(s.max()), 3), f"máximo de {col} ({unit})"),
        ]

    return pd.DataFrame(rows, columns=["metric", "value", "description"])


def write_quality_report(cfg: dict[str, Any]) -> Path:
    """Escreve a tabela e o relatório em Markdown. Devolve o caminho do Markdown."""
    metrics = collect_metrics(cfg)
    tables_dir = resolve("results/tables")
    tables_dir.mkdir(parents=True, exist_ok=True)
    csv_path = tables_dir / "data_quality.csv"
    metrics.to_csv(csv_path, index=False)

    def value(metric: str) -> Any:
        return metrics.loc[metrics["metric"] == metric, "value"].iloc[0]

    md_path = resolve("results") / "data_quality.md"
    lines = [
        "# Relatório de qualidade dos dados",
        "",
        f"Fonte: **{value('source')}** · agregação em intervalos de "
        f"**{value('interval_seconds')} s** · gerado por `make data`.",
        "",
        "## Resumo",
        "",
        f"- {value('n_rows_raw'):,} linhas brutas, {value('n_machines'):,} máquinas distintas "
        f"(**N = {value('n_machines')}** na definição de demanda).",
        f"- {value('n_intervals'):,} intervalos, cobrindo {value('duration_days')} dias.",
        f"- Amostragem original estimada em ~{value('sampling_seconds_median')} s por máquina "
        f"(amostras por intervalo, p05–p95: {value('samples_per_bucket_p05_p95')}), "
        "confirmando que a amostragem é irregular.",
        f"- Divisão cronológica treino/validação/teste: {value('split_sizes')} intervalos.",
        "",
        "## Cobertura e lacunas",
        "",
        f"- Cobertura mediana: {float(value('coverage_median')):.4f}; "
        f"mínima: {float(value('coverage_min')):.4f}.",
        f"- Intervalos com cobertura < 100%: "
        f"{float(value('frac_buckets_coverage_below_1')):.4f} do total.",
        f"- Intervalos sem nenhuma amostra: {value('n_buckets_no_data')}; "
        f"preenchidos por interpolação: {value('n_buckets_filled')}.",
        f"- Lacunas maiores que `max_fill_gap`: {value('n_gaps_above_max_fill')} "
        f"({value('gaps_above_max_fill_detail')}).",
        f"- Mediana de intervalos com dado por máquina: "
        f"{value('median_buckets_per_machine')} de {value('n_intervals')}.",
        f"- Máquinas cujo primeiro intervalo é 0: {value('n_machines_starting_at_bucket_0')} "
        f"de {value('n_machines')}; primeiro intervalo por máquina (mín./mediana/máx.): "
        f"{value('machine_first_bucket_min_median_max')}; último: "
        f"{value('machine_last_bucket_min_median_max')}. Isso responde se os `time_stamp` "
        "compartilham a mesma origem.",
        f"- `NaN` restantes em `demand_cpu`: {value('n_nan_demand_cpu')}.",
        "",
        "## Amostras descartadas",
        "",
        f"- CPU nula ou fora de [0, 100]: {value('n_cpu_dropped')} amostras "
        f"({float(value('frac_cpu_dropped')):.2e} das linhas).",
        f"- Memória nula ou fora de [0, 100]: {value('n_mem_dropped')} amostras.",
        "",
        "## Demanda (em máquinas equivalentes totalmente utilizadas)",
        "",
        "| Série | mín. | média | mediana | p95 | máx. |",
        "|---|---|---|---|---|---|",
    ]
    for col in ("demand_cpu", "demand_mem"):
        lines.append(
            f"| `{col}` | {value(f'{col}_min')} | {value(f'{col}_mean')} | "
            f"{value(f'{col}_median')} | {value(f'{col}_p95')} | {value(f'{col}_max')} |"
        )
    lines += [
        "",
        "## Limitações",
        "",
        "- **Demanda censurada:** a utilização por máquina tem teto de 100%, então em momentos",
        "  de saturação a demanda observada subestima a demanda real.",
        "- A série cobre ~8 dias, o que deixa o conjunto de teste pequeno (limitação aceita",
        "  no v0).",
        "",
        "Tabela completa em `results/tables/data_quality.csv`.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
