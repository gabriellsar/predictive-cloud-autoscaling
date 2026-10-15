# Verificações de sanidade do simulador (G2)

Conjunto: **test** (355 intervalos de 300 s) · `L = 1` · `n_min = 1` · `c = 1.0`

Capacidade por instância: `k = max(d_train) / n_peak = 3047.2 / 50 = 60.944` máquinas equivalentes. Pico do teste: 3156.3 (1.036 do pico do treino).

## Tabela

| política | C | V | U | O | changes | n_mean | n_max | C_norm |
|---|---|---|---|---|---|---|---|---|
| oracle (m = 0) | 9588 | 0 | 0 | 0.0189 | 294 | 27.0085 | 52 | 1 |
| static_peak (m = 0) | 17750 | 0.0028 | 0.0002 | 0.4702 | 0 | 50 | 50 | 1.8513 |
| reactive_hpa (u* = 0.5) | 20953 | 0 | 0 | 0.5511 | 88 | 59.0225 | 104 | 2.1853 |
| reactive_hpa (u* = 0.6) | 17492 | 0 | 0 | 0.4622 | 85 | 49.2732 | 87 | 1.8244 |
| reactive_hpa (u* = 0.7) | 15029 | 0 | 0 | 0.3741 | 84 | 42.3352 | 74 | 1.5675 |
| reactive_hpa (u* = 0.8) | 13150 | 0.0141 | 0.0008 | 0.2852 | 85 | 37.0423 | 65 | 1.3715 |
| reactive_hpa (u* = 0.9) | 11675 | 0.031 | 0.0034 | 0.1971 | 78 | 32.8873 | 58 | 1.2177 |
| reactive_hpa (u* = 0.95) | 11118 | 0.0845 | 0.0068 | 0.1597 | 81 | 31.3183 | 55 | 1.1596 |
| predictive naive (m = 0) | 9585 | 0.3775 | 0.0324 | 0.0504 | 294 | 27 | 52 | 0.9997 |

## O que cada verificação mostra

- **Oráculo:** `V = 0.0000` e `U = 0.0000`, como exige a spec, com `C = 9588`. Ele é o **menor custo entre as políticas que não violam** (confirmado: as demais com `V = 0` custam de 15029 a 20953). Atenção ao que ele **não** é: a política `predictive naive (m = 0)` custa 9585, menos que o oráculo, mas violando em 37.7% dos intervalos. O oráculo é o piso do custo *sob a restrição de nunca violar*, não o piso absoluto.
- **static_peak:** ociosidade alta (`O = 0.470`) e custo 1.85× o do oráculo. `V = 0.0028 > 0` porque o pico do teste (3156) passa do pico do treino (3047): dimensionar pelo passado não protege contra um pico maior no futuro.
- **reactive_hpa:** decide em `τ` com `d[τ]`, mas a decisão só vale em `τ + L`, então só não viola enquanto a folga `1/u* − 1` cobrir a variação da demanda em um intervalo de 300 s. As violações crescem de forma monótona com `u*` (monotonicidade confirmada), de 0.0000 a 0.0845:

  | `u*` | V | C | C_norm | changes |
  |---|---|---|---|---|
  | 0.5 | 0.0000 | 20953 | 2.185 | 88 |
  | 0.6 | 0.0000 | 17492 | 1.824 | 85 |
  | 0.7 | 0.0000 | 15029 | 1.567 | 84 |
  | 0.8 | 0.0141 | 13150 | 1.372 | 85 |
  | 0.9 | 0.0310 | 11675 | 1.218 | 78 |
  | 0.95 | 0.0845 | 11118 | 1.160 | 81 |

- **predictive com `naive` (m = 0):** `V = 0.3775` e `C_norm = 1.000`. Comportamento próximo do reativo, o que faz sentido: os dois decidem olhando para a última observação. A diferença é que a política preditiva não tem tolerância nem janela de estabilização, então ela troca de tamanho muito mais vezes (294 alterações).

## Figura

![Políticas](figures/sanity_policies.png)

A faixa vermelha marca os intervalos em que `d_t > k·n_t`. É o que o simulador conta em `V`.

## Simplificações do modelo

- Aumentos e reduções sofrem o **mesmo** atraso `L`; na prática, desligar é imediato.
- **Não há custo de troca**: `changes` é medido, mas não entra em `C`.
- Uma instância só, homogênea, de capacidade `k`; nada de tipos ou de posicionamento.
- A demanda é independente da alocação: violar não gera fila nem demanda represada.
