"""Previsores simples: persistência, média móvel e sazonal ingênuo.

Os três são vetorizados em `forecast_many`, mas a versão vetorizada só indexa posições
`<= τ`, o que mantém a garantia de não olhar o futuro.
"""

from __future__ import annotations

import numpy as np

from tcc.forecast.base import BaseForecaster


class NaiveForecaster(BaseForecaster):
    """Persistência: `ŷ(τ + h) = y[τ]`, para qualquer `h`."""

    name = "naive"
    min_history = 1

    def forecast(self, history: np.ndarray, h: int) -> float:
        history = self._check(history, h)
        return float(history[-1])

    def forecast_many(self, series: np.ndarray, origins: np.ndarray, h: int) -> np.ndarray:
        self._check(series[: int(origins[0]) + 1], h)
        return np.asarray(series, dtype=float)[origins]


class MovingAverageForecaster(BaseForecaster):
    """Média das últimas `window` observações, repetida para todo horizonte."""

    name = "moving_average"

    def __init__(self, window: int) -> None:
        if window < 1:
            raise ValueError(f"moving_average: janela deve ser >= 1, recebi {window}")
        self.window = int(window)
        self.min_history = self.window

    def forecast(self, history: np.ndarray, h: int) -> float:
        history = self._check(history, h)
        return float(history[-self.window :].mean())

    def forecast_many(self, series: np.ndarray, origins: np.ndarray, h: int) -> np.ndarray:
        self._check(series[: int(origins[0]) + 1], h)
        y = np.asarray(series, dtype=float)
        cumulative = np.concatenate([[0.0], np.cumsum(y)])
        # média de y[τ - window + 1 .. τ], ou seja, só o passado até a origem
        ends = origins + 1
        starts = ends - self.window
        return (cumulative[ends] - cumulative[starts]) / self.window


class SeasonalNaiveForecaster(BaseForecaster):
    """Valor de um período sazonal atrás, alinhado ao horizonte.

    `ŷ(τ + h) = y[τ + h - m * ceil(h / m)]`, que é a última observação disponível no
    mesmo ponto do ciclo. Para `h <= m` isso é simplesmente `y[τ + h - m]`.
    """

    name = "seasonal_naive"

    def __init__(self, season_period: int) -> None:
        if season_period < 1:
            raise ValueError(f"seasonal_naive: período deve ser >= 1, recebi {season_period}")
        self.season_period = int(season_period)
        self.min_history = self.season_period

    def _lag(self, h: int) -> int:
        """Quantos passos atrás da origem está o valor usado."""
        cycles = int(np.ceil(h / self.season_period))
        return self.season_period * cycles - h

    def forecast(self, history: np.ndarray, h: int) -> float:
        history = self._check(history, h)
        lag = self._lag(h)
        if lag >= len(history):
            raise ValueError(
                f"seasonal_naive: histórico com {len(history)} pontos é curto demais para "
                f"olhar {lag + 1} passos atrás (período {self.season_period}, h = {h})"
            )
        return float(history[-1 - lag])

    def forecast_many(self, series: np.ndarray, origins: np.ndarray, h: int) -> np.ndarray:
        self._check(series[: int(origins[0]) + 1], h)
        y = np.asarray(series, dtype=float)
        indices = origins - self._lag(h)
        if indices.min() < 0:
            raise ValueError("seasonal_naive: origem anterior ao primeiro ciclo sazonal")
        return y[indices]
