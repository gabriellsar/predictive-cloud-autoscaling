"""Verificações de sanidade do simulador (seção 6 da spec da Fase 3).

Gera `results/sanity.md` e `results/figures/sanity_policies.png`. O objetivo não é
produzir o experimento da Fase 4, e sim deixar **visível** o que o simulador faz, para
revisão antes de qualquer varredura de parâmetros.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tcc.config import load_config  # noqa: E402
from tcc.data import load_series, split_series  # noqa: E402
from tcc.data.paths import resolve  # noqa: E402
from tcc.eval.allocation import capacity_per_instance  # noqa: E402
from tcc.forecast.baselines import NaiveForecaster  # noqa: E402
from tcc.sim import (  # noqa: E402
    OraclePolicy,
    PredictivePolicy,
    ReactiveHPAPolicy,
    SimResult,
    StaticPeakPolicy,
    simulate,
)

SPLIT = "test"


def _markdown_table(table: pd.DataFrame) -> str:
    """Tabela em Markdown sem depender do `tabulate` (que não está no pyproject)."""
    header = "| " + " | ".join(str(c) for c in table.columns) + " |"
    rule = "|" + "---|" * len(table.columns)
    rows = [
        "| " + " | ".join(f"{v:g}" if isinstance(v, float) else str(v) for v in row) + " |"
        for row in table.itertuples(index=False, name=None)
    ]
    return "\n".join([header, rule, *rows])


def _setup(cfg: dict[str, Any]) -> tuple[np.ndarray, slice, float, dict[str, Any]]:
    series = load_series(cfg)
    splits = split_series(series, cfg)
    demand = series["demand_cpu"].to_numpy(dtype=float)
    train = demand[splits["train"]]
    k = capacity_per_instance(train, int(cfg["sim"]["n_peak"]))
    return demand, splits[SPLIT], k, {"train": train, "splits": splits}


def run_sanity(cfg: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, SimResult], float]:
    """Roda as políticas no teste e devolve a tabela, os resultados e `k`."""
    demand, split, k, extra = _setup(cfg)
    sim_cfg = cfg["sim"]
    lead_time = int(sim_cfg["lead_time"])
    c = float(sim_cfg["cost_per_instance"])
    n_min = int(sim_cfg["n_min"])
    train_peak = float(extra["train"].max())

    forecaster = NaiveForecaster()
    forecaster.fit(extra["train"])

    def run(policy: Any, cost_oracle: float | None = None) -> SimResult:
        return simulate(
            demand,
            split,
            policy,
            k=k,
            lead_time=lead_time,
            c=c,
            n_min=n_min,
            cost_oracle=cost_oracle,
        )

    oracle = run(OraclePolicy(demand, margin=0.0))
    cost_oracle = oracle.metrics["C"]
    oracle = run(OraclePolicy(demand, margin=0.0), cost_oracle)

    results: dict[str, SimResult] = {"oracle (m = 0)": oracle}
    results["static_peak (m = 0)"] = run(StaticPeakPolicy(train_peak, margin=0.0), cost_oracle)
    for target in sim_cfg.get("sanity_hpa_targets", sim_cfg["hpa_targets"]):
        policy = ReactiveHPAPolicy(
            target_utilization=float(target),
            tolerance=float(sim_cfg["hpa_tolerance"]),
            scale_down_window=int(sim_cfg["hpa_scale_down_window"]),
        )
        results[f"reactive_hpa (u* = {target})"] = run(policy, cost_oracle)
    results["predictive naive (m = 0)"] = run(PredictivePolicy(forecaster, 0.0), cost_oracle)

    rows = [{"política": name, **result.metrics} for name, result in results.items()]
    table = pd.DataFrame(rows)
    return table, results, k


def plot_policies(
    demand: np.ndarray,
    split: slice,
    results: dict[str, SimResult],
    k: float,
    interval: int,
    out: Path,
    names: list[str] | None = None,
) -> None:
    """Demanda contra capacidade alocada, por política, no trecho inicial do teste."""
    names = names or list(results)
    actual = demand[split]
    n_points = min(2 * 86400 // interval, len(actual))
    hours = np.arange(n_points) * interval / 3600.0

    fig, axes = plt.subplots(len(names), 1, figsize=(11, 2.4 * len(names)), sharex=True)
    for ax, name in zip(np.atleast_1d(axes), names):
        capacity = k * results[name].n[:n_points]
        demand_window = actual[:n_points]
        ax.plot(hours, demand_window, color="black", lw=1.1, label="demanda $d_t$")
        ax.step(hours, capacity, where="post", color="#1f77b4", lw=1.2, label="capacidade $k n_t$")
        ax.fill_between(
            hours,
            demand_window,
            capacity,
            where=demand_window > capacity,
            color="#d62728",
            alpha=0.35,
            step="post",
            label="violação",
        )
        metrics = results[name].metrics
        ax.set_title(
            f"{name} — C = {metrics['C']:.0f}, V = {metrics['V']:.3f}, O = {metrics['O']:.3f}",
            fontsize=10,
        )
        ax.set_ylabel("máquinas eq.", fontsize=9)
        ax.margins(x=0.01)
    np.atleast_1d(axes)[0].legend(ncol=3, fontsize=8, loc="upper right")
    np.atleast_1d(axes)[-1].set_xlabel("horas desde o início do conjunto de teste")
    fig.suptitle("O que cada política faz com a capacidade alocada", fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def write_sanity_report(cfg: dict[str, Any]) -> Path:
    """Escreve `results/sanity.md` com a tabela e as observações pedidas no G2."""
    demand, split, k, extra = _setup(cfg)
    table, results, _ = run_sanity(cfg)
    train_peak = float(extra["train"].max())
    test_peak = float(demand[split].max())

    figures_dir = resolve("results/figures")
    figures_dir.mkdir(parents=True, exist_ok=True)
    figure = figures_dir / "sanity_policies.png"
    plot_policies(
        demand,
        split,
        results,
        k,
        int(cfg["data"]["interval_seconds"]),
        figure,
        names=[
            "oracle (m = 0)",
            "static_peak (m = 0)",
            "reactive_hpa (u* = 0.7)",
            "predictive naive (m = 0)",
        ],
    )

    tables_dir = resolve("results/tables")
    tables_dir.mkdir(parents=True, exist_ok=True)
    table.round(4).to_csv(tables_dir / "sanity_policies.csv", index=False)

    reactive = table[table["política"].str.startswith("reactive_hpa")]
    oracle_row = table.iloc[0]

    # Afirmações sobre o oráculo e a reativa precisam sair dos números, não do texto.
    feasible = table[(table["V"] == 0) & (table["política"] != oracle_row["política"])]
    feasible_min = float(feasible["C"].min()) if len(feasible) else float("nan")
    feasible_max = float(feasible["C"].max()) if len(feasible) else float("nan")
    oracle_is_cheapest_feasible = bool(len(feasible) == 0 or oracle_row["C"] <= feasible_min)
    below = table[table["C"] < oracle_row["C"]]
    cheaper_than_oracle = str(below.iloc[0]["política"]) if len(below) else ""
    cheapest_cost = float(below.iloc[0]["C"]) if len(below) else float("nan")
    cheapest_violation = float(below.iloc[0]["V"]) if len(below) else float("nan")
    reactive_monotonic = bool(
        (reactive.sort_values("política")["V"].diff().dropna() >= -1e-12).all()
    )
    static_row = table[table["política"].str.startswith("static_peak")].iloc[0]
    predictive_row = table[table["política"].str.startswith("predictive")].iloc[0]

    lines = [
        "# Verificações de sanidade do simulador (G2)",
        "",
        f"Conjunto: **{SPLIT}** ({len(demand[split])} intervalos de "
        f"{cfg['data']['interval_seconds']} s) · "
        f"`L = {cfg['sim']['lead_time']}` · `n_min = {cfg['sim']['n_min']}` · "
        f"`c = {cfg['sim']['cost_per_instance']}`",
        "",
        f"Capacidade por instância: `k = max(d_train) / n_peak = {train_peak:.1f} / "
        f"{cfg['sim']['n_peak']} = {k:.3f}` máquinas equivalentes. "
        f"Pico do teste: {test_peak:.1f} ({test_peak / train_peak:.3f} do pico do treino).",
        "",
        "## Tabela",
        "",
        _markdown_table(table.round(4)),
        "",
        "## O que cada verificação mostra",
        "",
        f"- **Oráculo:** `V = {oracle_row['V']:.4f}` e `U = {oracle_row['U']:.4f}`, como exige a "
        f"spec, com `C = {oracle_row['C']:.0f}`. Ele é o **menor custo entre as políticas que "
        f"não violam** ({'confirmado' if oracle_is_cheapest_feasible else 'NÃO confirmado'}: "
        f"as demais com `V = 0` custam de {feasible_min:.0f} a {feasible_max:.0f}). "
        "Atenção ao que ele **não** é: "
        + (
            f"a política `{cheaper_than_oracle}` custa {cheapest_cost:.0f}, menos que o oráculo, "
            f"mas violando em {cheapest_violation:.1%} dos intervalos. O oráculo é o piso do "
            "custo *sob a restrição de nunca violar*, não o piso absoluto."
            if cheaper_than_oracle
            else "nenhuma política ficou abaixo dele no custo."
        ),
        f"- **static_peak:** ociosidade alta (`O = {static_row['O']:.3f}`) e custo "
        f"{static_row['C_norm']:.2f}× o do oráculo. "
        + (
            f"`V = {static_row['V']:.4f} > 0` porque o pico do teste ({test_peak:.0f}) "
            f"passa do pico do treino ({train_peak:.0f}): dimensionar pelo passado não "
            "protege contra um pico maior no futuro."
            if static_row["V"] > 0
            else f"`V = {static_row['V']:.4f}`, porque o pico do teste ({test_peak:.0f}) "
            f"não passa do pico do treino ({train_peak:.0f})."
        ),
        "- **reactive_hpa:** decide em `τ` com `d[τ]`, mas a decisão só vale em `τ + L`, então "
        "só não viola enquanto a folga `1/u* − 1` cobrir a variação da demanda em um intervalo "
        f"de {cfg['data']['interval_seconds']} s. As violações crescem de forma monótona com "
        f"`u*` ({'monotonicidade confirmada' if reactive_monotonic else 'ATENÇÃO: não monótono'}"
        f"), de {reactive['V'].min():.4f} a {reactive['V'].max():.4f}:",
        "",
        "  | `u*` | V | C | C_norm | changes |",
        "  |---|---|---|---|---|",
    ]
    for _, row in reactive.iterrows():
        target = row["política"].split("= ")[1].rstrip(")")
        lines.append(
            f"  | {target} | {row['V']:.4f} | {row['C']:.0f} | "
            f"{row['C_norm']:.3f} | {row['changes']:.0f} |"
        )
    lines += [
        "",
        f"- **predictive com `naive` (m = 0):** `V = {predictive_row['V']:.4f}` e "
        f"`C_norm = {predictive_row['C_norm']:.3f}`. Comportamento próximo do reativo, o que "
        "faz sentido: os dois decidem olhando para a última observação. A diferença é que a "
        "política preditiva não tem tolerância nem janela de estabilização, então ela troca "
        f"de tamanho muito mais vezes ({predictive_row['changes']:.0f} alterações).",
        "",
        "## Figura",
        "",
        "![Políticas](figures/sanity_policies.png)",
        "",
        "A faixa vermelha marca os intervalos em que `d_t > k·n_t`. É o que o simulador conta "
        "em `V`.",
        "",
        "## Simplificações do modelo",
        "",
        "- Aumentos e reduções sofrem o **mesmo** atraso `L`; na prática, desligar é imediato.",
        "- **Não há custo de troca**: `changes` é medido, mas não entra em `C`.",
        "- Uma instância só, homogênea, de capacidade `k`; nada de tipos ou de posicionamento.",
        "- A demanda é independente da alocação: violar não gera fila nem demanda represada.",
        "",
    ]
    out = resolve("results") / "sanity.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[simulação] relatório de sanidade em {out}")
    return out


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Fase 3: verificações de sanidade.")
    parser.add_argument("--config", default=None)
    args = parser.parse_args(argv)
    write_sanity_report(load_config(args.config))


if __name__ == "__main__":
    main()
