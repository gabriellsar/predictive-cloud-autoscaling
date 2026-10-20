"""Testes obrigatórios do simulador (seção 5 da spec da Fase 3)."""

from __future__ import annotations

import numpy as np
import pytest

from tcc.eval.allocation import allocation_metrics, capacity_per_instance
from tcc.forecast.baselines import NaiveForecaster
from tcc.sim import (
    OraclePolicy,
    PolicyState,
    PredictivePolicy,
    ReactiveHPAPolicy,
    StaticPeakPolicy,
    simulate,
)


class ConstantPolicy:
    """Devolve sempre o mesmo número de instâncias."""

    def __init__(self, n: int) -> None:
        self.n = int(n)
        self.name = "constant"

    def required_instances(self, tau: int, history: np.ndarray, state: PolicyState) -> int:
        return self.n


class EchoOriginPolicy:
    """Devolve a própria origem, para tornar o atraso visível em `n`."""

    name = "echo"

    def required_instances(self, tau: int, history: np.ndarray, state: PolicyState) -> int:
        return int(tau)


def demand_series(n: int = 120, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    return 500 + 200 * np.sin(2 * np.pi * t / 24) + rng.normal(0, 30, n)


# --- 1 -------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_oraculo_sem_margem_nao_viola(seed: int) -> None:
    """Com m = 0 o oráculo aloca exatamente o necessário: V = 0 e U = 0."""
    demand = np.abs(demand_series(seed=seed))
    split = slice(20, 120)
    result = simulate(demand, split, OraclePolicy(demand, margin=0.0), k=37.3, lead_time=1)
    assert result.metrics["V"] == 0.0
    assert result.metrics["U"] == 0.0


# --- 2 -------------------------------------------------------------------------------


def test_capacidade_enorme_nao_viola_e_fica_quase_toda_ociosa() -> None:
    demand = np.abs(demand_series())
    split = slice(20, 120)
    result = simulate(demand, split, ConstantPolicy(10_000), k=10.0, lead_time=1)
    assert result.metrics["V"] == 0.0
    assert result.metrics["O"] > 0.99


# --- 3 -------------------------------------------------------------------------------


def test_capacidade_minima_viola_sempre() -> None:
    demand = np.full(60, 1000.0)
    split = slice(10, 60)
    result = simulate(demand, split, ConstantPolicy(1), k=1.0, lead_time=1, n_min=1)
    assert result.metrics["V"] == 1.0
    assert result.metrics["U"] == pytest.approx(1 - 1 / 1000)


# --- 4 -------------------------------------------------------------------------------


def test_metricas_conferidas_a_mao() -> None:
    # k = 10; capacidade = [20, 20, 30, 10, 10, 20]; demanda = [15, 25, 30, 5, 12, 18]
    demand = np.array([15.0, 25.0, 30.0, 5.0, 12.0, 18.0])
    n = np.array([2, 2, 3, 1, 1, 2])
    m = allocation_metrics(demand, n, k=10.0, c=1.0)

    assert m["C"] == 11.0  # 2 + 2 + 3 + 1 + 1 + 2
    assert m["V"] == pytest.approx(2 / 6)  # t = 2 (25 > 20) e t = 5 (12 > 10)
    assert m["U"] == pytest.approx((5 + 2) / 105)  # déficits 5 e 2, demanda total 105
    # sobras: 5, 0, 0, 5, 0, 2 = 12; capacidade total = 110
    assert m["O"] == pytest.approx(12 / 110)
    assert m["changes"] == 3.0  # 2->3, 3->1, 1->2


# --- 5 -------------------------------------------------------------------------------


def test_custo_e_proporcional_a_c() -> None:
    demand = np.abs(demand_series())
    split = slice(20, 120)
    policy = ConstantPolicy(7)
    base = simulate(demand, split, policy, k=50.0, lead_time=1, c=1.0)
    doubled = simulate(demand, split, policy, k=50.0, lead_time=1, c=2.0)

    assert base.metrics["C"] == float(base.n.sum())
    assert doubled.metrics["C"] == pytest.approx(2 * base.metrics["C"])


# --- 6 -------------------------------------------------------------------------------


def test_lead_time_desloca_a_decisao() -> None:
    """Com L = 2, a decisão tomada na origem τ aparece em n[τ + 2]."""
    demand = np.abs(demand_series())
    split = slice(20, 40)
    result = simulate(demand, split, EchoOriginPolicy(), k=10.0, lead_time=2)

    for i, target in enumerate(range(split.start, split.stop)):
        assert result.n[i] == target - 2


# --- 7 -------------------------------------------------------------------------------


@pytest.mark.parametrize("lead_time", [1, 2])
def test_politicas_realizaveis_nao_olham_para_o_futuro(lead_time: int) -> None:
    demand = np.abs(demand_series())
    split = slice(40, 120)
    last_origin = split.stop - 1 - lead_time
    corrupted = demand.copy()
    corrupted[last_origin + 1 :] = 9_999.0

    forecaster = NaiveForecaster()
    forecaster.fit(demand[: split.start])
    policies = [
        ReactiveHPAPolicy(target_utilization=0.7, tolerance=0.1, scale_down_window=6),
        PredictivePolicy(forecaster, margin=0.1),
        StaticPeakPolicy(train_peak=float(demand[: split.start].max()), margin=0.0),
    ]
    for policy in policies:
        original = simulate(demand, split, policy, k=20.0, lead_time=lead_time)
        changed = simulate(corrupted, split, policy, k=20.0, lead_time=lead_time)
        np.testing.assert_array_equal(original.n, changed.n)


def test_o_oraculo_de_fato_usa_o_futuro() -> None:
    """Controle do teste anterior: se nem o oráculo reagir, o teste não detecta nada."""
    demand = np.abs(demand_series())
    split = slice(40, 120)
    corrupted = demand.copy()
    corrupted[split.stop - 1 :] = 9_999.0

    original = simulate(demand, split, OraclePolicy(demand), k=20.0, lead_time=1)
    changed = simulate(corrupted, split, OraclePolicy(corrupted), k=20.0, lead_time=1)
    assert not np.array_equal(original.n, changed.n)


# --- 8 -------------------------------------------------------------------------------


def test_margem_maior_nunca_piora_violacoes_nem_barateia() -> None:
    demand = np.abs(demand_series(n=200))
    split = slice(50, 200)
    forecaster = NaiveForecaster()
    forecaster.fit(demand[:50])

    previous_v, previous_c = 1.0, 0.0
    for margin in (0.0, 0.05, 0.1, 0.3, 0.5):
        result = simulate(
            demand, split, PredictivePolicy(forecaster, margin=margin), k=20.0, lead_time=1
        )
        assert result.metrics["V"] <= previous_v + 1e-12
        assert result.metrics["C"] >= previous_c - 1e-12
        previous_v, previous_c = result.metrics["V"], result.metrics["C"]


# --- extras --------------------------------------------------------------------------


def test_k_sai_do_pico_do_treino() -> None:
    train = np.array([10.0, 50.0, 100.0])
    assert capacity_per_instance(train, n_peak=50) == pytest.approx(2.0)
    with pytest.raises(ValueError, match="n_peak"):
        capacity_per_instance(train, n_peak=0)


def test_split_no_inicio_da_serie_e_recusado() -> None:
    demand = np.abs(demand_series())
    with pytest.raises(ValueError, match="histórico"):
        simulate(demand, slice(0, 50), ConstantPolicy(5), k=10.0, lead_time=1)


def test_reactive_sobe_na_hora_e_desce_com_janela() -> None:
    """A janela de estabilização só atrasa a redução, nunca o aumento."""
    # demanda: baixa, pico, baixa de novo
    demand = np.concatenate([np.full(20, 100.0), np.full(3, 900.0), np.full(20, 100.0)])
    policy = ReactiveHPAPolicy(target_utilization=0.5, tolerance=0.1, scale_down_window=5)
    result = simulate(demand, slice(10, 43), policy, k=100.0, lead_time=1)

    peak_index = 20 - 10 + 1  # o pico em t = 20 é visto na origem 20 e vale em t = 21
    assert result.n[peak_index] == 18  # ceil(900 / (100 * 0.5))
    # cinco origens depois do fim do pico a janela libera a redução
    assert result.n[-1] == 2  # ceil(100 / (100 * 0.5))


# --- ceil na fronteira de inteiro ----------------------------------------------------


def test_ceil_tolerante_conferido_a_mao() -> None:
    from tcc.sim.policies import ceil_tolerant

    assert ceil_tolerant(50.0) == 50
    assert ceil_tolerant(50.0 + 1e-12) == 50  # um resíduo de ponto flutuante não sobe
    assert ceil_tolerant(50.0 - 1e-12) == 50
    assert ceil_tolerant(50.001) == 51  # um excesso real sobe
    assert ceil_tolerant(50.0 + 1e-6) == 51
    assert ceil_tolerant(0.0) == 0
    assert ceil_tolerant(0.4) == 1


def test_estatica_da_o_inteiro_exato_quando_ele_existe() -> None:
    from fractions import Fraction

    n_peak = 50
    rng = np.random.default_rng(0)
    peaks = [3221.1122678751262, *rng.uniform(100, 5000, 200)]
    margins = [round(0.02 * i, 2) for i in range(31)]  # (1 + m) · 50 inteiro
    for peak in peaks:
        state = PolicyState(n_active=0, k=float(peak) / n_peak, lead_time=1)
        for margin in margins:
            expected = int((1 + Fraction(repr(margin))) * n_peak)
            n = StaticPeakPolicy(float(peak), margin).required_instances(0, np.zeros(1), state)
            assert n == expected, (peak, margin, n, expected)


def test_estatica_insensivel_a_um_ulp_no_pico() -> None:
    peak = 3047.196533551673
    state = PolicyState(n_active=0, k=peak / 50, lead_time=1)
    for neighbor in (np.nextafter(peak, np.inf), np.nextafter(peak, -np.inf)):
        for margin in (0.0, 0.04, 0.12):
            same = StaticPeakPolicy(peak, margin).required_instances(0, np.zeros(1), state)
            other = StaticPeakPolicy(float(neighbor), margin).required_instances(
                0, np.zeros(1), state
            )
            assert same == other
