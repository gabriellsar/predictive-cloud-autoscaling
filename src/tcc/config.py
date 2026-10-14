from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path("configs/v0.toml")


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Lê o arquivo de configuração TOML. Nenhum parâmetro deve ficar fixo no código."""
    with open(path, "rb") as f:
        return tomllib.load(f)
