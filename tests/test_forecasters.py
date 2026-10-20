"""Testes da Fase 2: previsores, ausência de vazamento e métricas."""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from tcc.forecast.arima import ArimaForecaster
from tcc.forecast.base import BaseForecaster, Forecaster
from tcc.forecast.baselines import (
    MovingAverageForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)
from tcc.forecast.holt_winters import HoltWintersForecaster
from tcc.forecast.metrics import all_metrics

SEASON = 12
N = 200
HAS_TORCH = importlib.util.find_spec("torch") is not None
#: GRU pequena, só para os testes de contrato rodarem em poucos segundos.
SMALL_GRU = dict(
    window=24,
    max_horizon=3,
    hidden_size=8,
    num_layers=1,
    epochs=3,
    batch_size=16,
    learning_rate=0.01,
    val_fraction=0.2,
    patience=2,
    seed=42,
    num_threads=1,
)


def synthetic_series(seed: int = 42) -> np.ndarray:
    """Série com tendência, sazonalidade e ruído, com semente fixa."""
    rng = np.random.default_rng(seed)
    t = np.arange(N)
    return 100 + 0.05 * t + 10 * np.sin(2 * np.pi * t / SEASON) + rng.normal(0, 1, N)


def all_forecasters() -> list[Forecaster]:
    forecasters: list[Forecaster] = [
        NaiveForecaster(),
        MovingAverageForecaster(window=6),
        SeasonalNaiveForecaster(season_period=SEASON),
        HoltWintersForecaster(season_period=SEASON),
        ArimaForecaster(order=(2, 1, 2)),
    ]
    # a GRU entra nos mesmos testes de contrato quando o grupo `nn` está instalado
    if HAS_TORCH:
        from tcc.forecast.nn import GRUForecaster

        forecasters.append(GRUForecaster(**SMALL_GRU))
    return forecasters


def forecaster_ids() -> list[str]:
    return [f.name for f in all_forecasters()]


# --------------------------------------------------------------------------------------
# O árbitro do vazamento
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("forecaster", all_forecasters(), ids=forecaster_ids())
@pytest.mark.parametrize("h", [1, 3])
def test_nao_olha_para_o_futuro(forecaster: Forecaster, h: int) -> None:
    """Alterar o futuro depois da origem não pode mudar a previsão feita na origem."""
    y = synthetic_series()
    train = y[:120]
    origins = np.array([120, 130, 140])

    forecaster.fit(train)
    expected = np.asarray(forecaster.forecast_many(y, origins, h), dtype=float)

    # tudo depois da última origem vira lixo
    corrupted = y.copy()
    corrupted[origins[-1] + 1 :] = -999.0

    # (a) uma instância nova, que nunca viu a série original
    fresh = {f.name: f for f in all_forecasters()}[forecaster.name]
    fresh.fit(train)
    np.testing.assert_allclose(
        np.asarray(fresh.forecast_many(corrupted, origins, h), dtype=float), expected
    )

    # (b) a mesma instância, cujo cache interno pode estar contaminado
    np.testing.assert_allclose(
        np.asarray(forecaster.forecast_many(corrupted, origins, h), dtype=float), expected
    )


@pytest.mark.parametrize("forecaster", all_forecasters(), ids=forecaster_ids())
def test_forecast_many_concorda_com_forecast(forecaster: Forecaster) -> None:
    """A versão vetorizada precisa dar o mesmo que chamar `forecast` origem a origem."""
    y = synthetic_series()
    forecaster.fit(y[:120])
    origins = np.array([120, 125, 130])
    vectorized = np.asarray(forecaster.forecast_many(y, origins, 2), dtype=float)
    one_by_one = np.array([forecaster.forecast(y[: int(tau) + 1], 2) for tau in origins])
    np.testing.assert_allclose(vectorized, one_by_one)


# --------------------------------------------------------------------------------------
# Casos conferidos à mão
# --------------------------------------------------------------------------------------


