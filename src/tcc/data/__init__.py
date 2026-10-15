"""Camada de dados: construção da série de demanda e divisão cronológica."""

from typing import Any

from tcc.data.series import load_series, split_series

__all__ = ["build_series", "load_series", "split_series"]


def __getattr__(name: str) -> Any:
    """Importa `build_series` só quando pedido.

    Importá-lo aqui faria `python -m tcc.data.build` carregar o módulo duas vezes e emitir
    um RuntimeWarning do runpy.
    """
    if name == "build_series":
        from tcc.data.build import build_series

        return build_series
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
