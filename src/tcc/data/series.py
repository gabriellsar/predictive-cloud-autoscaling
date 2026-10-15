"""Leitura da série processada e divisão cronológica em treino, validação e teste."""

from __future__ import annotations

from typing import Any

import pandas as pd

from tcc.data.paths import processed_path

SPLIT_NAMES = ("train", "val", "test")


def load_series(cfg: dict[str, Any]) -> pd.DataFrame:
    """Lê o Parquet da série com índice posicional 0..T-1 e colunas padronizadas.

    O índice é posicional (não temporal) de propósito: todo o resto do projeto indexa a
    série por posição `t`, e `bucket_start` guarda o tempo em segundos.
    """
    path = processed_path(cfg)
    if not path.exists():
        raise FileNotFoundError(f"série não encontrada em {path}; rode `make data` antes")
    df = pd.read_parquet(path)
    return df.reset_index(drop=True)


def split_series(df: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, slice]:
    """Divide a série em fatias por posição, em ordem cronológica.

    As fatias não se sobrepõem e cobrem a série inteira. O consumidor indexa a série
    completa com elas, para que um previsor no início de `val` ou `test` possa olhar o
    passado sem nunca olhar o futuro. Nunca use divisão aleatória.
    """
    fractions = cfg["data"]["split"]
    total = sum(fractions[name] for name in SPLIT_NAMES)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"as frações de divisão somam {total}, não 1.0")

    n = len(df)
    n_train = int(n * fractions["train"])
    n_val = int(n * fractions["val"])
    if min(n_train, n_val, n - n_train - n_val) <= 0:
        raise ValueError(f"série curta demais ({n} intervalos) para as frações pedidas")

    return {
        "train": slice(0, n_train),
        "val": slice(n_train, n_train + n_val),
        "test": slice(n_train + n_val, n),
    }
