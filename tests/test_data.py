"""Testes da Fase 1: agregação, grade regular e divisão cronológica."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from tcc.config import load_config
from tcc.data import build_series, load_series, split_series
from tcc.data.build import _to_regular_grid, check_long_fills_in_train
from tcc.data.paths import processed_path

# Duas máquinas, intervalos de 300 s. As médias abaixo são conferidas à mão no teste:
#   bucket 0: m_1 -> (10 + 30) / 2 = 20 ; m_2 -> (50 + 70) / 2 = 60 ; cluster = 40
#   bucket 1: ambas em 100 (a amostra 150, fora de [0, 100], e a vazia são ignoradas)
#   bucket 2: sem dado, lacuna de 1 intervalo -> interpolada
#   bucket 3: ambas em 0
#   buckets 4 a 7: sem dado, lacuna de 4 intervalos -> fica NaN
#   bucket 8: só m_1 em 50 -> cobertura 0,5 e média do cluster 50
SYNTHETIC_ROWS = [
    ("m_1", 0, "10", "40"),
    ("m_1", 100, "30", "40"),
    ("m_2", 0, "50", "60"),
    ("m_2", 150, "70", "60"),
    ("m_1", 300, "100", "50"),
    ("m_1", 320, "150", "50"),  # CPU fora de [0, 100]: ignorada
    ("m_2", 310, "100", "50"),
    ("m_2", 330, "", "50"),  # CPU nula: ignorada
    ("m_1", 900, "0", "30"),
    ("m_2", 950, "0", "30"),
    ("m_1", 2400, "50", "50"),
]


@pytest.fixture
def synthetic_cfg(tmp_path: Path) -> dict[str, Any]:
    """Configuração real, com os caminhos de dados redirecionados para um diretório temporário."""
    raw = tmp_path / "raw" / "machine_usage.csv"
    raw.parent.mkdir(parents=True)
    lines = [f"{machine},{ts},{cpu},{mem},,,1.0,1.0,5" for machine, ts, cpu, mem in SYNTHETIC_ROWS]
    raw.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cfg = load_config()
    cfg["data"] = {
        **cfg["data"],
        "source": "sintetico",
        "raw_path": str(raw),
        "interim_dir": str(tmp_path / "interim"),
        "processed_dir": str(tmp_path / "processed"),
        # Estes testes cobrem a definição base de demanda: as duas regras opcionais têm
        # testes próprios e não devem variar conforme o que estiver em configs/v0.toml.
        "min_coverage": 0.0,
        "trim_leading_missing": False,
        "long_gap_fill": "none",
    }
    return cfg


@pytest.fixture
def synthetic_series(synthetic_cfg: dict[str, Any]) -> pd.DataFrame:
    build_series(synthetic_cfg["data"]["raw_path"], processed_path(synthetic_cfg), synthetic_cfg)
    return load_series(synthetic_cfg)


def test_demanda_por_bucket_confere_com_a_media_feita_a_mao(synthetic_series: pd.DataFrame) -> None:
    series = synthetic_series
    assert len(series) == 9
    # d_t = (média do cluster / 100) * N, com N = 2 máquinas distintas no rastro.
    assert series["demand_cpu"].iloc[0] == pytest.approx(40 / 100 * 2)
    assert series["demand_cpu"].iloc[1] == pytest.approx(100 / 100 * 2)
    assert series["demand_cpu"].iloc[3] == pytest.approx(0.0)
    assert series["demand_cpu"].iloc[8] == pytest.approx(50 / 100 * 2)
    # memória do bucket 0: m_1 -> 40, m_2 -> 60, cluster -> 50
    assert series["demand_mem"].iloc[0] == pytest.approx(50 / 100 * 2)


def test_cobertura_e_maquinas_reportando(synthetic_series: pd.DataFrame) -> None:
    series = synthetic_series
    assert series["n_machines_reporting"].tolist() == [2, 2, 0, 2, 0, 0, 0, 0, 1]
    assert series["coverage"].iloc[0] == pytest.approx(1.0)
    assert series["coverage"].iloc[8] == pytest.approx(0.5)
    assert series["coverage"].iloc[2] == pytest.approx(0.0)


def test_lacuna_curta_interpolada_e_lacuna_longa_preservada(
    synthetic_series: pd.DataFrame,
) -> None:
    series = synthetic_series
    # Lacuna de 1 intervalo entre 2,0 e 0,0: interpolada para 1,0 e marcada como preenchida.
    assert series["filled"].iloc[2]
    assert series["demand_cpu"].iloc[2] == pytest.approx(1.0)
    # Lacuna de 4 intervalos (> max_fill_gap = 3): fica NaN e não é marcada como preenchida.
    assert series["demand_cpu"].iloc[4:8].isna().all()
    assert not series["filled"].iloc[4:8].any()


def test_sem_nan_fora_das_lacunas_sinalizadas(synthetic_series: pd.DataFrame) -> None:
    series = synthetic_series
    no_data = series["n_machines_reporting"] == 0
    big_gap = no_data & ~series["filled"]
    assert series.loc[~big_gap, "demand_cpu"].notna().all()
    assert series.loc[~big_gap, "demand_mem"].notna().all()


def test_grade_de_tempo_crescente_e_com_espacamento_constante(
    synthetic_series: pd.DataFrame, synthetic_cfg: dict[str, Any]
) -> None:
    series = synthetic_series
    interval = synthetic_cfg["data"]["interval_seconds"]
    diffs = series["bucket_start"].diff().dropna().unique()
    assert diffs.tolist() == [interval]
    assert series["bucket_start"].is_monotonic_increasing
    assert series.index.tolist() == list(range(len(series)))


def test_split_series_cobre_a_serie_sem_sobreposicao(synthetic_cfg: dict[str, Any]) -> None:
    df = pd.DataFrame({"demand_cpu": range(100)})
    splits = split_series(df, synthetic_cfg)
    assert [splits[name].start for name in ("train", "val", "test")] == [0, 60, 80]
    assert splits["test"].stop == len(df)
    # ordem cronológica, sem buracos e sem sobreposição
    assert splits["train"].stop == splits["val"].start
    assert splits["val"].stop == splits["test"].start
    total = sum(len(df.iloc[splits[name]]) for name in ("train", "val", "test"))
    assert total == len(df)


def test_split_series_rejeita_fracoes_que_nao_somam_um(synthetic_cfg: dict[str, Any]) -> None:
    synthetic_cfg["data"]["split"] = {"train": 0.6, "val": 0.2, "test": 0.1}
    with pytest.raises(ValueError, match="somam"):
        split_series(pd.DataFrame({"x": range(100)}), synthetic_cfg)


def test_split_series_rejeita_serie_curta(synthetic_cfg: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="curta"):
        split_series(pd.DataFrame({"x": range(3)}), synthetic_cfg)


def test_load_series_exige_o_parquet(synthetic_cfg: dict[str, Any]) -> None:
    with pytest.raises(FileNotFoundError, match="make data"):
        load_series(synthetic_cfg)


def test_divisao_do_rastro_real_respeita_as_fracoes() -> None:
    """Confere as frações na série real, se ela já tiver sido construída."""
    cfg = load_config()
    if not processed_path(cfg).exists():
        pytest.skip("série real ainda não construída (rode `make data`)")
    series = load_series(cfg)
    splits = split_series(series, cfg)
    fractions = cfg["data"]["split"]
    assert len(series.iloc[splits["train"]]) == math.floor(len(series) * fractions["train"])
    assert splits["test"].stop == len(series)


def _grade(n_reporting: list[int], **kwargs: Any) -> pd.DataFrame:
    raw = pd.DataFrame(
        {
            "bucket": range(len(n_reporting)),
            "cpu_util_mean": [50.0] * len(n_reporting),
            "mem_util_mean": [25.0] * len(n_reporting),
            "n_machines_reporting": n_reporting,
        }
    )
    return _to_regular_grid(raw, n_machines=10, interval=300, max_fill_gap=3, **kwargs)


def test_min_coverage_trata_bucket_pouco_coberto_como_lacuna() -> None:
    # O primeiro bucket tem 1 de 10 máquinas: a média vezes N seria uma extrapolação ruidosa.
    out = _grade([1, 10, 10, 10], min_coverage=0.5)
    assert out["demand_cpu"].isna().iloc[0]
    assert out["demand_cpu"].iloc[1:].notna().all()
    assert len(out) == 4


def test_trim_leading_missing_descarta_o_trecho_inicial_invalido() -> None:
    out = _grade([1, 10, 10, 10], min_coverage=0.5, trim_leading_missing=True)
    assert len(out) == 3
    assert out["demand_cpu"].notna().all()
    assert out["bucket_start"].iloc[0] == 300  # o tempo absoluto é preservado


# --- preenchimento sazonal das lacunas longas ------------------------------------------


def _grade_com_lacuna(values: list[float], **kwargs: Any) -> pd.DataFrame:
    """Grade com N = 100 máquinas, para que a demanda seja igual à utilização média."""
    present = [t for t, v in enumerate(values) if not math.isnan(v)]
    raw = pd.DataFrame(
        {
            "bucket": present,
            "cpu_util_mean": [values[t] for t in present],
            "mem_util_mean": [values[t] / 2 for t in present],
            "n_machines_reporting": [100] * len(present),
        }
    )
    return _to_regular_grid(raw, n_machines=100, interval=300, max_fill_gap=3, **kwargs)


NAN = float("nan")


def test_preenchimento_sazonal_confere_com_a_conta_feita_a_mao() -> None:
    # s = 6. O dia anterior da lacuna t = 7..10 é t = 1..4; as bordas são t = 6 e t = 11.
    #   correção na borda esquerda: d[6] − d[0] = 12 − 10 = 2
    #   correção na borda direita:  d[11] − d[5] = 70 − 60 = 10
    #   pesos 1/5 .. 4/5: t = 7 -> 20 + 2 + 8·0,2 = 23,6 ; t = 10 -> 50 + 2 + 8·0,8 = 58,4
    values = [10, 20, 30, 40, 50, 60, 12, NAN, NAN, NAN, NAN, 70, 15, 25]
    out = _grade_com_lacuna(values, long_gap_fill="seasonal", season_period=6)
    assert out["demand_cpu"].iloc[7:11].tolist() == pytest.approx([23.6, 35.2, 46.8, 58.4])
    # A memória segue a mesma regra sobre a própria série (metade da CPU aqui).
    assert out["demand_mem"].iloc[7:11].tolist() == pytest.approx([11.8, 17.6, 23.4, 29.2])
    assert out["filled"].tolist() == [False] * 7 + [True] * 4 + [False] * 3
    # As bordas e o resto da série não mudam.
    assert out["demand_cpu"].iloc[[6, 11]].tolist() == [12, 70]


def test_preenchimento_sazonal_sem_dia_anterior_deixa_a_lacuna() -> None:
    # A lacuna t = 2..5 não tem um dia inteiro antes dela (s = 6): fica NaN.
    values = [10, 20, NAN, NAN, NAN, NAN, 12, 22, 32, 42]
    out = _grade_com_lacuna(values, long_gap_fill="seasonal", season_period=6)
    assert out["demand_cpu"].iloc[2:6].isna().all()
    assert not out["filled"].any()


def test_preenchimento_none_preserva_a_definicao_original() -> None:
    values = [10, 20, 30, 40, 50, 60, 12, NAN, NAN, NAN, NAN, 70, 15, 25]
    out = _grade_com_lacuna(values)
    assert out["demand_cpu"].iloc[7:11].isna().all()
    assert not out["filled"].any()


def test_preenchimento_longo_rejeita_metodo_desconhecido() -> None:
    with pytest.raises(ValueError, match="long_gap_fill"):
        _grade_com_lacuna([10, 20, 30], long_gap_fill="linear")
    with pytest.raises(ValueError, match="season_period"):
        _grade_com_lacuna([10, 20, 30], long_gap_fill="seasonal")


@pytest.mark.parametrize(
    ("filled_range", "leaks"),
    [
        (range(2, 6), False),
        (range(7, 11), False),  # borda direita em t = 11, último ponto do treino
        (range(8, 12), True),  # borda direita em t = 12, primeiro ponto da validação
        (range(13, 17), True),
        (range(9, 11), False),  # curta (≤ max_fill_gap): interpolação linear, fora da regra
    ],
)
def test_lacuna_longa_preenchida_precisa_ficar_no_treino(
    synthetic_cfg: dict[str, Any], filled_range: range, leaks: bool
) -> None:
    """Com 20 intervalos e 60/20/20, o treino é t = 0..11."""
    filled = [t in filled_range for t in range(20)]
    series = pd.DataFrame({"demand_cpu": range(20), "filled": filled})
    if leaks:
        with pytest.raises(ValueError, match="fora do treino"):
            check_long_fills_in_train(series, synthetic_cfg)
    else:
        check_long_fills_in_train(series, synthetic_cfg)


def test_serie_real_so_tem_lacunas_preenchidas_no_treino() -> None:
    """Na série real, nada preenchido fora do treino e nenhum NaN, se ela já existir."""
    cfg = load_config()
    if not processed_path(cfg).exists():
        pytest.skip("série real ainda não construída (rode `make data`)")
    series = load_series(cfg)
    splits = split_series(series, cfg)
    assert series["demand_cpu"].notna().all()
    assert not series["filled"].iloc[splits["train"].stop :].any()


# --- arredondamento da demanda no Parquet ---------------------------------------------


def test_parquet_grava_a_demanda_arredondada(
    synthetic_cfg: dict[str, Any], synthetic_series: pd.DataFrame
) -> None:
    decimals = int(synthetic_cfg["data"]["demand_decimals"])
    for col in ("demand_cpu", "demand_mem"):
        values = synthetic_series[col].dropna()
        pd.testing.assert_series_equal(values, values.round(decimals))


def test_round_demand_preserva_lacunas_e_as_demais_colunas() -> None:
    from tcc.data.build import round_demand

    series = pd.DataFrame(
        {
            "demand_cpu": [1282.4355574, float("nan")],
            "demand_mem": [3584.5411716, 1.0],
            "coverage": [0.98309712345, 1.0],
        }
    )
    out = round_demand(series, 6)
    assert out["demand_cpu"].iloc[0] == 1282.435557
    assert math.isnan(out["demand_cpu"].iloc[1])
    assert out["demand_mem"].iloc[0] == 3584.541172
    pd.testing.assert_series_equal(out["coverage"], series["coverage"])
    assert series["demand_cpu"].iloc[0] == 1282.4355574  # não altera a entrada


def test_round_demand_absorve_variacao_de_um_ulp() -> None:
    """A soma paralela do DuckDB pode mudar a média alguns *ulps* entre execuções."""
    import numpy as np

    from tcc.data.build import round_demand

    rng = np.random.default_rng(0)
    values = rng.uniform(500, 4000, 1000)
    a = pd.DataFrame({"demand_cpu": values, "demand_mem": values})
    shifted = np.nextafter(np.nextafter(values, np.inf), np.inf)  # dois ulps acima
    b = pd.DataFrame({"demand_cpu": shifted, "demand_mem": shifted})
    pd.testing.assert_frame_equal(round_demand(a, 6), round_demand(b, 6))
