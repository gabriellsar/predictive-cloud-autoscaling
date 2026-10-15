"""Figuras da Fase 2 (seção 6 da spec). Rótulos em português."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tcc.data.paths import resolve  # noqa: E402

DPI = 150
MODEL_COLORS = {
    "naive": "#1f77b4",
    "moving_average": "#ff7f0e",
    "seasonal_naive": "#2ca02c",
    "holt_winters": "#9467bd",
    "arima": "#d62728",
}


def _figures_dir() -> Path:
    path = resolve("results/figures")
    path.mkdir(parents=True, exist_ok=True)
    return path


def plot_forecast_vs_actual(
    predictions: dict[tuple[str, int, str], tuple[np.ndarray, np.ndarray]],
    interval: int,
    out: Path,
    h: int = 1,
    days: int = 2,
) -> None:
    """Dois dias do teste, horizonte `h`: real contra cada previsor."""
    models = [m for (m, hh, split) in predictions if hh == h and split == "test"]
    actual = predictions[(models[0], h, "test")][0]
    n = min(days * 86400 // interval, len(actual))
    hours = np.arange(n) * interval / 3600.0

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(hours, actual[:n], color="black", lw=1.8, label="real", zorder=5)
    for model in models:
        ax.plot(
            hours,
            predictions[(model, h, "test")][1][:n],
            color=MODEL_COLORS.get(model),
            lw=0.9,
            alpha=0.75,
            label=model,
        )

    ax.set_xlabel("horas desde o início do conjunto de teste")
    ax.set_ylabel("demanda $d_t$ (máquinas equivalentes)")
    ax.set_title(
        f"Previsão contra demanda real no teste (h = {h}, {days} dias, intervalos de 5 min)",
        fontsize=11,
    )
    ax.set_xticks(np.arange(0, days * 24 + 1, 6))
    ax.legend(ncol=6, fontsize=9, loc="upper center")
    ax.margins(x=0.01)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def plot_rmse_by_model(metrics: pd.DataFrame, out: Path) -> None:
    """RMSE no teste, por modelo e horizonte."""
    table = (
        metrics[metrics["split"] == "test"]
        .pivot(index="model", columns="h", values="rmse")
        .sort_values(by=list(sorted(metrics["h"].unique()))[0])
    )
    horizons = list(table.columns)
    models = list(table.index)
    x = np.arange(len(models))
    width = 0.8 / len(horizons)

    fig, ax = plt.subplots(figsize=(9, 4.4))
    for i, h in enumerate(horizons):
        ax.bar(
            x + i * width - 0.4 + width / 2,
            table[h].to_numpy(),
            width=width,
            label=f"h = {h}",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=9)
    ax.set_xlabel("previsor")
    ax.set_ylabel("RMSE (máquinas equivalentes)")
    ax.set_title("Erro de previsão no teste, por modelo e horizonte", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def make_forecast_figures(
    cfg: dict[str, Any],
    metrics: pd.DataFrame,
    predictions: dict[tuple[str, int, str], tuple[np.ndarray, np.ndarray]],
) -> list[Path]:
    """Gera as duas figuras da Fase 2 e devolve os caminhos."""
    out_dir = _figures_dir()
    paths = [out_dir / "forecast_vs_actual.png", out_dir / "rmse_by_model.png"]
    horizons = sorted({h for (_, h, _) in predictions})
    plot_forecast_vs_actual(
        predictions, int(cfg["data"]["interval_seconds"]), paths[0], horizons[0]
    )
    plot_rmse_by_model(metrics, paths[1])
    print(f"[previsão] figuras em {out_dir}")
    return paths
