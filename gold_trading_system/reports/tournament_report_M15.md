# Tournament report -- M15

Generated 2026-10-04T09:43:48. XAUUSD M15, IS 2022-07-18 -> 2025-06-24, OOS 2025-06-24 -> 2026-10-02. Spread floor 35 pts; Shield risk 1.0%/trade.

## Grid searches (in-sample only)

| Strategy | Combos | Eligible | Selected params | IS Sharpe | IS DD % | Eligible combos profitable OOS |
|---|---:|---:|---|---:|---:|---:|
| atr_trend | 27 | 12 | `{'adx_min': 30, 'sl_atr_mult': 1.5, 'reward_risk': 3.0}` | -0.06 | 7.99 | 0/12 |
| mtf_pullback | 12 | 0 | none eligible | - | - | 0/0 |
| session_breakout | 18 | 0 | none eligible | - | - | 0/0 |
| mean_reversion_bands | 12 | 2 | `{'htf_minutes': 60, 'rsi_low': 25, 'reward_risk': 2.0}` | -0.10 | 18.34 | 1/2 |

## OOS results

| entrant | capital | trades | win_rate_pct | profit_factor | return_pct | max_equity_dd_pct | sharpe_daily_annualized | flags |
|---|---|---|---|---|---|---|---|---|
| baseline (0.01 lot, 1000pt SL) | 100.00 | 67 | 26.87 | 0.82 | -68.36 | 80.71 | 0.25 | rej 505 (mostly insufficient_margin) |
| atr_trend default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 45 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 24 (mostly account_too_small) |
| mtf_pullback default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 4163 (mostly account_too_small) |
| session_breakout default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 102 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 124 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 40 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 1,000.00 | 572 | 16.08 | 0.95 | -24.27 | 61.49 | 0.19 |  |
| atr_trend default + Shield | 1,000.00 | 4 | 25.00 | 0.01 | -2.77 | 3.69 | -1.46 | rej 41 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 1,000.00 | 4 | 0.00 | 0.00 | -2.68 | 3.21 | -1.89 | rej 20 (mostly account_too_small) |
| mtf_pullback default + Shield | 1,000.00 | 267 | 34.46 | 0.89 | -14.54 | 20.20 | -0.62 | KILLED, 1 trips, rej 2028 (mostly account_too_small) |
| session_breakout default + Shield | 1,000.00 | 11 | 36.36 | 0.48 | -2.31 | 3.22 | -0.86 | rej 91 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 1,000.00 | 40 | 25.00 | 0.48 | -10.97 | 10.97 | -1.74 | rej 84 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 1,000.00 | 13 | 30.77 | 0.86 | -0.89 | 3.29 | -0.20 | rej 27 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 10,000.00 | 572 | 16.08 | 0.95 | -2.43 | 6.90 | -0.25 |  |
| atr_trend default + Shield | 10,000.00 | 45 | 35.56 | 0.74 | -5.29 | 6.19 | -0.73 |  |
| atr_trend IS-selected + Shield | 10,000.00 | 24 | 25.00 | 0.53 | -6.76 | 8.57 | -1.11 |  |
| mtf_pullback default + Shield | 10,000.00 | 122 | 36.89 | 0.79 | -13.93 | 20.06 | -0.89 | KILLED, 1 trips |
| session_breakout default + Shield | 10,000.00 | 100 | 46.00 | 1.20 | 8.16 | 14.24 | 0.67 | rej 1 (mostly spread) |
| mean_reversion_bands default + Shield | 10,000.00 | 121 | 39.67 | 0.91 | -5.34 | 8.98 | -0.37 | rej 2 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 10,000.00 | 39 | 41.03 | 1.00 | -0.09 | 5.53 | 0.02 | rej 1 (mostly account_too_small) |

## IS results

