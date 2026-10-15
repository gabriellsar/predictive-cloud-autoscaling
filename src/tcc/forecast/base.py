"""Interface de previsores.

Este módulo é deliberadamente **livre de dependências de modelagem** (nada de
`statsmodels`): a rede neural da semana seguinte precisa implementar a mesma interface
sem ele. Só `numpy` entra aqui.

Contrato: `forecast(history, h)` devolve a previsão de `y[len(history) - 1 + h]` usando
**somente** `history`. Quem precisar de atalho por eficiência mantém um cache interno
equivalente, validado pelo teste de ausência de olhar para o futuro.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Forecaster(Protocol):
    """Protocolo que todo previsor do projeto implementa."""

    name: str

    def fit(self, train: np.ndarray) -> None:
        """Estima parâmetros vendo **só** o treino. Eles ficam fixos na avaliação."""
        ...

    def forecast(self, history: np.ndarray, h: int) -> float:
        """Previsão de `y[len(history) - 1 + h]`, usando somente `history`."""
        ...


class BaseForecaster:
    """Implementação comum: validação de `h` e `forecast_many` genérico.

    Herdar daqui é opcional — qualquer objeto que satisfaça `Forecaster` serve.
    """

    name: str = "base"
    #: Mínimo de observações que `forecast` exige no histórico.
    min_history: int = 1

    def fit(self, train: np.ndarray) -> None:  # pragma: no cover - previsores sem ajuste
        """Por padrão não há nada a estimar."""
        return None

    def forecast(self, history: np.ndarray, h: int) -> float:
        raise NotImplementedError

    def forecast_many(self, series: np.ndarray, origins: np.ndarray, h: int) -> np.ndarray:
        """Previsões de horizonte `h` a partir de várias origens.

        A implementação genérica chama `forecast` com o prefixo de cada origem, de modo
        que não há como olhar o futuro. Previsores que sobrescreverem este método para
        vetorizar precisam manter a mesma garantia.
        """
        return np.array([self.forecast(series[: int(tau) + 1], h) for tau in origins])

    def _check(self, history: np.ndarray, h: int) -> np.ndarray:
        """Valida `h` e o tamanho do histórico, com mensagem clara."""
        if h < 1:
            raise ValueError(f"{self.name}: o horizonte h deve ser >= 1, recebi h = {h}")
        history = np.asarray(history, dtype=float)
        if history.ndim != 1:
            raise ValueError(f"{self.name}: o histórico deve ser unidimensional")
        if len(history) < self.min_history:
            raise ValueError(
                f"{self.name}: histórico com {len(history)} pontos, "
                f"mas o previsor precisa de pelo menos {self.min_history}"
            )
        return history
