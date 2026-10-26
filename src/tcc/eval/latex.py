"""Tabelas em LaTeX para o relatório, geradas a partir de `results/tables/`.

Hoje gera só o erro de previsão por horizonte (Apêndice A), a partir de `forecast_metrics.csv`.
O arquivo é gravado em `results/tables/` e copiado à mão para `lib/report/tables/`, como as
figuras.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tcc.data.paths import resolve

#: Ordem e rótulos dos previsores, os mesmos da Tabela de erro com h = 1 (RMSE crescente).
MODELS: dict[str, str] = {
    "arima": "ARIMA",
    "gru": "GRU",
    "naive": "Ingênuo",
    "holt_winters": "Holt-Winters",
    "moving_average": "Média móvel",
    "seasonal_naive": "Sazonal ingênuo",
}
SPLITS: dict[str, str] = {"val": "na validação", "test": "no teste"}


def _num(x: float, decimals: int = 2, signed: bool = False) -> str:
    """Número com vírgula decimal; com sinal explícito no viés."""
    if signed:
        return "$" + f"{x:+.{decimals}f}".replace(".", "{,}") + "$"
    return f"{x:.{decimals}f}".replace(".", ",")


def forecast_by_horizon_table(metrics: pd.DataFrame, split: str) -> str:
    """Tabela com RMSE, MAE, MAPE, viés e taxa de subestimação por previsor e horizonte `h`."""
    df = metrics[metrics["split"] == split]
    n_origins = int(df["n_origins"].iloc[0])
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        rf"\caption{{Erro das previsões {SPLITS[split]}, por horizonte $h$.}}",
        rf"\label{{tab:erro-horizonte-{split}}}",
        r"\footnotesize",
        r"\begin{tabular}{lcrrrrr}",
        r"\toprule",
        r"\textbf{Previsor} & $h$ & \textbf{RMSE} & \textbf{MAE} & \textbf{MAPE (\%)} "
        r"& \textbf{Viés} & \textbf{Taxa de subestimação} \\",
        r"\midrule",
    ]
    for i, (model, label) in enumerate(MODELS.items()):
        rows = df[df["model"] == model].sort_values("h")
        if i > 0:
            lines.append(r"\addlinespace")
        for j, r in enumerate(rows.itertuples()):
            name = label if j == 0 else ""
            lines.append(
                f"{name} & {r.h} & {_num(r.rmse)} & {_num(r.mae)} & {_num(r.mape)} "
                f"& {_num(r.bias, signed=True)} & {_num(100 * r.under_rate, 1)}\\% \\\\"
            )
    coverage = df["mape_coverage"].min()
    coverage_text = (
        "a máscara do MAPE não excluiu nenhuma"
        if coverage == 1
        else f"a cobertura da máscara do MAPE é de pelo menos {_num(100 * coverage, 1)}\\%"
    )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        "",
        r"\smallskip",
        r"\parbox{\textwidth}{\footnotesize Nota: RMSE, MAE e viés em máquinas equivalentes; "
        r"viés positivo indica superestimação. "
        rf"Cada linha usa as mesmas {n_origins} origens, e {coverage_text}. "
        r"O sazonal ingênuo repete o valor de um dia antes "
        r"e, por isso, não depende de $h$.}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Gera as tabelas em LaTeX do relatório.")
    parser.add_argument("--tables-dir", default="results/tables", help="pasta das tabelas")
    args = parser.parse_args(argv)

    tables_dir: Path = resolve(args.tables_dir)
    metrics = pd.read_csv(tables_dir / "forecast_metrics.csv")
    out = tables_dir / "forecast_by_horizon.tex"
    out.write_text("\n".join(forecast_by_horizon_table(metrics, s) for s in SPLITS))
    print(f"[latex] erro por horizonte em {out}")


if __name__ == "__main__":
    main()
