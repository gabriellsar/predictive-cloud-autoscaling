"""Ponto de entrada das Fases 3 e 4 (`make sim`).

Gera, a partir de `data/processed/` e de `results/tables/forecast_metrics.csv`:
`allocation_metrics.csv`, `operating_points.csv`, as figuras da Fase 4 e as
verificações de sanidade da Fase 3.
"""

from __future__ import annotations

import argparse

import pandas as pd

from tcc.config import load_config
from tcc.data.paths import resolve
from tcc.sim.experiment import operating_points, prepare, run_sweep
from tcc.sim.figures import plot_cost_at_epsilon, plot_pareto, plot_rmse_vs_cost
from tcc.sim.sanity import write_sanity_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fases 3 e 4: simulação e experimento.")
    parser.add_argument("--config", default=None, help="caminho de um TOML alternativo")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    sim_cfg = cfg["sim"]
    main_lead = int(sim_cfg["lead_time"])
    lead_times = [main_lead] + [int(L) for L in sim_cfg.get("sensitivity_lead_times", [])]
    epsilons = [float(e) for e in sim_cfg["epsilons"]]

    tables = resolve("results/tables")
    figures = resolve("results/figures")
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    forecast_path = tables / "forecast_metrics.csv"
    if not forecast_path.exists():
        raise FileNotFoundError(f"{forecast_path} não existe; rode `make baselines` antes")

    setup = prepare(cfg)
    sweeps = []
    for lead_time in lead_times:
        print(f"[experimento] varrendo políticas com L = {lead_time}...", flush=True)
        sweeps.append(run_sweep(cfg, setup, lead_time))
    table = pd.concat(sweeps, ignore_index=True)
    table.round(6).to_csv(tables / "allocation_metrics.csv", index=False)

    points = operating_points(table, epsilons, main_lead)
    points.to_csv(tables / "operating_points.csv", index=False)

    plot_pareto(table, main_lead, epsilons, figures / "pareto_cost_violation.png")
    for lead_time in lead_times[1:]:
        plot_pareto(table, lead_time, epsilons, figures / f"pareto_cost_violation_L{lead_time}.png")
    plot_cost_at_epsilon(points, figures / "cost_at_epsilon.png")
    plot_rmse_vs_cost(points, pd.read_csv(forecast_path), main_lead, figures / "rmse_vs_cost.png")
    print(f"[experimento] tabelas em {tables} e figuras em {figures}", flush=True)

    write_sanity_report(cfg)


if __name__ == "__main__":
    main()
