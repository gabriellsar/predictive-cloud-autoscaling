"""Testes da GRU (spec 05). Ignorados sem o grupo `nn` (`uv sync --group nn`).

A ausência de olhar para o futuro, a concordância entre `forecast_many` e `forecast` e o
horizonte não positivo já são cobertos em `test_forecasters.py`, que inclui a GRU quando o
`torch` está instalado. Aqui ficam os testes próprios da rede.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")

from tcc.forecast.cache import CachedForecaster  # noqa: E402
from tcc.forecast.nn import GRUForecaster  # noqa: E402

PARAMS = dict(
    window=24,
    max_horizon=6,
    hidden_size=8,
    num_layers=1,
    epochs=5,
    batch_size=16,
    learning_rate=0.01,
    val_fraction=0.2,
    patience=3,
    seed=42,
    num_threads=1,
)


def sine_series(n: int = 300, seed: int = 42) -> np.ndarray:
    """Senoide com tendência leve e ruído: a média do treino difere da média da série."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    return 100 + 0.1 * t + 10 * np.sin(2 * np.pi * t / 24) + rng.normal(0, 1, n)


def fitted(train: np.ndarray, **overrides: object) -> GRUForecaster:
    f = GRUForecaster(**{**PARAMS, **overrides})
    f.fit(train)
    return f


@pytest.fixture(scope="module")
def series() -> np.ndarray:
    return sine_series()


@pytest.fixture(scope="module")
def gru(series: np.ndarray) -> GRUForecaster:
    return fitted(series[:200])


def test_fumaca_previsao_finita_em_todos_os_horizontes(
    gru: GRUForecaster, series: np.ndarray
) -> None:
    for h in range(1, gru.max_horizon + 1):
        value = gru.forecast(series[:200], h)
        assert isinstance(value, float)
        assert np.isfinite(value)
    assert 1 <= gru.best_epoch_ <= PARAMS["epochs"]


def test_normalizacao_usa_so_o_treino(gru: GRUForecaster, series: np.ndarray) -> None:
    train = series[:200]
    assert gru.mean_ == pytest.approx(np.mean(train))
    assert gru.std_ == pytest.approx(np.std(train))
    # a série tem tendência: as estatísticas da série inteira são outras
    assert gru.mean_ != pytest.approx(np.mean(series))


def test_mesma_semente_mesma_previsao(series: np.ndarray) -> None:
    a, b = fitted(series[:200]), fitted(series[:200])
    origins = np.arange(200, 260)
    for h in (1, 6):
        np.testing.assert_array_equal(
            a.forecast_many(series, origins, h), b.forecast_many(series, origins, h)
        )
    # e a semente realmente importa
    other = fitted(series[:200], seed=7)
    assert other.forecast(series[:200], 1) != a.forecast(series[:200], 1)


@pytest.mark.parametrize("h", [0, 7])
def test_horizonte_invalido(gru: GRUForecaster, series: np.ndarray, h: int) -> None:
    with pytest.raises(ValueError, match="horizonte"):
        gru.forecast(series[:200], h)
    with pytest.raises(ValueError, match="horizonte"):
        gru.forecast_many(series, np.array([199]), h)


def test_historico_curto_e_completado_com_o_primeiro_valor(
    gru: GRUForecaster, series: np.ndarray
) -> None:
    short = series[:5]
    padded = np.concatenate([np.full(gru.window - len(short), short[0]), short])
    assert gru.forecast(short, 2) == pytest.approx(gru.forecast(padded, 2), abs=1e-12)
    # e o lote faz o mesmo nas origens do início da série
    origins = np.arange(0, gru.window + 3)
    np.testing.assert_allclose(
        gru.forecast_many(series, origins, 2),
        [gru.forecast(series[: tau + 1], 2) for tau in origins],
        atol=1e-9,
    )


def test_cache_devolve_o_mesmo_que_a_gru(gru: GRUForecaster, series: np.ndarray) -> None:
    cached = CachedForecaster(gru)
    origins = np.arange(200, 240)
    plain = np.array([gru.forecast(series[: tau + 1], 3) for tau in origins])
    for _ in range(2):  # a segunda passada vem toda do cache
        np.testing.assert_array_equal(cached.forecast_many(series, origins, 3), plain)
    assert cached.misses == len(origins)
    assert cached.hits == len(origins)


def test_prever_antes_de_ajustar_e_erro() -> None:
    with pytest.raises(RuntimeError, match="fit"):
        GRUForecaster(**PARAMS).forecast(np.arange(30.0), 1)


def test_treino_curto_demais_tem_mensagem_clara() -> None:
    with pytest.raises(ValueError, match="janelas"):
        GRUForecaster(**PARAMS).fit(np.arange(30.0))


def test_build_forecasters_inclui_a_gru_com_a_configuracao() -> None:
    from tcc.config import load_config
    from tcc.forecast.evaluate import build_forecasters

    cfg = load_config()
    gru = build_forecasters(cfg)[-1]
    assert isinstance(gru, GRUForecaster)
    assert gru.window == cfg["forecast"]["nn"]["window"]
    assert gru.max_horizon == cfg["forecast"]["nn"]["max_horizon"]
