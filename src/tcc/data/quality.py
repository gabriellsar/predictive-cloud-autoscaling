"""Relatório de qualidade dos dados (Fase 1, seção 5 da spec).

Gera `results/tables/data_quality.csv` (métrica, valor, descrição) e
`results/data_quality.md` (leitura humana, em português). Todos os números saem dos
Parquet em `data/`, nunca de valores escritos à mão.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from tcc.data.build import gap_runs, long_filled_runs
from tcc.data.paths import connect, interim_path, resolve
from tcc.data.series import load_series, split_series

SPLIT_LABELS = {"train": "no treino", "val": "na validação", "test": "no teste"}


def _pt(value: Any) -> str:
    """Formata um número no padrão português: milhar com ponto, decimal com vírgula."""
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, (int,)) or (hasattr(value, "is_integer") and float(value).is_integer()):
        text = f"{int(value):,}"
    elif isinstance(value, float):
        text = f"{value:,.4f}".rstrip("0").rstrip(".")
    else:
        return str(value)
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


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
                median(n_buckets) AS median_buckets_per_machine,
                max(last_bucket) + 1 AS n_buckets_trace
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
    low_coverage = ~no_data & (series["coverage"] < float(data["min_coverage"]))
    # Lacuna é todo intervalo sem demanda própria: sem dado, abaixo de `min_coverage` ou
    # preenchido. Os preenchidos continuam contando como lacuna, só que tratada.
    gap = series["filled"] | series["demand_cpu"].isna()
    big_runs = [r for r in gap_runs(gap) if r[1] > max_fill_gap]
    seasonal_runs = set(long_filled_runs(series, max_fill_gap))
    n_seasonal = sum(length for _, length in seasonal_runs)
    observed = series[~gap]
    splits = split_series(series, cfg)

    rows: list[tuple[str, Any, str]] = [
        ("source", data["source"], "fonte dos dados"),
        ("min_coverage", data["min_coverage"], "cobertura mínima para o intervalo valer"),
        (
            "long_gap_fill",
            data.get("long_gap_fill", "none"),
            "tratamento das lacunas maiores que max_fill_gap",
        ),
        (
            "trim_leading_missing",
            data["trim_leading_missing"],
            "descarta o trecho inicial sem demanda válida",
        ),
        ("first_bucket_start", int(series["bucket_start"].iloc[0]), "início da série, em segundos"),
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
        (
            "coverage_min",
            float(observed["coverage"].min()),
            "cobertura mínima entre os intervalos observados (não preenchidos)",
        ),
        (
            "coverage_median",
            float(observed["coverage"].median()),
            "cobertura mediana entre os intervalos observados (não preenchidos)",
        ),
    ]
    for name, sl in splits.items():
        coverage = observed.loc[observed.index.isin(range(sl.start, sl.stop)), "coverage"]
        rows.append(
            (
                f"coverage_{name}_min_median_mean",
                f"{coverage.min():.4f}/{coverage.median():.4f}/{coverage.mean():.4f}",
                f"cobertura {SPLIT_LABELS[name]}, só intervalos observados: mín./mediana/média",
            )
        )
    rows += [
        ("n_buckets_no_data", int(no_data.sum()), "intervalos sem nenhuma amostra"),
        (
            "n_buckets_low_coverage",
            int(low_coverage.sum()),
            "intervalos com amostras, mas cobertura abaixo de min_coverage (viram lacuna)",
        ),
        (
            "n_buckets_filled",
            int(series["filled"].sum()),
            "intervalos preenchidos (interpolação linear ou preenchimento sazonal)",
        ),
        (
            "n_buckets_filled_seasonal",
            n_seasonal,
            "intervalos preenchidos pelo método sazonal (lacunas longas)",
        ),
        (
            "n_gaps_above_max_fill",
            len(big_runs),
            f"lacunas contíguas maiores que max_fill_gap = {max_fill_gap}",
        ),
        (
            "gaps_above_max_fill_detail",
            "; ".join(
                f"t={s}..{s + n - 1} ({n} intervalos, "
                f"{'preenchida' if (s, n) in seasonal_runs else 'NaN'})"
                for s, n in big_runs
            )
            or "nenhuma",
            "posição, tamanho e tratamento das lacunas longas",
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
            "n_buckets_trace",
            int(per_machine["n_buckets_trace"]),
            "buckets do rastro completo, antes de qualquer corte",
        ),
        (
            "median_buckets_per_machine",
            float(per_machine["median_buckets_per_machine"]),
            "mediana de buckets com dado por máquina, no rastro completo",
        ),
        (
            "split_sizes",
            "/".join(str(len(series[sl])) for sl in splits.values()),
            "tamanho de treino/validação/teste (divisão cronológica)",
        ),
    ]

    # Estatísticas descritivas só dos intervalos observados: os preenchidos são estimativas.
    for col in ("demand_cpu", "demand_mem"):
        s = observed[col].dropna()
        unit = "máquinas equivalentes, intervalos observados"
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
        f"- {_pt(value('n_rows_raw'))} linhas brutas, {_pt(value('n_machines'))} máquinas "
        f"distintas (**N = {value('n_machines')}** na definição de demanda).",
        f"- {_pt(value('n_intervals'))} intervalos, cobrindo "
        f"{_pt(value('duration_days'))} dias, a partir de "
        f"t = {_pt(value('first_bucket_start'))} s do rastro.",
        f"- Amostragem original estimada em ~{_pt(value('sampling_seconds_median'))} s por máquina "
        f"(amostras por intervalo, p05–p95: {value('samples_per_bucket_p05_p95')}), "
        "confirmando que a amostragem é irregular.",
        f"- Divisão cronológica treino/validação/teste: {value('split_sizes')} intervalos.",
        "",
        "## Cobertura e lacunas",
        "",
        f"- Cobertura dos intervalos observados (não preenchidos): mediana "
        f"{_pt(round(float(value('coverage_median')), 4))}; "
        f"mínima: {_pt(round(float(value('coverage_min')), 4))}.",
        "- Cobertura por *split* (mín./mediana/média, só intervalos observados): "
        + "; ".join(
            f"{label} {value(f'coverage_{name}_min_median_mean').replace('.', ',')}"
            for name, label in SPLIT_LABELS.items()
        )
        + ".",
        f"- Intervalos com cobertura < 100%: "
        f"{_pt(round(float(value('frac_buckets_coverage_below_1')) * int(value('n_intervals'))))}"
        f" de {_pt(value('n_intervals'))}.",
        f"- Regra em vigor: `min_coverage = {value('min_coverage')}` (intervalos com cobertura "
        f"abaixo disso viram lacuna), `trim_leading_missing = "
        f"{str(value('trim_leading_missing')).lower()}`, `max_fill_gap = "
        f"{cfg['data']['max_fill_gap']}` (lacunas curtas: interpolação linear) e "
        f'`long_gap_fill = "{value("long_gap_fill")}"` (lacunas longas).',
        f"- Intervalos sem nenhuma amostra: {_pt(value('n_buckets_no_data'))}; com amostras, "
        f"mas abaixo de `min_coverage`: {_pt(value('n_buckets_low_coverage'))}; preenchidos: "
        f"{_pt(value('n_buckets_filled'))}, dos quais "
        f"{_pt(value('n_buckets_filled_seasonal'))} pelo método sazonal.",
        f"- Lacunas maiores que `max_fill_gap`: {value('n_gaps_above_max_fill')} — "
        f"{value('gaps_above_max_fill_detail')}.",
        "- Método sazonal: cada intervalo da lacuna recebe a demanda do mesmo horário do dia "
        f"anterior (`s = {cfg['forecast']['season_period']}` intervalos antes), somada a uma "
        "correção que varia linearmente entre a diferença observada na borda esquerda e a "
        "observada na borda direita. Toda lacuna preenchida assim fica no treino (conferido em "
        "`make data`), de modo que nenhuma previsão da validação ou do teste usa dado posterior "
        "à sua origem.",
        "",
        "As estatísticas por máquina abaixo são do **rastro completo** "
        f"({_pt(value('n_buckets_trace'))} intervalos), independentemente de qualquer corte:",
        "",
        f"- Mediana de intervalos com dado por máquina: "
        f"{_pt(value('median_buckets_per_machine'))} de {_pt(value('n_buckets_trace'))}.",
        f"- Máquinas cujo primeiro intervalo é 0: "
        f"{_pt(value('n_machines_starting_at_bucket_0'))} de {_pt(value('n_machines'))}; "
        f"primeiro intervalo por máquina (mín./mediana/máx.): "
        f"{value('machine_first_bucket_min_median_max')}; último: "
        f"{value('machine_last_bucket_min_median_max')}. Os `time_stamp` compartilham a mesma "
        "origem; o que varia é o tempo de vida de cada máquina no rastro.",
        f"- `NaN` restantes em `demand_cpu`: {value('n_nan_demand_cpu')}.",
        "",
        "## Amostras descartadas",
        "",
        f"- CPU nula ou fora de [0, 100]: {_pt(value('n_cpu_dropped'))} amostras "
        f"({float(value('frac_cpu_dropped')):.2e} das linhas).",
        f"- Memória nula ou fora de [0, 100]: {_pt(value('n_mem_dropped'))} amostras.",
        "",
        "## Demanda (em máquinas equivalentes totalmente utilizadas)",
        "",
        "Só intervalos observados; os preenchidos ficam de fora das estatísticas.",
        "",
        "| Série | mín. | média | mediana | p95 | máx. |",
        "|---|---|---|---|---|---|",
    ]
    for col in ("demand_cpu", "demand_mem"):
        lines.append(
            f"| `{col}` | {_pt(value(f'{col}_min'))} | {_pt(value(f'{col}_mean'))} | "
            f"{_pt(value(f'{col}_median'))} | {_pt(value(f'{col}_p95'))} | "
            f"{_pt(value(f'{col}_max'))} |"
        )
    lines += [
        "",
        "## Limitações",
        "",
        "- **Demanda censurada:** a utilização por máquina tem teto de 100%, então em momentos",
        "  de saturação a demanda observada subestima a demanda real.",
        "- **Cobertura desigual:** onde a cobertura é menor, a demanda é a média das máquinas que",
        "  reportaram vezes N, isto é, uma extrapolação que supõe que as ausentes se comportam",
        "  como as presentes.",
        f"- **Intervalos preenchidos:** {_pt(value('n_buckets_filled'))} intervalos são "
        "estimativas, não medições;",
        "  entram no ajuste dos previsores, mas não nas métricas de previsão nem de alocação.",
        f"- A série cobre {_pt(value('duration_days'))} dias, o que deixa o conjunto de teste",
        "  pequeno (limitação aceita no v0).",
        "",
        "Tabela completa em `results/tables/data_quality.csv`.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
