"""Previsores e avaliação *walk-forward*.

`Forecaster` e os previsores simples não dependem de `statsmodels`: a rede neural da
semana seguinte implementa a mesma interface sem ele. Holt-Winters e ARIMA, que dependem,
são importados sob demanda.
"""

from typing import Any

from tcc.forecast.base import BaseForecaster, Forecaster
from tcc.forecast.baselines import (
    MovingAverageForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)

__all__ = [
    "ArimaForecaster",
    "BaseForecaster",
    "Forecaster",
    "HoltWintersForecaster",
    "MovingAverageForecaster",
    "NaiveForecaster",
    "SeasonalNaiveForecaster",
    "build_forecasters",
    "evaluate",
    "walk_forward",
]

_LAZY = {
    "ArimaForecaster": ("tcc.forecast.arima", "ArimaForecaster"),
    "HoltWintersForecaster": ("tcc.forecast.holt_winters", "HoltWintersForecaster"),
    "build_forecasters": ("tcc.forecast.evaluate", "build_forecasters"),
    "evaluate": ("tcc.forecast.evaluate", "evaluate"),
    "walk_forward": ("tcc.forecast.evaluate", "walk_forward"),
}


def __getattr__(name: str) -> Any:
    """Importa sob demanda o que puxa `statsmodels` ou o pacote de dados."""
    if name in _LAZY:
        from importlib import import_module

        module, attribute = _LAZY[name]
        return getattr(import_module(module), attribute)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
