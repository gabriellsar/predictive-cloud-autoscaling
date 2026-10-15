"""Métricas de erro de previsão (seção 4 da spec da Fase 2).

O **viés** e a **taxa de subestimação** estão aqui junto com MAE/RMSE/MAPE porque, na
alocação, subestimar e superestimar têm custos diferentes: subestimar vira violação de
SLA, superestimar vira capacidade ociosa.
"""

from __future__ import annotations

import numpy as np


def mae(y: np.ndarray, y_hat: np.ndarray) -> float:
    return float(np.mean(np.abs(y - y_hat)))


def rmse(y: np.ndarray, y_hat: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - y_hat) ** 2)))


def mape(y: np.ndarray, y_hat: np.ndarray, eps: float) -> tuple[float, float]:
    """MAPE em %, mascarando `y` próximo de zero. Devolve (mape, cobertura da máscara)."""
    mask = np.abs(y) > eps
    coverage = float(mask.mean())
    if not mask.any():
        return float("nan"), coverage
    return float(np.mean(np.abs((y[mask] - y_hat[mask]) / y[mask])) * 100.0), coverage


def bias(y: np.ndarray, y_hat: np.ndarray) -> float:
    """Erro médio com sinal: positivo significa que o modelo superestima."""
    return float(np.mean(y_hat - y))


def under_rate(y: np.ndarray, y_hat: np.ndarray) -> float:
    """Fração de origens em que a previsão ficou abaixo do valor real."""
    return float(np.mean(y_hat < y))


def all_metrics(y: np.ndarray, y_hat: np.ndarray, eps: float) -> dict[str, float]:
    """Todas as métricas da spec, na ordem em que vão para a tabela."""
    value, coverage = mape(y, y_hat, eps)
    return {
        "mae": mae(y, y_hat),
        "rmse": rmse(y, y_hat),
        "mape": value,
        "mape_coverage": coverage,
        "bias": bias(y, y_hat),
        "under_rate": under_rate(y, y_hat),
    }
