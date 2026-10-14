# Fase 3 — Simulador de alocação

**Objetivo:** um simulador de tempo discreto, pequeno e correto, que transforma uma política de
decisão em `n_t` e mede custo e violações. **Time-box:** 1,5 dia.

Este é o componente que dá sentido ao trabalho. **Correção importa mais que velocidade ou
sofisticação.** O código deve ficar abaixo de ~200 linhas na parte central.

## 1. Modelo

- Tempo discreto, intervalos `t = 1..T` de 5 min (o simulador roda sobre um *split*).
- Demanda `d_t` vem da série de `demand_cpu`, que a Fase 1 produz.
- **Capacidade por instância `k`:** `k = max(d_train) / n_peak`, calculado só com o treino
  (`n_peak = 50` por padrão). Assim o pico do treino exige cerca de 50 instâncias e a
  discretização por `ceil` é significativa.
- Custo `c = 1` por instância por intervalo, então `C` é medido em "instâncias-intervalo".
- **Mínimo de instâncias:** `n_min = 1`. Sempre `n_t ≥ n_min`.

### Temporização (*lead time*)

A decisão é tomada no fim do intervalo `τ`, depois de observar `d_1..d_τ`, e vale para o intervalo
`τ + L`. O parâmetro `L` (`lead_time`, padrão 1) representa o atraso entre decidir e ter a
capacidade disponível. Por simplicidade, **aumentos e reduções sofrem o mesmo atraso `L`**
(documente isso como simplificação no diário).

Para que todos os intervalos do *split* tenham uma decisão, as origens `τ` percorrem de
`split_start − L` até `split_end − L − 1`. As primeiras origens usam o fim do *split* anterior,
que é histórico legítimo.

A política preditiva usa horizonte `h = L`.

## 2. Políticas

Toda política implementa `required_instances(tau, history, state) -> int`, que devolve as
instâncias que estarão ativas no intervalo `tau + L`.

| Política | Regra |
|---|---|
| `static_peak` | `n = ceil((1 + m) · max(d_train) / k)`, constante |
| `oracle` | `n = ceil((1 + m) · d[tau + L] / k)`, usa a demanda futura real (limite inferior de custo) |
| `reactive_hpa` | estilo HPA: `u = d[tau] / (k · n_atual)`; se `abs(u / u_star − 1) ≤ tolerância`, mantém; senão `n = ceil(d[tau] / (k · u_star))`. Para **reduzir**, usar o **máximo** das recomendações das últimas `hpa_scale_down_window` origens (janela de estabilização) |
| `predictive` | `n = ceil((1 + m) · d_hat / k)`, com `d_hat = forecaster.forecast(history, h=L)`, truncado em `≥ 0` |

Todas aplicam `n = max(n, n_min)`.

`n_atual` na política reativa é o número de instâncias **ativas em `tau`** (já com o atraso aplicado).

Parâmetros varridos (de `configs/v0.toml`): `m` em `margins` para `static_peak`, `oracle` e
`predictive`; `u_star` em `hpa_targets` para `reactive_hpa`.

## 3. Métricas

Calculadas em `src/tcc/eval/allocation.py`, sobre os `T` intervalos do *split*:

```
C       = Σ c · n_t
V       = (1/T) Σ 1[ d_t > k·n_t ]
U       = Σ max(0, d_t − k·n_t) / Σ d_t
O       = Σ max(0, k·n_t − d_t) / Σ k·n_t
changes = Σ 1[ n_t ≠ n_{t−1} ]
C_norm  = C / C_oracle        (C_oracle: oráculo com m = 0, mesmo split e mesmo L)
```

## 4. API sugerida (`src/tcc/sim/`)

```python
@dataclass(frozen=True)
class SimResult:
    n: np.ndarray  # instâncias ativas por intervalo do split
    metrics: dict[str, float]


def simulate(
    demand: np.ndarray,
    split: slice,
    policy: Policy,
    k: float,
    lead_time: int,
    c: float = 1.0,
    n_min: int = 1,
) -> SimResult: ...
```

`demand` é a série completa; `split` seleciona os intervalos avaliados. Políticas e previsores
recebem apenas o histórico até a origem.

## 5. Testes obrigatórios (`tests/test_sim.py`)

1. **Oráculo com `m = 0`:** `V = 0` e `U = 0` para qualquer série não negativa.
2. **Capacidade enorme (`n_t` fixo e muito alto):** `V = 0` e `O` próximo de 1.
3. **`n_t = n_min` fixo com demanda sempre acima da capacidade:** `V = 1`.
4. **Conta à mão:** série de 6 pontos com `n_t` conhecido, conferindo `C, V, U, O, changes`.
5. **Custo:** `C = c · Σ n_t`, e dobrar `c` dobra `C`.
6. **Lead time:** com `L = 2`, a decisão tomada na origem `τ` aparece em `n[τ + 2]`
   (testar com uma política que devolve um valor que muda de forma identificável).
7. **Sem olhar para o futuro:** modificar `d[t > τ]` não altera a decisão da política reativa e
   da preditiva em `τ` (exceto o oráculo, que usa o futuro por definição).
8. **Monotonicidade da margem:** na política preditiva com um previsor fixo, aumentar `m` nunca
   aumenta `V` e nunca reduz `C`.

## 6. Verificações de sanidade (G2)

Executar e mostrar ao Gabriel, em `results/sanity.md`:

- oráculo: `V = 0`, `U = 0` e o menor custo entre as políticas;
- `static_peak`: `O` alto, custo alto e `V` possivelmente > 0 se o teste passar do pico do treino
  (explicar o que acontecer);
- `reactive_hpa`: `V > 0` por causa do atraso, com `V` caindo quando `u_star` diminui;
- `predictive` com `naive`: comportamento parecido com o reativo (faz sentido, pois ambos olham
  para a última observação);
- um gráfico de `d_t` contra `k · n_t` para um trecho de 2 dias, para cada política, de modo que o
  Gabriel possa **ver** o que o simulador faz.

## Critérios de aceite (G2)

- [ ] simulador e 4 políticas implementados
- [ ] os 8 testes passam
- [ ] `results/sanity.md` e o gráfico de trecho gerados
- [ ] diário registra as simplificações (atraso simétrico, sem custo de troca, `k` único)
