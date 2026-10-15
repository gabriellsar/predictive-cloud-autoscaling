"""Ponto de entrada da Fase 2: avalia os previsores e grava tabela e figuras."""

from __future__ import annotations

import argparse

from tcc.config import load_config
from tcc.data.paths import resolve
from tcc.forecast.evaluate import METRIC_COLUMNS, evaluate
from tcc.forecast.figures import make_forecast_figures


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fase 2: avalia os previsores de base.")
    parser.add_argument("--config", default=None, help="caminho de um TOML alternativo")
    parser.add_argument("--skip-figures", action="store_true", help="não gera as figuras")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    metrics, predictions = evaluate(cfg)

    tables_dir = resolve("results/tables")
    tables_dir.mkdir(parents=True, exist_ok=True)
    out = tables_dir / "forecast_metrics.csv"
    metrics.round({column: 4 for column in METRIC_COLUMNS}).to_csv(out, index=False)
    print(f"[previsão] métricas em {out}")

    if not args.skip_figures:
        make_forecast_figures(cfg, metrics, predictions)


if __name__ == "__main__":
    main()