| entrant | capital | trades | win_rate_pct | profit_factor | return_pct | max_equity_dd_pct | sharpe_daily_annualized | flags |
|---|---|---|---|---|---|---|---|---|
| baseline (0.01 lot, 1000pt SL) | 100.00 | 77 | 25.97 | 0.73 | -84.95 | 88.55 | -0.15 | rej 1240 (mostly insufficient_margin) |
| atr_trend default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 125 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 42 (mostly account_too_small) |
| mtf_pullback default + Shield | 100.00 | 15 | 40.00 | 1.13 | 1.06 | 4.37 | 0.15 | rej 9301 (mostly account_too_small) |
| session_breakout default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 290 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 100.00 | 3 | 33.33 | 0.66 | -0.57 | 1.48 | -0.20 | rej 338 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 100.00 | 1 | 0.00 | 0.00 | -0.88 | 0.88 | -0.58 | rej 123 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 1,000.00 | 1317 | 25.59 | 1.02 | 10.10 | 67.63 | 0.32 |  |
| atr_trend default + Shield | 1,000.00 | 103 | 26.21 | 0.59 | -18.67 | 20.20 | -1.30 | KILLED, 1 trips, rej 13 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 1,000.00 | 42 | 38.10 | 0.87 | -2.62 | 6.94 | -0.19 |  |
| mtf_pullback default + Shield | 1,000.00 | 403 | 36.97 | 0.92 | -14.27 | 20.39 | -0.43 | KILLED, 1 trips, rej 61 (mostly account_too_small) |
| session_breakout default + Shield | 1,000.00 | 58 | 20.69 | 0.30 | -20.03 | 20.65 | -2.18 | KILLED, 1 trips |
| mean_reversion_bands default + Shield | 1,000.00 | 279 | 39.07 | 0.87 | -16.38 | 20.04 | -0.59 | KILLED, 1 trips, rej 13 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 1,000.00 | 112 | 39.29 | 0.92 | -4.56 | 15.33 | -0.19 | rej 10 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 10,000.00 | 1317 | 25.59 | 1.02 | 1.01 | 6.95 | 0.11 |  |
| atr_trend default + Shield | 10,000.00 | 81 | 25.93 | 0.59 | -18.86 | 20.16 | -1.16 | KILLED, 1 trips |
| atr_trend IS-selected + Shield | 10,000.00 | 42 | 38.10 | 0.95 | -1.28 | 7.99 | -0.06 |  |
| mtf_pullback default + Shield | 10,000.00 | 268 | 37.69 | 0.90 | -14.09 | 20.40 | -0.45 | KILLED, 1 trips |
| session_breakout default + Shield | 10,000.00 | 46 | 23.91 | 0.35 | -19.73 | 20.48 | -1.77 | KILLED, 1 trips |
| mean_reversion_bands default + Shield | 10,000.00 | 254 | 40.16 | 0.88 | -16.24 | 20.09 | -0.51 | KILLED, 1 trips |
| mean_reversion_bands IS-selected + Shield | 10,000.00 | 122 | 39.34 | 0.95 | -3.53 | 18.34 | -0.10 |  |

<!-- random-benchmark:begin -->
## Random-entry benchmark (100 seeds per row)

Random entries with the strategy's own entry rate, median stop (ATR units), R:R and trail. Expectancy columns: fixed 0.10 lot, no breaker. Shield columns: $10k behind Shield. `p` = share of random seeds with avg R >= the strategy's (low = edge, ~0.5 = coin flip).

| Strategy | Window | Trades (strat / rand med) | Strat avg R | Random avg R mean [p05, p95] | Strat PF | Random PF med | p | Strat Shield ret % | Random Shield ret % med | Random kill rate |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| atr_trend default | IS | 125 / 120 | -0.222 | -0.087 [-0.275, 0.100] | 0.67 | 0.92 | 0.86 | -18.9 (killed) | -10.5 | 41% |
| atr_trend default | OOS | 45 / 44 | -0.117 | -0.036 [-0.350, 0.218] | 0.77 | 0.96 | 0.66 | -5.3 | -1.1 | 2% |
| mtf_pullback default | IS | 2167 / 1942 | -0.053 | -0.058 [-0.093, -0.017] | 0.94 | 0.93 | 0.39 | -14.1 (killed) | -16.6 | 100% |
| mtf_pullback default | OOS | 992 / 949 | -0.003 | -0.020 [-0.081, 0.053] | 0.98 | 0.99 | 0.35 | -13.9 (killed) | -12.3 | 99% |
| session_breakout default | IS | 290 / 266 | -0.236 | -0.051 [-0.180, 0.069] | 0.73 | 0.98 | 0.98 | -19.7 (killed) | -14.8 | 70% |
| session_breakout default | OOS | 101 / 91 | 0.078 | -0.015 [-0.233, 0.237] | 1.26 | 1.03 | 0.19 | 8.2 | -2.3 | 5% |
| mean_reversion_bands default | IS | 337 / 330 | -0.077 | -0.141 [-0.249, -0.024] | 0.99 | 0.82 | 0.15 | -16.2 (killed) | -18.4 | 98% |
| mean_reversion_bands default | OOS | 122 / 118 | -0.041 | -0.070 [-0.237, 0.108] | 0.98 | 0.94 | 0.42 | -5.3 | -6.9 | 29% |
| atr_trend IS-selected | IS | 42 / 42 | -0.023 | -0.121 [-0.446, 0.230] | 0.96 | 0.88 | 0.35 | -1.3 | -4.8 | 5% |
| atr_trend IS-selected | OOS | 24 / 23 | -0.313 | -0.051 [-0.574, 0.472] | 0.47 | 1.01 | 0.76 | -6.8 | -0.7 | 0% |
| mean_reversion_bands IS-selected | IS | 122 / 120 | -0.021 | -0.127 [-0.322, 0.073] | 1.03 | 0.88 | 0.16 | -3.5 | -15.3 | 62% |
| mean_reversion_bands IS-selected | OOS | 40 / 39 | -0.019 | -0.047 [-0.450, 0.378] | 0.80 | 0.94 | 0.46 | -0.1 | -2.4 | 0% |
<!-- random-benchmark:end -->
