"""Protocolo de avaliação *walk-forward* (seção 3 da spec da Fase 2).

Para cada previsor, horizonte `h` e *split*, percorre todas as origens `τ` cujo alvo
`τ + h` cai no *split* e compara `ŷ(τ + h)` com `y[τ + h]`. O histórico das primeiras
origens de `val` e `test` inclui o fim do *split* anterior — isso é passado legítimo.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from tcc.data import load_series, split_series
from tcc.forecast.arima import ArimaForecaster
from tcc.forecast.base import Forecaster
from tcc.forecast.baselines import (
    MovingAverageForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)
from tcc.forecast.holt_winters import HoltWintersForecaster
from tcc.forecast.metrics import all_metrics

#: *Splits* avaliados. O treino não entra: nele os parâmetros foram estimados.
EVAL_SPLITS = ("val", "test")

METRIC_COLUMNS = ["mae", "rmse", "mape", "mape_coverage", "bias", "under_rate"]


def build_forecasters(cfg: dict[str, Any]) -> list[Forecaster]:
    """Monta os cinco previsores do v0 com os parâmetros de `configs/v0.toml`."""
    fc = cfg["forecast"]
    return [
        NaiveForecaster(),
        MovingAverageForecaster(int(fc["ma_window"])),
        SeasonalNaiveForecaster(int(fc["season_period"])),
        HoltWintersForecaster(int(fc["season_period"])),
        ArimaForecaster(tuple(int(v) for v in fc["arima_order"])),
    ]


def walk_forward(
    forecaster: Forecaster,
    y: np.ndarray,
    target_slice: slice,
    h: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Devolve (reais, previstos) para todos os alvos do *split* com horizonte `h`."""
    targets = np.arange(target_slice.start, target_slice.stop)
    origins = targets - h
    if origins[0] < 0:
        keep = origins >= 0
        targets, origins = targets[keep], origins[keep]
    predictions = np.asarray(forecaster.forecast_many(y, origins, h), dtype=float)
    return y[targets], predictions


def evaluate(
    cfg: dict[str, Any],
    series: pd.DataFrame | None = None,
    forecasters: list[Forecaster] | None = None,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict[tuple[str, int, str], tuple[np.ndarray, np.ndarray]]]:
    """Avalia todos os previsores e devolve a tabela de métricas e as previsões.

    As previsões voltam junto para alimentar as figuras sem recalcular nada.
    """
    series = load_series(cfg) if series is None else series
    splits = split_series(series, cfg)
    y = series["demand_cpu"].to_numpy(dtype=float)
    if np.isnan(y).any():
        raise ValueError("há NaN em demand_cpu; a Fase 2 pressupõe a série sem lacunas")

    train = y[splits["train"]]
    # MAPE mascara y próximo de zero; o limiar vem só do treino, como manda a regra de
    # ausência de vazamento.
    eps = 0.01 * float(np.median(train))
    horizons = [int(h) for h in cfg["forecast"]["horizons"]]

    rows: list[dict[str, Any]] = []
    predictions: dict[tuple[str, int, str], tuple[np.ndarray, np.ndarray]] = {}
    for forecaster in forecasters if forecasters is not None else build_forecasters(cfg):
        if verbose:
            print(f"[previsão] ajustando {forecaster.name}...", flush=True)
        forecaster.fit(train)
        for h in horizons:
            for split_name in EVAL_SPLITS:
                actual, predicted = walk_forward(forecaster, y, splits[split_name], h)
                predictions[(forecaster.name, h, split_name)] = (actual, predicted)
                rows.append(
                    {
                        "model": forecaster.name,
                        "h": h,
                        "split": split_name,
                        **all_metrics(actual, predicted, eps),
                        "n_origins": len(actual),
                    }
                )
        if verbose:
            test_h1 = predictions[(forecaster.name, horizons[0], "test")]
            print(
                f"[previsão] {forecaster.name}: RMSE em teste (h = {horizons[0]}) = "
                f"{np.sqrt(np.mean((test_h1[0] - test_h1[1]) ** 2)):.1f}",
                flush=True,
            )

    metrics = pd.DataFrame(rows, columns=["model", "h", "split", *METRIC_COLUMNS, "n_origins"])
    return metrics, predictions
