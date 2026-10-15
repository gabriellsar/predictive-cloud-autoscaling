"""Holt-Winters aditivo: ajuste no treino com `statsmodels`, recursão própria na avaliação.

Por que a recursão é própria: a avaliação *walk-forward* faz uma previsão por origem, e
`HoltWintersResults` do `statsmodels` não tem `append`/`apply` (isso só existe nos modelos
de espaço de estados). Reajustar a cada origem seria lento demais, então o previsor mantém
o **cache de estado** que a spec autoriza: nível, tendência e sazonais são atualizados
incrementalmente pela recursão clássica (Hyndman), com os parâmetros estimados no treino
e congelados. O teste `test_holt_winters_reproduz_o_statsmodels` confere que essa recursão
reproduz os valores ajustados do `statsmodels`, e o teste de ausência de olhar para o
futuro cobre o cache.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tcc.forecast.base import BaseForecaster


@dataclass
class _State:
    """Estado da recursão depois de observar `n` pontos."""

    n: int
    level: float
    trend: float
    seasons: np.ndarray  # seasons[i] é o sazonal mais recente da fase i


class HoltWintersForecaster(BaseForecaster):
    """Suavização exponencial com tendência e sazonalidade aditivas."""

    name = "holt_winters"

    def __init__(self, season_period: int) -> None:
        self.season_period = int(season_period)
        self.min_history = 1
        self._params: dict[str, float] | None = None
        self._initial: _State | None = None
        self._cache: _State | None = None
        self._cache_history: np.ndarray | None = None

    def fit(self, train: np.ndarray) -> None:
        """Estima α, β, γ e o estado inicial no treino, com `statsmodels`."""
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        train = np.asarray(train, dtype=float)
        m = self.season_period
        if len(train) < 2 * m:
            raise ValueError(
                f"holt_winters: período sazonal {m} exige pelo menos {2 * m} pontos de "
                f"treino (dois ciclos completos), mas o treino tem {len(train)}"
            )

        res = ExponentialSmoothing(
            train,
            trend="add",
            seasonal="add",
            seasonal_periods=m,
            initialization_method="heuristic",
        ).fit()
        params = res.params
        self._params = {
            "alpha": float(params["smoothing_level"]),
            "beta": float(params["smoothing_trend"]),
            "gamma": float(params["smoothing_seasonal"]),
        }
        self._initial = _State(
            n=0,
            level=float(params["initial_level"]),
            trend=float(params["initial_trend"]),
            seasons=np.asarray(params["initial_seasons"], dtype=float).copy(),
        )
        self._cache = None
        self._cache_history = None

    def _advance(self, state: _State, observations: np.ndarray) -> _State:
        """Roda a recursão de Holt-Winters sobre novas observações."""
        assert self._params is not None
        alpha, beta, gamma = (self._params[k] for k in ("alpha", "beta", "gamma"))
        m = self.season_period
        level, trend = state.level, state.trend
        seasons = state.seasons.copy()
        n = state.n

        for y in observations:
            phase = n % m
            season = seasons[phase]
            previous_level, previous_trend = level, trend
            level = alpha * (y - season) + (1 - alpha) * (previous_level + previous_trend)
            trend = beta * (level - previous_level) + (1 - beta) * previous_trend
            seasons[phase] = gamma * (y - previous_level - previous_trend) + (1 - gamma) * season
            n += 1

        return _State(n=n, level=level, trend=trend, seasons=seasons)

    def _state_for(self, history: np.ndarray) -> _State:
        """Estado após `history`, reaproveitando o cache quando o prefixo bate."""
        if self._initial is None:
            raise RuntimeError("holt_winters: chame fit() antes de prever")

        cache, cached_history = self._cache, self._cache_history
        if (
            cache is not None
            and cached_history is not None
            and len(history) >= cache.n
            and np.array_equal(cached_history, history[: cache.n])
        ):
            state = self._advance(cache, history[cache.n :])
        else:
            state = self._advance(self._initial, history)

        self._cache = state
        self._cache_history = history[: state.n].copy()
        return state

    def forecast(self, history: np.ndarray, h: int) -> float:
        history = self._check(history, h)
        state = self._state_for(history)
        m = self.season_period
        # sazonal mais recente da fase alvo: o valor guardado já é o do último ciclo
        season = state.seasons[(state.n + h - 1) % m]
        return float(state.level + h * state.trend + season)
