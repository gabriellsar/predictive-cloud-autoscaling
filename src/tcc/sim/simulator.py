"""Simulador de alocação em tempo discreto (seção 1 da spec da Fase 3).

Temporização: a decisão é tomada no fim do intervalo `tau`, depois de observar
`d_1..d_tau`, e vale para o intervalo `tau + L`. Aumentos e reduções sofrem o **mesmo**
atraso `L` — simplificação registrada no diário.

Para que todo intervalo do *split* tenha uma decisão, as origens vão de `split.start − L`
a `split.stop − L − 1`. As primeiras usam o fim do *split* anterior, que é passado
legítimo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tcc.eval.allocation import allocation_metrics
from tcc.sim.policies import Policy, PolicyState


@dataclass(frozen=True)
class SimResult:
    """Resultado de uma simulação sobre um *split*."""

    n: np.ndarray  # instâncias ativas por intervalo do split
    metrics: dict[str, float]


def simulate(
    demand: np.ndarray,
    split: slice,
    policy: Policy,
    k: float,
    lead_time: int,
    c: float = 1.0,
    n_min: int = 1,
    n_initial: int | None = None,
    cost_oracle: float | None = None,
) -> SimResult:
    """Roda a política sobre `demand[split]` e mede custo e violações.

    `demand` é a série completa; `split` seleciona os intervalos avaliados. `n_initial` é
    o número de instâncias ativas antes do primeiro intervalo do *split*, usado só pela
    política reativa nas `L` primeiras origens (o padrão é `n_min`, e o transiente dura
    um passo).
    """
    demand = np.asarray(demand, dtype=float)
    if lead_time < 1:
        raise ValueError(f"o lead time L deve ser >= 1, recebi {lead_time}")
    if n_min < 0:
        raise ValueError(f"n_min deve ser >= 0, recebi {n_min}")

    targets = np.arange(split.start, split.stop)
    if len(targets) == 0:
        raise ValueError("o split está vazio")
    if targets[0] - lead_time < 0:
        raise ValueError(
            f"o split começa em {targets[0]} e não há histórico para a origem "
            f"{targets[0] - lead_time}: use um split que não seja o início da série"
        )
    if targets[-1] >= len(demand):
        raise ValueError("o split ultrapassa o fim da série")

    if hasattr(policy, "reset"):
        policy.reset()

    n = np.empty(len(targets), dtype=int)
    start_n = n_min if n_initial is None else int(n_initial)
    for i, target in enumerate(targets):
        tau = int(target) - lead_time
        n_active = int(n[i - lead_time]) if i - lead_time >= 0 else start_n
        state = PolicyState(n_active=n_active, k=k, lead_time=lead_time)
        requested = policy.required_instances(tau, demand[: tau + 1], state)
        n[i] = max(int(requested), n_min)

    metrics = allocation_metrics(demand[targets], n, k=k, c=c, cost_oracle=cost_oracle)
    return SimResult(n=n, metrics=metrics)
