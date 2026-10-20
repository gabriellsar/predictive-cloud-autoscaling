"""Experimento principal (Fase 4): varredura de parâmetros e pontos de operação.

A política de decisão é fixa por família e **só o previsor muda** dentro da família
preditiva. É isso que permite atribuir as diferenças de custo e de violações à qualidade
da previsão.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from tcc.data import load_series, split_series
from tcc.eval.allocation import capacity_per_instance
from tcc.forecast.base import Forecaster
from tcc.forecast.cache import CachedForecaster
from tcc.forecast.evaluate import build_forecasters
from tcc.sim.policies import OraclePolicy, PredictivePolicy, ReactiveHPAPolicy, StaticPeakPolicy
from tcc.sim.simulator import simulate

SPLITS = ("val", "test")
TABLE_COLUMNS = [
    "policy",
    "forecaster",
    "param_name",
    "param",
    "L",
    "split",
    "C",
    "C_norm",
    "V",
    "U",
    "O",
    "changes",
]
OPERATING_COLUMNS = [
    "policy",
    "forecaster",
    "epsilon",
    "param_name",
    "param",
    "C_norm_test",
    "V_test",
    "U_test",
    "O_test",
    "changes_test",
]
#: Rótulo de "previsor" para as políticas que não usam previsão.
NO_FORECASTER = "-"


@dataclass
class Setup:
    """Tudo o que o experimento precisa, calculado uma vez."""

    demand: np.ndarray
    splits: dict[str, slice]
    k: float
    train_peak: float
    forecasters: list[Forecaster]


def prepare(cfg: dict[str, Any], verbose: bool = True) -> Setup:
    """Carrega a série, calcula `k` no treino e ajusta os previsores **só no treino**."""
    series = load_series(cfg)
    splits = split_series(series, cfg)
    demand = series["demand_cpu"].to_numpy(dtype=float)
    train = demand[splits["train"]]
    k = capacity_per_instance(train, int(cfg["sim"]["n_peak"]))

    forecasters: list[Forecaster] = []
    for forecaster in build_forecasters(cfg):
        if verbose:
            print(f"[experimento] ajustando {forecaster.name} no treino...", flush=True)
        forecaster.fit(train)
        # A previsão não depende da margem: o cache evita refazê-la a cada valor de m.
        forecasters.append(CachedForecaster(forecaster))
    return Setup(demand, splits, k, float(train.max()), forecasters)


def run_sweep(cfg: dict[str, Any], setup: Setup, lead_time: int) -> pd.DataFrame:
    """Simula todas as políticas e parâmetros em `val` e `test` para um `L`."""
    sim_cfg = cfg["sim"]
    c = float(sim_cfg["cost_per_instance"])
    n_min = int(sim_cfg["n_min"])
    margins = [float(m) for m in sim_cfg["margins"]]
    targets = [float(u) for u in sim_cfg["hpa_targets"]]

    rows: list[dict[str, Any]] = []
    for split_name in SPLITS:
        split = setup.splits[split_name]

        def run(policy: Any, cost_oracle: float | None) -> dict[str, float]:
            return simulate(
                setup.demand,
                split,
                policy,
                k=setup.k,
                lead_time=lead_time,
                c=c,
                n_min=n_min,
                cost_oracle=cost_oracle,
            ).metrics

        # C_norm é relativo ao oráculo com m = 0 no mesmo split e com o mesmo L.
        cost_oracle = run(OraclePolicy(setup.demand, margin=0.0), None)["C"]

        def record(policy: str, forecaster: str, name: str, value: float, m: dict) -> None:
            rows.append(
                {
                    "policy": policy,
                    "forecaster": forecaster,
                    "param_name": name,
                    "param": value,
                    "L": lead_time,
                    "split": split_name,
                    **{key: m[key] for key in ("C", "C_norm", "V", "U", "O", "changes")},
                }
            )

        for margin in margins:
            record(
                "oracle",
                NO_FORECASTER,
                "m",
                margin,
                run(OraclePolicy(setup.demand, margin), cost_oracle),
            )
            record(
                "static_peak",
                NO_FORECASTER,
                "m",
                margin,
                run(StaticPeakPolicy(setup.train_peak, margin), cost_oracle),
            )
            for forecaster in setup.forecasters:
                record(
                    "predictive",
                    forecaster.name,
                    "m",
                    margin,
                    run(PredictivePolicy(forecaster, margin), cost_oracle),
                )

        for target in targets:
            policy = ReactiveHPAPolicy(
                target_utilization=target,
                tolerance=float(sim_cfg["hpa_tolerance"]),
                scale_down_window=int(sim_cfg["hpa_scale_down_window"]),
            )
            record("reactive_hpa", NO_FORECASTER, "u_star", target, run(policy, cost_oracle))

    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


def operating_points(table: pd.DataFrame, epsilons: list[float], lead_time: int) -> pd.DataFrame:
    """Escolhe o parâmetro **na validação** e reporta suas métricas **no teste**.

    Para cada (política, previsor) e cada `ε`: entre os parâmetros com `V_val ≤ ε`, o de
    menor custo na validação (por monotonicidade, a menor margem `m` ou o maior `u*`). O
    teste nunca participa da escolha. Sem parâmetro viável, a linha fica `n/a`.
    """
    main = table[table["L"] == lead_time]
    rows: list[dict[str, Any]] = []
    for (policy, forecaster), group in main.groupby(["policy", "forecaster"], sort=False):
        val = group[group["split"] == "val"]
        test = group[group["split"] == "test"].set_index("param")
        for epsilon in epsilons:
            feasible = val[val["V"] <= epsilon]
            base = {
                "policy": policy,
                "forecaster": forecaster,
                "epsilon": epsilon,
                "param_name": group["param_name"].iloc[0],
            }
            if feasible.empty:
                rows.append({**base, "param": "n/a"} | {c: "n/a" for c in OPERATING_COLUMNS[5:]})
                continue
            chosen = feasible.sort_values(["C", "V"]).iloc[0]
            result = test.loc[chosen["param"]]
            rows.append(
                {
                    **base,
                    "param": chosen["param"],
                    "C_norm_test": result["C_norm"],
                    "V_test": result["V"],
                    "U_test": result["U"],
                    "O_test": result["O"],
                    "changes_test": result["changes"],
                }
            )
    return pd.DataFrame(rows, columns=OPERATING_COLUMNS)
