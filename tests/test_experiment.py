"""Testes da Fase 4: escolha do ponto de operação sem olhar o teste."""

from __future__ import annotations

import pandas as pd

from tcc.sim.experiment import TABLE_COLUMNS, operating_points


def _row(param: float, split: str, C: float, V: float, L: int = 1) -> dict:
    return {
        "policy": "predictive",
        "forecaster": "naive",
        "param_name": "m",
        "param": param,
        "L": L,
        "split": split,
        "C": C,
        "C_norm": C / 100,
        "V": V,
        "U": 0.0,
        "O": 0.0,
        "changes": 0.0,
    }


def _table(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


def test_escolhe_o_parametro_mais_barato_que_cumpre_epsilon_na_validacao() -> None:
    table = _table(
        [
            _row(0.0, "val", 100, 0.30),
            _row(0.1, "val", 110, 0.04),  # mais barato com V <= 5%
            _row(0.2, "val", 120, 0.00),
            _row(0.0, "test", 101, 0.31),
            _row(0.1, "test", 111, 0.06),
            _row(0.2, "test", 121, 0.00),
        ]
    )
    points = operating_points(table, [0.05], lead_time=1)
    assert points["param"].iloc[0] == 0.1
    # as métricas reportadas são as do teste, mesmo violando ε no teste
    assert points["C_norm_test"].iloc[0] == 1.11
    assert points["V_test"].iloc[0] == 0.06


def test_o_teste_nao_influencia_a_escolha() -> None:
    """Trocar os números do teste não pode mudar o parâmetro escolhido."""
    base = [_row(0.0, "val", 100, 0.30), _row(0.1, "val", 110, 0.04)]
    good_test = _table(base + [_row(0.0, "test", 100, 0.0), _row(0.1, "test", 110, 0.0)])
    bad_test = _table(base + [_row(0.0, "test", 100, 0.9), _row(0.1, "test", 110, 0.9)])
    a = operating_points(good_test, [0.05], lead_time=1)
    b = operating_points(bad_test, [0.05], lead_time=1)
    assert a["param"].iloc[0] == b["param"].iloc[0] == 0.1


def test_sem_parametro_viavel_vira_na() -> None:
    table = _table([_row(0.0, "val", 100, 0.30), _row(0.0, "test", 100, 0.30)])
    points = operating_points(table, [0.01], lead_time=1)
    assert points["param"].iloc[0] == "n/a"
    assert points["C_norm_test"].iloc[0] == "n/a"


def test_so_usa_o_lead_time_principal() -> None:
    table = _table(
        [
            _row(0.0, "val", 100, 0.00, L=2),
            _row(0.0, "test", 100, 0.00, L=2),
            _row(0.5, "val", 150, 0.00, L=1),
            _row(0.5, "test", 150, 0.00, L=1),
        ]
    )
    points = operating_points(table, [0.05], lead_time=1)
    assert points["param"].iloc[0] == 0.5
