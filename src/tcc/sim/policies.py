"""Políticas de decisão (seção 2 da spec da Fase 3).

Toda política responde `required_instances(tau, history, state)`: quantas instâncias
estarão ativas no intervalo `tau + L`. `history` é a demanda **até a origem** `tau`, o que
torna o vazamento estruturalmente difícil.

A única exceção é o oráculo, que recebe a série inteira na construção porque olhar o
futuro é a definição dele: ele é o limite inferior de custo, não uma política realizável.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from tcc.eval.allocation import RELATIVE_TOLERANCE
from tcc.forecast.base import Forecaster


@dataclass(frozen=True)
class PolicyState:
    """O que a política sabe sobre o sistema na origem `tau`."""

    n_active: int  # instâncias ativas em tau (decisão de tau - L, já com o atraso)
    k: float  # capacidade de uma instância
    lead_time: int  # L


class Policy(Protocol):
    name: str

    def required_instances(self, tau: int, history: np.ndarray, state: PolicyState) -> int: ...


def ceil_tolerant(x: float) -> int:
    """`ceil(x)`, mas um `x` a menos de `RELATIVE_TOLERANCE` relativo de um inteiro conta
    como esse inteiro.

    Sem isso, quando o valor exato é inteiro (por exemplo `(1 + m) · pico / k` com
    `k = pico / n_peak` e `(1 + m) · n_peak` inteiro), um *ulp* a mais no cálculo faz o
    `ceil` pular para o inteiro de cima, e o resultado passa a depender da ordem de soma
    do DuckDB. A tolerância é a mesma da comparação `d_t > k·n_t` em `eval/allocation.py`:
    a capacidade que deixa de ser alocada é no máximo `RELATIVE_TOLERANCE · d_t`, que a
    métrica de violação já trata como empate.
    """
    nearest = round(x)
    if abs(x - nearest) <= RELATIVE_TOLERANCE * max(1.0, abs(x)):
        return int(nearest)
    return int(math.ceil(x))


def _instances_for(demand: float, k: float, margin: float) -> int:
    """`ceil((1 + m) · d / k)`, nunca negativo (com a tolerância de `ceil_tolerant`)."""
    return ceil_tolerant(max(0.0, (1.0 + margin) * demand) / k)


class StaticPeakPolicy:
    """Dimensionamento fixo no pico do treino: `n = ceil((1 + m) · max(d_train) / k)`."""

    def __init__(self, train_peak: float, margin: float = 0.0) -> None:
        self.train_peak = float(train_peak)
        self.margin = float(margin)
        self.name = "static_peak"

    def required_instances(self, tau: int, history: np.ndarray, state: PolicyState) -> int:
        return _instances_for(self.train_peak, state.k, self.margin)


class OraclePolicy:
    """Conhece `d[tau + L]`. Limite inferior de custo, não é realizável."""

    def __init__(self, demand: np.ndarray, margin: float = 0.0) -> None:
        self.demand = np.asarray(demand, dtype=float)
        self.margin = float(margin)
        self.name = "oracle"

    def required_instances(self, tau: int, history: np.ndarray, state: PolicyState) -> int:
        return _instances_for(float(self.demand[tau + state.lead_time]), state.k, self.margin)


class ReactiveHPAPolicy:
    """Reativa no estilo HPA do Kubernetes.

    Mede a utilização atual `u = d[tau] / (k · n_active)`. Dentro da tolerância, mantém.
    Fora dela, recomenda `n = ceil(d[tau] / (k · u*))`. Para **reduzir**, usa o máximo das
    recomendações das últimas `scale_down_window` origens — a janela de estabilização que
    evita que o cluster encolha por causa de um único vale.
    """

    def __init__(
        self,
        target_utilization: float,
        tolerance: float,
        scale_down_window: int,
    ) -> None:
        if not 0.0 < target_utilization <= 1.0:
            raise ValueError(f"u* deve estar em (0, 1], recebi {target_utilization}")
        self.target = float(target_utilization)
        self.tolerance = float(tolerance)
        self.window = int(scale_down_window)
        self.name = "reactive_hpa"
        self._recommendations: list[int] = []

    def reset(self) -> None:
        """Limpa a janela de estabilização entre simulações."""
        self._recommendations = []

    def required_instances(self, tau: int, history: np.ndarray, state: PolicyState) -> int:
        observed = float(history[-1])
        recommended = ceil_tolerant(observed / (state.k * self.target))
        self._recommendations.append(recommended)

        utilization = observed / (state.k * max(state.n_active, 1))
        if abs(utilization / self.target - 1.0) <= self.tolerance:
            return state.n_active
        if recommended > state.n_active:
            return recommended
        return max(self._recommendations[-self.window :])


class PredictivePolicy:
    """Aloca para a demanda prevista com margem: `n = ceil((1 + m) · d̂ / k)`.

    O horizonte da previsão é exatamente o *lead time*: `h = L`.
    """

    def __init__(self, forecaster: Forecaster, margin: float = 0.0) -> None:
        self.forecaster = forecaster
        self.margin = float(margin)
        self.name = f"predictive_{forecaster.name}"

    def required_instances(self, tau: int, history: np.ndarray, state: PolicyState) -> int:
        predicted = float(self.forecaster.forecast(history, state.lead_time))
        return _instances_for(max(0.0, predicted), state.k, self.margin)
