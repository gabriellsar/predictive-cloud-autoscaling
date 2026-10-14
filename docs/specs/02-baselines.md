# Fase 2 — Baselines de previsão

**Objetivo:** previsores simples e uma avaliação sem vazamento, em uma interface que a rede
neural da semana seguinte possa usar sem mudar mais nada. **Time-box:** 1 dia.

## 1. Interface

```python
class Forecaster(Protocol):
    name: str

    def fit(self, train: np.ndarray) -> None: ...
    def forecast(self, history: np.ndarray, h: int) -> float:
        """Previsão de y[len(history) - 1 + h], usando SOMENTE `history`."""
```

Regras:

- `fit` só enxerga o treino. Parâmetros estimados ali ficam **fixos** durante a avaliação.
- `forecast` recebe apenas o passado até a origem. Isso torna o vazamento estruturalmente
  difícil. Se um previsor precisar de um atalho por eficiência (por exemplo, atualizar estado
  incrementalmente), ele deve manter um cache interno equivalente, validado pelo teste da Seção 5.
- Um método auxiliar `forecast_many(series, origins, h) -> np.ndarray` pode existir para
  eficiência (vetorização), com a mesma garantia de não olhar o futuro.

## 2. Previsores do v0

| Nome | Descrição |
|---|---|
| `naive` | persistência: `ŷ = y[τ]` |
| `moving_average` | média das últimas `ma_window` observações |
| `seasonal_naive` | valor de `season_period` passos atrás (alinhado ao horizonte) |
| `holt_winters` | suavização exponencial com tendência e sazonalidade de período `season_period`; parâmetros ajustados no treino |
| `arima` | ARIMA com ordem `arima_order`; parâmetros ajustados no treino |

Notas técnicas, a confirmar na documentação atual do `statsmodels`:

- Para ARIMA e Holt-Winters, ajustar **uma vez no treino** e depois atualizar o estado com as novas
  observações **sem reestimar** (a API de resultados do `statsmodels` tem mecanismos para aplicar
  um modelo ajustado a novos dados, como `apply` e `extend`). Reajustar a cada passo é lento demais.
- Para `h > 1` o ARIMA pode ficar lento. Se for o caso, avaliar o ARIMA somente em `h = 1`,
  registrar no diário e seguir.
- Holt-Winters com período de 288 precisa de pelo menos dois ciclos no treino (576 pontos);
  confira isso e falhe com mensagem clara se não houver.
- Não otimizar à exaustão a ordem do ARIMA. A ordem de `configs/v0.toml` é um ponto de partida;
  se `arima_order` for claramente inadequada (resíduos com autocorrelação forte), escolha outra
  usando **só validação**, registre no diário e atualize o arquivo de configuração.

## 3. Protocolo de avaliação (*walk-forward*)

Para cada previsor, cada horizonte `h` em `horizons` e cada *split* (`val` e `test`):

1. Para cada origem `τ` tal que o intervalo-alvo `τ + h` cai dentro do *split*, calcular
   `ŷ(τ + h) = forecaster.forecast(y[: τ + 1], h)`.
2. Comparar com `y[τ + h]`.
3. Calcular as métricas abaixo sobre todas as origens.

O histórico para as primeiras origens de `val` e `test` inclui o fim do *split* anterior. Isso é
passado legítimo.

## 4. Métricas

| Métrica | Definição |
|---|---|
| MAE | média de `abs(y − ŷ)` |
| RMSE | raiz da média de `(y − ŷ)²` |
| MAPE | média de `abs((y − ŷ) / y)` em %, só onde `y > eps` (`eps` = 1% da mediana do treino); reportar também `mape_coverage` (fração de pontos usados) |
| bias | média de `ŷ − y` (positivo = superestima) |
| under_rate | fração de origens com `ŷ < y` |

## 5. Testes (`tests/test_forecasters.py`)

**Teste de ausência de olhar para o futuro (obrigatório para todo previsor):** gerar uma série
sintética, calcular previsões nas origens `τ` e, depois, **alterar arbitrariamente os valores
posteriores a `τ`**. A previsão em `τ` não pode mudar. Esse teste é o árbitro do vazamento.

Outros testes:

- `naive` e `seasonal_naive` conferidos à mão em séries pequenas;
- `moving_average` com janela conhecida;
- um previsor com `h` fora do intervalo levanta erro claro.

## 6. Saídas

- `results/tables/forecast_metrics.csv` com as colunas
  `model, h, split, mae, rmse, mape, mape_coverage, bias, under_rate`.
- `results/figures/forecast_vs_actual.png` — 2 dias do conjunto de teste, `h = 1`, real versus
  cada previsor (uma figura legível; ajuste transparência e cores).
- `results/figures/rmse_by_model.png` — RMSE no teste por modelo e horizonte.

## Critérios de aceite

- [ ] os 5 previsores implementados, todos passando no teste de ausência de olhar para o futuro
- [ ] `forecast_metrics.csv` gerado para `val` e `test`
- [ ] as 2 figuras geradas
- [ ] diário registra decisões do ARIMA e de Holt-Winters (ordem, atalhos, limitações)
- [ ] a interface não depende de `statsmodels` (a rede neural deve poder implementá-la sem ele)
