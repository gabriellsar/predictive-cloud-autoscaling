import tcc
from tcc.config import load_config


def test_import():
    assert tcc.__version__


def test_config_keys():
    cfg = load_config()
    assert cfg["seed"] == 42
    assert abs(sum(cfg["data"]["split"].values()) - 1.0) < 1e-9
    for key in ("n_peak", "lead_time", "margins", "hpa_targets", "epsilons"):
        assert key in cfg["sim"]
    for key in ("horizons", "ma_window", "season_period", "arima_order"):
        assert key in cfg["forecast"]
