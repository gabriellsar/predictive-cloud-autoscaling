"""Figuras da Fase 1 (seção 6 da spec). Rótulos em português, eixos com unidade.

A autocorrelação e a correlação CPU × memória são calculadas **só no treino**: elas
embasam escolhas de modelagem (período sazonal, entrada multivariada) e, pela regra de
ausência de vazamento, não podem olhar validação nem teste.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.tsa.stattools import acf  # noqa: E402

from tcc.data.paths import resolve  # noqa: E402
from tcc.data.series import load_series, split_series  # noqa: E402

SPLIT_LABELS = {"train": "treino", "val": "validação", "test": "teste"}
DPI = 150


def _figures_dir() -> Path:
    path = resolve("results/figures")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _days(series: pd.DataFrame) -> np.ndarray:
    """Eixo de tempo em dias desde o início do rastro."""
    return series["bucket_start"].to_numpy() / 86400.0


def plot_series_full(series: pd.DataFrame, splits: dict[str, slice], out: Path) -> None:
    """Série completa de `demand_cpu`, com as três divisões marcadas."""
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(_days(series), series["demand_cpu"], lw=0.7, color="#1f77b4")

    colors = {"train": "#2ca02c", "val": "#ff7f0e", "test": "#d62728"}
    for name, sl in splits.items():
        start, stop = sl.start, sl.stop
        ax.axvspan(
            series["bucket_start"].iloc[start] / 86400.0,
            series["bucket_start"].iloc[stop - 1] / 86400.0,
            color=colors[name],
            alpha=0.08,
        )
        middle = (start + stop) / 2
        ax.text(
            series["bucket_start"].iloc[int(middle)] / 86400.0,
            0.97,
            SPLIT_LABELS[name],
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=9,
            color=colors[name],
        )
        if start > 0:
            ax.axvline(series["bucket_start"].iloc[start] / 86400.0, color="0.4", lw=0.8, ls="--")

    ax.set_xlabel("tempo (dias desde o início do rastro)")
    ax.set_ylabel("demanda $d_t$ (máquinas equivalentes)")
    ax.set_title(
        "Demanda de CPU do cluster em intervalos de 5 min, com a divisão cronológica",
        fontsize=11,
    )
    ax.margins(x=0.01)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def plot_series_day(series: pd.DataFrame, interval: int, out: Path, day: int = 2) -> None:
    """Um dia ampliado, para ver a variação intradiária."""
    per_day = 86400 // interval
    start = day * per_day
    stop = min(start + per_day, len(series))
    window = series.iloc[start:stop]
    hours = (window["bucket_start"] - window["bucket_start"].iloc[0]) / 3600.0

    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(hours, window["demand_cpu"], lw=1.2, color="#1f77b4", label="CPU")
    ax.plot(hours, window["demand_mem"], lw=1.2, color="#9467bd", ls="--", label="memória")
    ax.set_xlabel(f"hora dentro do dia {day} do rastro")
    ax.set_ylabel("demanda $d_t$ (máquinas equivalentes)")
    ax.set_title(f"Variação intradiária da demanda (dia {day}, intervalos de 5 min)", fontsize=11)
    ax.set_xticks(range(0, 25, 3))
    ax.legend(fontsize=9)
    ax.margins(x=0.01)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def plot_acf_cpu(train: pd.DataFrame, season_period: int, out: Path) -> None:
    """Autocorrelação até 2 dias de *lags*, com marcação do período sazonal."""
    nlags = min(2 * season_period, len(train) - 2)
    values = acf(train["demand_cpu"].to_numpy(), nlags=nlags, missing="conservative")

    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(np.arange(len(values)), values, lw=0.9, color="#1f77b4")
    ax.axhline(0.0, color="0.5", lw=0.8)
    for multiple in (1, 2):
        lag = multiple * season_period
        if lag < len(values):
            ax.axvline(lag, color="#d62728", lw=0.9, ls="--")
            ax.text(
                lag,
                0.97,
                f"{multiple} dia{'s' if multiple > 1 else ''} ({lag} intervalos)",
                transform=ax.get_xaxis_transform(),
                rotation=90,
                ha="right",
                va="top",
                fontsize=8,
                color="#d62728",
            )
    ax.set_xlabel("defasagem (intervalos de 5 min)")
    ax.set_ylabel("autocorrelação")
    ax.set_title("Autocorrelação da demanda de CPU (só no treino)", fontsize=11)
    ax.margins(x=0.01)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def plot_cpu_vs_mem(train: pd.DataFrame, out: Path) -> float:
    """Dispersão CPU × memória. Devolve a correlação de Pearson (calculada no treino)."""
    valid = train[["demand_cpu", "demand_mem"]].dropna()
    r = float(valid["demand_cpu"].corr(valid["demand_mem"]))

    fig, ax = plt.subplots(figsize=(5, 4.6))
    ax.scatter(valid["demand_cpu"], valid["demand_mem"], s=6, alpha=0.25, color="#1f77b4")
    ax.set_xlabel("demanda de CPU (máquinas equivalentes)")
    ax.set_ylabel("demanda de memória (máquinas equivalentes)")
    ax.set_title(f"CPU × memória no treino (Pearson $r$ = {r:.3f})", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return r


def make_figures(cfg: dict[str, Any]) -> list[Path]:
    """Gera as quatro figuras da Fase 1 e devolve os caminhos."""
    series = load_series(cfg)
    splits = split_series(series, cfg)
    train = series.iloc[splits["train"]]
    out_dir = _figures_dir()
    interval = int(cfg["data"]["interval_seconds"])

    paths = [
        out_dir / "series_full.png",
        out_dir / "series_day.png",
        out_dir / "acf_cpu.png",
        out_dir / "cpu_vs_mem.png",
    ]
    plot_series_full(series, splits, paths[0])
    plot_series_day(series, interval, paths[1])
    plot_acf_cpu(train, int(cfg["forecast"]["season_period"]), paths[2])
    r = plot_cpu_vs_mem(train, paths[3])
    print(f"[dados] figuras em {out_dir} (correlação CPU x memória no treino: r = {r:.3f})")
    return paths
