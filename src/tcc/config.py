from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

CONFIG_NAME = "configs/v0.toml"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    """Caminho do arquivo de configuração, independente do diretório de trabalho.

    Procura primeiro a partir da raiz do projeto (caso normal, com instalação editável) e
    depois a partir do diretório atual, que cobre uma instalação não-editável no contêiner.
    """
    for candidate in (PROJECT_ROOT / CONFIG_NAME, Path.cwd() / CONFIG_NAME):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"não encontrei {CONFIG_NAME} a partir de {PROJECT_ROOT} nem do cwd")


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Lê o arquivo de configuração TOML. Nenhum parâmetro deve ficar fixo no código."""
    with open(path or default_config_path(), "rb") as f:
        return tomllib.load(f)
