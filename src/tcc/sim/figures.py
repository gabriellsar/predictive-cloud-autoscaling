"""Figuras da Fase 4 (seção 3 da spec). Legíveis em A4 e distinguíveis em preto e branco:
cada série tem marcador e estilo de linha próprios, não só cor."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

DPI = 200
#: (rótulo em português, cor, marcador, estilo de linha)
STYLES: dict[str, tuple[str, str, str, str]] = {
    "naive": ("preditiva · naive", "#1f77b4", "o", "-"),
    "moving_average": ("preditiva · média móvel", "#ff7f0e", "s", "--"),
    "seasonal_naive": ("preditiva · sazonal ingênuo", "#2ca02c", "^", "-."),
    "holt_winters": ("preditiva · Holt-Winters", "#9467bd", "D", ":"),
    "arima": ("preditiva · ARIMA", "#d62728", "v", (0, (5, 1))),
    "gru": ("preditiva · GRU", "#17becf", "h", (0, (3, 1, 1, 1, 1, 1))),
    "reactive_hpa": ("reativa (HPA)", "#000000", "P", "-"),
    "static_peak": ("estática no pico", "#7f7f7f", "X", ""),
    "oracle": ("oráculo", "#000000", "*", ""),
}
EPSILON_STYLE = {"color": "0.35", "lw": 0.9, "ls": (0, (2, 2))}


def _key(policy: str, forecaster: str) -> str:
    return forecaster if policy == "predictive" else policy


def _percent(x: float, _: object) -> str:
    return f"{100 * x:g}%"


def plot_pareto(table: pd.DataFrame, lead_time: int, epsilons: list[float], out: Path) -> None:
    """Custo normalizado contra fração de intervalos com violação, no teste."""
    test = table[(table["split"] == "test") & (table["L"] == lead_time)]
    fig, ax = plt.subplots(figsize=(8.5, 5.6))

    for (policy, forecaster), group in test.groupby(["policy", "forecaster"], sort=False):
        label, color, marker, linestyle = STYLES[_key(policy, forecaster)]
        group = group.sort_values("param")
        if policy in ("oracle", "static_peak"):
            point = group[group["param"] == 0.0]
            ax.plot(
                point["V"],
                point["C_norm"],
                marker=marker,
                ms=13 if policy == "oracle" else 10,
                color=color,
                ls="",
                label=f"{label} (m = 0)",
                zorder=6,
            )
            continue
        ax.plot(
            group["V"],
            group["C_norm"],
            marker=marker,
            ms=5.5,
            color=color,
            ls=linestyle,
            lw=1.3,
            label=label + (" (varia u*)" if policy == "reactive_hpa" else " (varia m)"),
            mfc="white" if policy == "reactive_hpa" else color,
            # com a grade fina (passo 0,01), um marcador a cada 0,05 basta para identificar
            # a série em preto e branco sem esconder a linha
            markevery=5,
        )

    # rótulos dos extremos das varreduras, na curva do ARIMA e na reativa
    for policy, forecaster, name in (("predictive", "arima", "m"), ("reactive_hpa", "-", "u*")):
        group = test[(test["policy"] == policy) & (test["forecaster"] == forecaster)]
        group = group.sort_values("param")
        for _, row in group.iloc[[0, -1]].iterrows():
            ax.annotate(
                f"{name} = {row['param']:g}",
                (row["V"], row["C_norm"]),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=7.5,
                color="0.25",
            )

    for epsilon in epsilons:
        ax.axvline(epsilon, **EPSILON_STYLE)
        ax.text(
            epsilon,
            0.99,
            f" ε = {100 * epsilon:g}%",
            transform=ax.get_xaxis_transform(),
            va="top",
            fontsize=8,
            color="0.3",
        )

    ax.set_xscale("symlog", linthresh=0.01, linscale=0.6)
    ax.set_xlim(left=-0.0005)
    ax.xaxis.set_major_formatter(FuncFormatter(_percent))
    ax.set_xticks([0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5])
    ax.set_xlabel(
        "V: fração de intervalos com violação no teste (escala linear até 1%, log depois)"
    )
    ax.set_ylabel("$C_{norm}$: custo relativo ao oráculo")
    ax.set_title(
        f"Custo × violações no teste, L = {lead_time} (melhor: para baixo e para a esquerda)",
        fontsize=11,
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7.5, loc="upper right", framealpha=0.92)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def plot_cost_at_epsilon(points: pd.DataFrame, out: Path) -> None:
    """`C_norm` no teste, no ponto de operação escolhido na validação, para cada ε."""
    data = points[points["policy"] != "oracle"].copy()
    data["key"] = [_key(p, f) for p, f in zip(data["policy"], data["forecaster"])]
    order = [k for k in STYLES if k in set(data["key"])]
    epsilons = sorted(data["epsilon"].unique())
    shades = ["0.75", "0.35"]
    width = 0.8 / len(epsilons)
    x = np.arange(len(order))

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for i, epsilon in enumerate(epsilons):
        rows = data[data["epsilon"] == epsilon].set_index("key")
        for j, key in enumerate(order):
            row = rows.loc[key]
            position = x[j] + i * width - 0.4 + width / 2
            if row["C_norm_test"] == "n/a":
                ax.text(position, 1.0, "n/a", ha="center", va="bottom", fontsize=8, rotation=90)
                continue
            value = float(row["C_norm_test"])
            ax.bar(
                position,
                value,
                width=width,
                color=shades[i % len(shades)],
                edgecolor="black",
                lw=0.6,
                label=f"ε = {100 * epsilon:g}%" if j == 0 else None,
            )
            ax.text(position, value + 0.01, f"{value:.2f}", ha="center", fontsize=7)
            if float(row["V_test"]) > epsilon:
                ax.plot(position, value + 0.07, marker="x", color="#d62728", ms=7, mew=1.6)

    ax.axhline(1.0, color="black", lw=0.9, ls="--")
    ax.text(len(order) - 0.45, 1.005, "oráculo", fontsize=8, va="bottom", ha="right")
    ax.plot([], [], marker="x", color="#d62728", ls="", mew=1.6, label="V no teste > ε")
    ax.set_xticks(x)
    ax.set_xticklabels([STYLES[k][0].replace("preditiva · ", "") for k in order], fontsize=8.5)
    ax.set_ylabel("$C_{norm}$ no teste")
    ax.set_ylim(0.9, max(2.0, ax.get_ylim()[1]))
    ax.set_title(
        "Custo para cumprir o SLO: parâmetro escolhido na validação, medido no teste",
        fontsize=11,
    )
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def plot_rmse_vs_cost(
    points: pd.DataFrame, forecast_metrics: pd.DataFrame, lead_time: int, out: Path
) -> None:
    """RMSE (h = L) no teste contra `C_norm` no ponto de operação, um ponto por previsor."""
    rmse = forecast_metrics[
        (forecast_metrics["split"] == "test") & (forecast_metrics["h"] == lead_time)
    ].set_index("model")["rmse"]
    predictive = points[points["policy"] == "predictive"]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    fills = {0: "full", 1: "none"}
    epsilons = sorted(predictive["epsilon"].unique())
    for i, epsilon in enumerate(epsilons):
        rows = predictive[(predictive["epsilon"] == epsilon) & (predictive["C_norm_test"] != "n/a")]
        for _, row in rows.iterrows():
            _, color, marker, _ = STYLES[row["forecaster"]]
            ax.plot(
                rmse[row["forecaster"]],
                float(row["C_norm_test"]),
                marker=marker,
                color=color,
                ms=9,
                ls="",
                fillstyle=fills[i % 2],
                mew=1.5,
            )
    # legenda em vez de rótulos de texto, que se sobrepõem quando os pontos coincidem
    for forecaster in dict.fromkeys(predictive["forecaster"]):
        label, color, marker, _ = STYLES[forecaster]
        ax.plot([], [], marker=marker, color=color, ls="", ms=8, label=label)
    for i, epsilon in enumerate(epsilons):
        ax.plot(
            [],
            [],
            marker="o",
            color="0.3",
            ls="",
            ms=8,
            fillstyle=fills[i % 2],
            label=f"ponto de operação ε = {100 * epsilon:g}%",
        )
    ax.set_xlabel(f"RMSE da previsão no teste, h = {lead_time} (máquinas equivalentes)")
    ax.set_ylabel("$C_{norm}$ no teste, no ponto de operação")
    ax.set_title("Menor erro de previsão leva a menor custo?", fontsize=11)
    ax.legend(fontsize=7.5, loc="upper center", framealpha=0.92)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
