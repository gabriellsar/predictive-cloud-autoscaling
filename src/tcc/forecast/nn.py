"""Previsor com rede neural recorrente (GRU), univariado, em CPU (spec 05).

Este é o único módulo do projeto que importa `torch`. Ele é carregado sob demanda, como
Holt-Winters e ARIMA com o `statsmodels`, de modo que a interface (`forecast/base.py`) e os
previsores simples continuam funcionando sem o grupo `nn` instalado.

A rede lê as últimas `window` observações da demanda `d_t` (normalizadas com média e desvio
**do treino**) e devolve de uma vez as previsões para `h = 1..max_horizon`: a saída `k`
(base 0) é a previsão de horizonte `h = k + 1`. Treina-se uma vez, no treino, e os pesos
ficam fixos na avaliação, como os parâmetros dos demais previsores.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from contextlib import contextmanager

import numpy as np
import torch
from torch import nn

from tcc.forecast.base import BaseForecaster

#: Precisão dupla: o modelo é pequeno e, com ela, previsões em lote e uma a uma coincidem.
DTYPE = torch.float64


@contextmanager
def _torch_threads(n: int) -> Iterator[None]:
    """Fixa o número de *threads* do PyTorch durante o bloco e restaura o anterior."""
    previous = torch.get_num_threads()
    torch.set_num_threads(n)
    try:
        yield
    finally:
        torch.set_num_threads(previous)


class _GRUNet(nn.Module):
    """GRU seguida de uma camada linear aplicada ao último estado oculto."""

    def __init__(self, hidden_size: int, num_layers: int, max_horizon: int) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=1, hidden_size=hidden_size, num_layers=num_layers, batch_first=True
        )
        self.head = nn.Linear(hidden_size, max_horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (lote, window, 1) → (lote, max_horizon)
        _, hidden = self.gru(x)
        return self.head(hidden[-1])


class GRUForecaster(BaseForecaster):
    """GRU com saída direta para os horizontes 1..`max_horizon`."""

    name = "gru"
    #: O preenchimento à esquerda cobre históricos menores que a janela.
    min_history = 1

    def __init__(
        self,
        *,
        window: int,
        max_horizon: int,
        hidden_size: int,
        num_layers: int,
        epochs: int,
        batch_size: int,
        learning_rate: float,
        val_fraction: float,
        patience: int,
        seed: int,
        num_threads: int,
    ) -> None:
        if window < 1 or max_horizon < 1:
            raise ValueError("gru: window e max_horizon devem ser >= 1")
        if not 0.0 < val_fraction < 1.0:
            raise ValueError(f"gru: val_fraction deve estar em (0, 1), recebi {val_fraction}")
        self.window = int(window)
        self.max_horizon = int(max_horizon)
        self.hidden_size = int(hidden_size)
        self.num_layers = int(num_layers)
        self.epochs = int(epochs)
        self.batch_size = int(batch_size)
        self.learning_rate = float(learning_rate)
        self.val_fraction = float(val_fraction)
        self.patience = int(patience)
        self.seed = int(seed)
        self.num_threads = int(num_threads)

        self.mean_: float | None = None
        self.std_: float | None = None
        self.best_epoch_: int | None = None
        self.history_: list[tuple[float, float]] = []
        self._net: _GRUNet | None = None

    # ----------------------------------------------------------------------------------
    # Ajuste
    # ----------------------------------------------------------------------------------

    def _windows(self, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Janelas deslizantes: entrada `z[t - window + 1 .. t]`, alvo `z[t + 1 .. t + H]`.

        Só entram as origens `t` em que a janela e o alvo completos cabem no treino.
        """
        origins = np.arange(self.window - 1, len(z) - self.max_horizon)
        inputs = origins[:, None] + np.arange(-self.window + 1, 1)[None, :]
        targets = origins[:, None] + np.arange(1, self.max_horizon + 1)[None, :]
        return z[inputs], z[targets]

    def fit(self, train: np.ndarray) -> None:
        """Treina a rede vendo **só** `train`; pesos, média e desvio ficam fixos depois."""
        with _torch_threads(self.num_threads):
            self._fit(train)

    def _fit(self, train: np.ndarray) -> None:
        train = np.asarray(train, dtype=float)
        if train.ndim != 1:
            raise ValueError("gru: o treino deve ser unidimensional")

        # 1. Normalização com estatísticas só do treino.
        self.mean_ = float(np.mean(train))
        std = float(np.std(train))
        self.std_ = std if std > 0 else 1.0
        z = (train - self.mean_) / self.std_

        # 2-3. Janelas e separação cronológica do fim do treino para o early stopping.
        x, y = self._windows(z)
        n_val = int(round(self.val_fraction * len(x)))
        # Descartam-se `max_horizon` janelas entre as duas partes: sem esse intervalo, os
        # alvos das últimas janelas de ajuste seriam os mesmos pontos que a validação
        # interna tenta prever, e a perda de validação ficaria otimista.
        n_fit = len(x) - n_val - self.max_horizon
        if n_val < 1 or n_fit < 1:
            raise ValueError(
                f"gru: treino com {len(train)} pontos rende {len(x)} janelas, poucas para "
                f"window = {self.window}, max_horizon = {self.max_horizon} e "
                f"val_fraction = {self.val_fraction}"
            )
        # entrada com um canal: (janelas, window, 1)
        x_fit, y_fit = self._tensor(x[:n_fit, :, None]), self._tensor(y[:n_fit])
        x_val, y_val = self._tensor(x[-n_val:, :, None]), self._tensor(y[-n_val:])

        # 4. MSE + Adam, semente fixa, restaura a melhor época da validação interna.
        torch.manual_seed(self.seed)
        generator = torch.Generator().manual_seed(self.seed)
        net = _GRUNet(self.hidden_size, self.num_layers, self.max_horizon).to(DTYPE)
        optimizer = torch.optim.Adam(net.parameters(), lr=self.learning_rate)
        loss_fn = nn.MSELoss()

        best_loss, best_state, best_epoch, stale = float("inf"), None, 0, 0
        self.history_ = []
        for epoch in range(1, self.epochs + 1):
            net.train()
            # embaralha só dentro da parte de ajuste; a validação interna fica no fim
            order = torch.randperm(n_fit, generator=generator)
            total = 0.0
            for start in range(0, n_fit, self.batch_size):
                batch = order[start : start + self.batch_size]
                optimizer.zero_grad()
                loss = loss_fn(net(x_fit[batch]), y_fit[batch])
                loss.backward()
                optimizer.step()
                total += loss.item() * len(batch)

            net.eval()
            with torch.no_grad():
                val_loss = float(loss_fn(net(x_val), y_val))
            self.history_.append((total / n_fit, val_loss))

            if val_loss < best_loss:
                best_loss, best_epoch, stale = val_loss, epoch, 0
                best_state = copy.deepcopy(net.state_dict())
            else:
                stale += 1
                if stale >= self.patience:
                    break

        # 5. Pesos da melhor época, modo de avaliação.
        net.load_state_dict(best_state)
        net.eval()
        self._net = net
        self.best_epoch_ = best_epoch

    # ----------------------------------------------------------------------------------
    # Previsão
    # ----------------------------------------------------------------------------------

    def _tensor(self, values: np.ndarray) -> torch.Tensor:
        return torch.as_tensor(values, dtype=DTYPE)

    def _predict(self, windows: np.ndarray, h: int) -> np.ndarray:
        """Roda a rede sobre janelas em escala original e devolve a saída `h` desnormalizada."""
        z = (windows - self.mean_) / self.std_
        with _torch_threads(self.num_threads), torch.no_grad():
            out = self._net(self._tensor(z[:, :, None]))
        return out[:, h - 1].numpy() * self.std_ + self.mean_

    def _check_ready(self, h: int) -> None:
        if self._net is None:
            raise RuntimeError("gru: chame fit() antes de prever")
        if h > self.max_horizon:
            raise ValueError(
                f"gru: o horizonte h = {h} excede max_horizon = {self.max_horizon} "
                "(ajuste [forecast.nn] em configs/v0.toml)"
            )

    def forecast(self, history: np.ndarray, h: int) -> float:
        """Previsão de `y[len(history) - 1 + h]` usando só as últimas `window` de `history`.

        Com menos de `window` observações, completa à esquerda repetindo o primeiro valor.
        """
        history = self._check(history, h)
        self._check_ready(h)
        last = history[-self.window :]
        if len(last) < self.window:
            last = np.concatenate([np.full(self.window - len(last), history[0]), last])
        return float(self._predict(last[None, :], h)[0])

    def forecast_many(self, series: np.ndarray, origins: np.ndarray, h: int) -> np.ndarray:
        """Versão em lote de `forecast`: a janela de cada origem `τ` usa só `series[: τ + 1]`.

        Índices antes do início da série são trocados por 0, o que reproduz o preenchimento
        com o primeiro valor do histórico feito em `forecast`.
        """
        series = np.asarray(series, dtype=float)
        origins = np.asarray(origins, dtype=int)
        if h < 1:
            self._check(series, h)  # mesma mensagem de erro de `forecast`
        self._check_ready(h)
        if len(origins) == 0:
            return np.array([], dtype=float)
        if origins.min() < 0 or origins.max() >= len(series):
            raise ValueError("gru: origem fora da série")
        index = origins[:, None] + np.arange(-self.window + 1, 1)[None, :]
        return self._predict(series[np.maximum(index, 0)], h)