def test_naive_repete_a_ultima_observacao() -> None:
    f = NaiveForecaster()
    history = np.array([1.0, 2.0, 3.0])
    assert f.forecast(history, 1) == 3.0
    assert f.forecast(history, 5) == 3.0


def test_moving_average_com_janela_conhecida() -> None:
    f = MovingAverageForecaster(window=3)
    assert f.forecast(np.array([1.0, 2.0, 3.0, 4.0]), 1) == pytest.approx(3.0)
    # a janela ignora o que está antes dela
    assert f.forecast(np.array([99.0, 1.0, 2.0, 3.0]), 2) == pytest.approx(2.0)


def test_seasonal_naive_olha_um_periodo_atras() -> None:
    f = SeasonalNaiveForecaster(season_period=4)
    history = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    # alvo é o índice 6, cuja fase é 2: o valor mais recente dessa fase é history[2]
    assert f.forecast(history, 1) == 2.0
    # alvo é o índice 9, fase 1: o valor mais recente é history[5]
    assert f.forecast(history, 4) == 5.0


def test_holt_winters_reproduz_o_statsmodels() -> None:
    """A recursão própria precisa dar o mesmo que os valores ajustados do statsmodels."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    y = synthetic_series()
    f = HoltWintersForecaster(season_period=SEASON)
    f.fit(y)
    reference = ExponentialSmoothing(
        y, trend="add", seasonal="add", seasonal_periods=SEASON, initialization_method="heuristic"
    ).fit()
    mine = np.array([f.forecast(y[:i], 1) for i in range(1, len(y))])
    np.testing.assert_allclose(mine, np.asarray(reference.fittedvalues)[1:], atol=1e-8)


# --------------------------------------------------------------------------------------
# Erros claros
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("forecaster", all_forecasters(), ids=forecaster_ids())
@pytest.mark.parametrize("h", [0, -1])
def test_horizonte_invalido_levanta_erro(forecaster: Forecaster, h: int) -> None:
    forecaster.fit(synthetic_series()[:120])
    with pytest.raises(ValueError, match="horizonte"):
        forecaster.forecast(synthetic_series()[:120], h)


def test_historico_curto_demais_levanta_erro() -> None:
    f = SeasonalNaiveForecaster(season_period=10)
    with pytest.raises(ValueError, match="pelo menos"):
        f.forecast(np.arange(5.0), 1)


def test_holt_winters_exige_dois_ciclos_no_treino() -> None:
    f = HoltWintersForecaster(season_period=50)
    with pytest.raises(ValueError, match="dois ciclos"):
        f.fit(np.arange(80.0))


def test_base_forecaster_rejeita_historico_multidimensional() -> None:
    class Dummy(BaseForecaster):
        name = "dummy"

        def forecast(self, history: np.ndarray, h: int) -> float:
            self._check(history, h)
            return 0.0

    with pytest.raises(ValueError, match="unidimensional"):
        Dummy().forecast(np.zeros((3, 2)), 1)


# --------------------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------------------


def test_metricas_conferidas_a_mao() -> None:
    y = np.array([10.0, 20.0, 30.0, 40.0])
    y_hat = np.array([12.0, 18.0, 33.0, 36.0])
    m = all_metrics(y, y_hat, eps=1.0)
    assert m["mae"] == pytest.approx(2.75)  # (2 + 2 + 3 + 4) / 4
    assert m["rmse"] == pytest.approx(np.sqrt((4 + 4 + 9 + 16) / 4))
    assert m["bias"] == pytest.approx(-0.25)  # (2 - 2 + 3 - 4) / 4
    assert m["under_rate"] == pytest.approx(0.5)  # duas previsões abaixo do real
    assert m["mape_coverage"] == pytest.approx(1.0)
    esperado = np.mean([2 / 10, 2 / 20, 3 / 30, 4 / 40]) * 100
    assert m["mape"] == pytest.approx(esperado)


def test_mape_mascara_valores_proximos_de_zero() -> None:
    y = np.array([0.0, 100.0])
    y_hat = np.array([5.0, 110.0])
    m = all_metrics(y, y_hat, eps=1.0)
    assert m["mape_coverage"] == pytest.approx(0.5)
    assert m["mape"] == pytest.approx(10.0)


def test_interface_nao_depende_de_statsmodels() -> None:
    """Critério de aceite: a rede neural deve implementar a interface sem `statsmodels`, e a
    interface não pode depender do `torch` (spec 05).

    Roda em um processo separado porque, neste aqui, `statsmodels` já foi importado.
    """
    import subprocess
    import sys

    code = (
        "import sys;"
        "import tcc.forecast, tcc.forecast.base, tcc.forecast.baselines, tcc.forecast.metrics;"
        "assert 'statsmodels' not in sys.modules, sorted(m for m in sys.modules if 'stats' in m);"
        "assert 'torch' not in sys.modules;"
        "tcc.forecast.NaiveForecaster()"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


# --------------------------------------------------------------------------------------
# Cache de previsões usado na varredura de margens
# --------------------------------------------------------------------------------------


def test_cache_devolve_o_mesmo_que_o_previsor_envolvido() -> None:
    from tcc.forecast.cache import CachedForecaster

    y = synthetic_series()
    plain = HoltWintersForecaster(season_period=SEASON)
    cached = CachedForecaster(HoltWintersForecaster(season_period=SEASON))
    plain.fit(y[:120])
    cached.fit(y[:120])
    origins = np.arange(120, 160)
    for _ in range(2):  # a segunda passada vem toda do cache
        np.testing.assert_allclose(
            cached.forecast_many(y, origins, 2), plain.forecast_many(y, origins, 2)
        )
    assert cached.misses == len(origins)
    assert cached.hits == len(origins)


def test_cache_nao_olha_para_o_futuro_nem_confunde_historicos() -> None:
    from tcc.forecast.cache import CachedForecaster

    y = synthetic_series()
    cached = CachedForecaster(ArimaForecaster(order=(2, 1, 2)))
    cached.fit(y[:120])
    origins = np.array([120, 130, 140])
    expected = cached.forecast_many(y, origins, 2)

    corrupted = y.copy()
    corrupted[origins[-1] + 1 :] = -999.0
    np.testing.assert_allclose(cached.forecast_many(corrupted, origins, 2), expected)

    # um histórico do mesmo tamanho, mas com outro conteúdo, não pode reaproveitar a previsão
    altered = y.copy()
    altered[100] += 50.0
    assert cached.forecast(altered[:131], 2) != cached.forecast(y[:131], 2)


# --------------------------------------------------------------------------------------
# Registro dos previsores a partir da configuração
# --------------------------------------------------------------------------------------


def test_sem_torch_a_gru_e_omitida_com_aviso(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem o grupo `nn`, os clássicos seguem e a GRU sai com um aviso (spec 05, 4.4)."""
    import importlib.util as util

    from tcc.config import load_config
    from tcc.forecast import evaluate

    real_find_spec = util.find_spec
    monkeypatch.setattr(
        util, "find_spec", lambda name, *a: None if name == "torch" else real_find_spec(name, *a)
    )
    with pytest.warns(UserWarning, match="GRU foi omitida"):
        names = [f.name for f in evaluate.build_forecasters(load_config())]
    assert names == ["naive", "moving_average", "seasonal_naive", "holt_winters", "arima"]


def test_max_horizon_menor_que_o_necessario_e_erro_de_configuracao() -> None:
    from tcc.config import load_config
    from tcc.forecast.evaluate import build_forecasters

    cfg = load_config()
    cfg["forecast"]["nn"]["max_horizon"] = 3  # forecast.horizons vai até 6
    with pytest.raises(ValueError, match="max_horizon = 3"):
        build_forecasters(cfg)
