"""Resolução de caminhos e abertura do DuckDB, a partir de `configs/v0.toml`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from tcc.config import PROJECT_ROOT


def resolve(path: str | Path) -> Path:
    """Torna um caminho da configuração absoluto, ancorado na raiz do projeto."""
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def processed_path(cfg: dict[str, Any]) -> Path:
    """`data/processed/<source>_<interval>s.parquet`, como define a spec da Fase 1."""
    data = cfg["data"]
    name = f"{data['source']}_{data['interval_seconds']}s.parquet"
    return resolve(data["processed_dir"]) / name


def interim_path(cfg: dict[str, Any]) -> Path:
    """Parquet intermediário com uma linha por (máquina, *bucket*)."""
    data = cfg["data"]
    name = f"{data['source']}_per_machine_{data['interval_seconds']}s.parquet"
    return resolve(data["interim_dir"]) / name


def connect(cfg: dict[str, Any]) -> duckdb.DuckDBPyConnection:
    """Conexão DuckDB com limite de memória e diretório temporário vindos da configuração."""
    data = cfg["data"]
    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{data['duckdb_memory_limit']}'")
    con.execute(f"SET threads = {data['duckdb_threads']}")
    tmp = resolve(data["interim_dir"]) / "duckdb_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory = '{tmp}'")
    return con
