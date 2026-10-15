"""ARIMA com ordem fixa, ajustado uma vez no treino.

Na avaliação os parâmetros ficam congelados: o estado é estendido com as novas
observações via `ARIMAResults.append(..., refit=False)`, que é o mecanismo do
`statsmodels` para aplicar um modelo já ajustado a dados novos. Reestimar a cada origem
seria lento demais. O cache guarda o prefixo que gerou o estado, então uma consulta com
prefixo diferente recalcula do zero — é isso que mantém o previsor honesto.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from tcc.forecast.base import BaseForecaster


class ArimaForecaster(BaseForecaster):
    """ARIMA(p, d, q) com ordem vinda da configuração."""

    name = "arima"

    def __init__(self, order: tuple[int, int, int]) -> None:
        self.order = tuple(int(v) for v in order)
        self.min_history = max(sum(self.order), 2)
        self._fitted: Any | None = None
        self._n_train = 0
        self._cache: Any | None = None
        self._cache_history: np.ndarray | None = None

    def fit(self, train: np.ndarray) -> None:
        from statsmodels.tsa.arima.model import ARIMA

        train = np.asarray(train, dtype=float)
        if len(train) <= self.min_history:
            raise ValueError(
                f"arima: treino com {len(train)} pontos é curto demais para a ordem {self.order}"
            )
        self._fitted = ARIMA(train, order=self.order).fit()
        self._n_train = len(train)
        self._cache = None
        self._cache_history = None

    def _results_for(self, history: np.ndarray) -> Any:
        """Resultado do `statsmodels` com o estado correspondente a `history`."""
        if self._fitted is None:
            raise RuntimeError("arima: chame fit() antes de prever")

        cache, cached_history = self._cache, self._cache_history
        if (
            cache is not None
            and cached_history is not None
            and len(history) > len(cached_history)
            and np.array_equal(cached_history, history[: len(cached_history)])
        ):
            res = cache.append(history[len(cached_history) :], refit=False)
        elif cached_history is not None and np.array_equal(cached_history, history):
            return cache
        else:
            # `apply` reaproveita os parâmetros do treino com um conjunto de dados novo
            res = self._fitted.apply(history, refit=False)

        self._cache = res
        self._cache_history = history.copy()
        return res

    def forecast(self, history: np.ndarray, h: int) -> float:
        history = self._check(history, h)
        res = self._results_for(history)
        return float(np.asarray(res.forecast(steps=h))[-1])
