"""Métricas de alocação (seção 3 da spec da Fase 3).

Notação idêntica à do relatório:

    C       = Σ c · n_t                              custo total
    V       = (1/T) Σ 1[ d_t > k·n_t ]               fração de intervalos com violação
    U       = Σ max(0, d_t − k·n_t) / Σ d_t          fração da demanda não atendida
    O       = Σ max(0, k·n_t − d_t) / Σ k·n_t        fração da capacidade ociosa
    changes = Σ 1[ n_t ≠ n_{t−1} ]                   número de alterações em n_t
    C_norm  = C / C_oracle                           custo relativo ao oráculo
"""

from __future__ import annotations

import numpy as np

#: Tolerância relativa na comparação `d_t > k·n_t`.
#: Sem ela, `k * ceil(d/k)` pode cair um ulp abaixo de `d` e o oráculo apareceria com
#: violações — exatamente o resultado suspeito que a spec manda investigar.
RELATIVE_TOLERANCE = 1e-9


def allocation_metrics(
    demand: np.ndarray,
    n: np.ndarray,
    k: float,
    c: float = 1.0,
    cost_oracle: float | None = None,
) -> dict[str, float]:
    """Calcula `C, V, U, O, changes` e, se houver referência, `C_norm`."""
    demand = np.asarray(demand, dtype=float)
    n = np.asarray(n, dtype=float)
    if demand.shape != n.shape:
        raise ValueError(f"demanda e n têm tamanhos diferentes: {demand.shape} e {n.shape}")
    if len(demand) == 0:
        raise ValueError("série vazia")

    capacity = k * n
    tolerance = RELATIVE_TOLERANCE * max(1.0, float(np.max(demand)))
    deficit = np.maximum(0.0, demand - capacity)
    surplus = np.maximum(0.0, capacity - demand)

    metrics = {
        "C": float(c * n.sum()),
        "V": float(np.mean(demand > capacity + tolerance)),
        "U": float(deficit.sum() / demand.sum()),
        "O": float(surplus.sum() / capacity.sum()) if capacity.sum() > 0 else 0.0,
        "changes": float(np.count_nonzero(np.diff(n))),
        "n_mean": float(n.mean()),
        "n_max": float(n.max()),
    }
    if cost_oracle is not None and cost_oracle > 0:
        metrics["C_norm"] = metrics["C"] / float(cost_oracle)
    return metrics


def capacity_per_instance(train_demand: np.ndarray, n_peak: int) -> float:
    """`k = max(d_train) / n_peak`, calculado **só com o treino**.

    Assim o pico do treino exige cerca de `n_peak` instâncias e o arredondamento por
    `ceil` tem significado: uma instância é uma fração visível do cluster.
    """
    if n_peak < 1:
        raise ValueError(f"n_peak deve ser >= 1, recebi {n_peak}")
    peak = float(np.max(train_demand))
    if peak <= 0:
        raise ValueError("o pico do treino precisa ser positivo")
    return peak / float(n_peak)
