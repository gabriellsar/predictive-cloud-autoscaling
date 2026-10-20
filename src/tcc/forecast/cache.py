"""Cache de previsões para a varredura de margens.

Na política preditiva a previsão não depende da margem `m`: varrer 61 margens refaria as
mesmas previsões 61 vezes. Este invólucro guarda cada previsão sob uma chave que é o
**conteúdo** do histórico (um *hash* dos bytes) mais o horizonte. Um histórico diferente,
mesmo que do mesmo tamanho, gera outra chave, então o cache não abre caminho para olhar
o futuro — o teste de ausência de olhar para o futuro roda também sobre ele.
"""

from __future__ import annotations

import hashlib

import numpy as np

from tcc.forecast.base import Forecaster


class CachedForecaster:
    """Envolve um previsor já ajustado e memoriza `forecast(history, h)`."""

    def __init__(self, forecaster: Forecaster) -> None:
        self.inner = forecaster
        self.name = forecaster.name
        self._memory: dict[tuple[int, bytes], float] = {}
        self.hits = 0
        self.misses = 0

    def fit(self, train: np.ndarray) -> None:
        """Reajustar invalida tudo o que foi memorizado."""
        self.inner.fit(train)
        self._memory.clear()

    def forecast(self, history: np.ndarray, h: int) -> float:
        history = np.ascontiguousarray(history, dtype=float)
        key = (int(h), hashlib.blake2b(history.tobytes(), digest_size=16).digest())
        if key in self._memory:
            self.hits += 1
            return self._memory[key]
        self.misses += 1
        value = float(self.inner.forecast(history, h))
        self._memory[key] = value
        return value

    def forecast_many(self, series: np.ndarray, origins: np.ndarray, h: int) -> np.ndarray:
        return np.array([self.forecast(series[: int(tau) + 1], h) for tau in origins])
