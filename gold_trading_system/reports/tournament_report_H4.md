# Tournament report -- H4

Generated 2026-10-04T09:43:48. XAUUSD H4, IS 2004-06-11 -> 2020-02-17, OOS 2020-02-17 -> 2026-10-02. Spread floor 35 pts; Shield risk 1.0%/trade.

## Grid searches (in-sample only)

| Strategy | Combos | Eligible | Selected params | IS Sharpe | IS DD % | Eligible combos profitable OOS |
|---|---:|---:|---|---:|---:|---:|
| atr_trend | 27 | 15 | `{'adx_min': 25, 'sl_atr_mult': 3.0, 'reward_risk': 3.0}` | 0.28 | 6.89 | 11/15 |
| mtf_pullback | 6 | 3 | `{'htf_minutes': 1440, 'reward_risk': 3.0, 'session_hours': [10, 22]}` | 0.78 | 18.69 | 2/3 |
| session_breakout | 18 | 0 | none eligible | - | - | 0/0 |
| mean_reversion_bands | 8 | 4 | `{'htf_minutes': 1440, 'rsi_low': 25, 'reward_risk': 2.0}` | 0.02 | 8.28 | 1/4 |

## OOS results

| entrant | capital | trades | win_rate_pct | profit_factor | return_pct | max_equity_dd_pct | sharpe_daily_annualized | flags |
|---|---|---|---|---|---|---|---|---|
| baseline (0.01 lot, 1000pt SL) | 100.00 | 9 | 0.00 | 0.00 | -92.17 | 94.78 | -0.72 | rej 194 (mostly insufficient_margin) |
| atr_trend default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 17 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 17 (mostly account_too_small) |
| mtf_pullback default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 1217 (mostly account_too_small) |
| mtf_pullback IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 598 (mostly account_too_small) |
| session_breakout default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 412 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 47 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 17 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 1,000.00 | 203 | 10.84 | 0.61 | -70.60 | 72.00 | -0.52 |  |
| atr_trend default + Shield | 1,000.00 | 1 | 0.00 | 0.00 | -0.99 | 0.99 | -0.51 | rej 16 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 1,000.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 17 (mostly account_too_small) |
| mtf_pullback default + Shield | 1,000.00 | 22 | 27.27 | 0.81 | -2.46 | 8.36 | -0.17 | rej 1167 (mostly account_too_small) |
| mtf_pullback IS-selected + Shield | 1,000.00 | 3 | 33.33 | 1.39 | 0.62 | 1.70 | 0.11 | rej 593 (mostly account_too_small) |
| session_breakout default + Shield | 1,000.00 | 139 | 38.85 | 0.68 | -17.46 | 20.70 | -0.75 | KILLED, 1 trips, rej 99 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 1,000.00 | 12 | 50.00 | 1.61 | 2.55 | 3.44 | 0.31 | rej 35 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 1,000.00 | 4 | 25.00 | 0.80 | -0.37 | 1.67 | -0.07 | rej 13 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 10,000.00 | 203 | 10.84 | 0.61 | -7.06 | 7.52 | -0.53 |  |
| atr_trend default + Shield | 10,000.00 | 17 | 41.18 | 1.12 | 0.95 | 3.64 | 0.09 |  |
| atr_trend IS-selected + Shield | 10,000.00 | 16 | 50.00 | 1.44 | 2.21 | 3.31 | 0.21 | rej 1 (mostly account_too_small) |
| mtf_pullback default + Shield | 10,000.00 | 297 | 44.11 | 1.23 | 29.70 | 19.23 | 0.60 | rej 20 (mostly account_too_small) |
| mtf_pullback IS-selected + Shield | 10,000.00 | 220 | 45.45 | 1.22 | 20.78 | 17.37 | 0.47 | rej 12 (mostly account_too_small) |
| session_breakout default + Shield | 10,000.00 | 78 | 38.46 | 0.65 | -12.74 | 20.42 | -0.64 | KILLED, 1 trips |
| mean_reversion_bands default + Shield | 10,000.00 | 44 | 43.18 | 1.05 | 1.04 | 8.95 | 0.07 | rej 3 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 10,000.00 | 14 | 28.57 | 0.65 | -3.04 | 5.69 | -0.27 | rej 3 (mostly account_too_small) |

## IS results

| entrant | capital | trades | win_rate_pct | profit_factor | return_pct | max_equity_dd_pct | sharpe_daily_annualized | flags |
|---|---|---|---|---|---|---|---|---|
| baseline (0.01 lot, 1000pt SL) | 100.00 | 190 | 22.63 | 0.93 | -93.00 | 98.22 | -0.01 | STOP-OUT, rej 240 (mostly insufficient_margin) |
| atr_trend default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 67 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 67 (mostly account_too_small) |
| mtf_pullback default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 2779 (mostly account_too_small) |
| mtf_pullback IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 1448 (mostly account_too_small) |
| session_breakout default + Shield | 100.00 | 2 | 100.00 | - | 1.61 | 0.55 | 0.34 | rej 1190 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 142 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 55 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 1,000.00 | 430 | 19.77 | 0.97 | -8.96 | 44.09 | 0.02 |  |
| atr_trend default + Shield | 1,000.00 | 34 | 41.18 | 1.10 | 1.72 | 9.06 | 0.07 | rej 33 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 1,000.00 | 9 | 44.44 | 0.82 | -0.76 | 3.91 | -0.07 | rej 58 (mostly account_too_small) |
| mtf_pullback default + Shield | 1,000.00 | 500 | 44.20 | 1.22 | 57.07 | 11.60 | 0.51 | rej 1022 (mostly account_too_small) |
| mtf_pullback IS-selected + Shield | 1,000.00 | 349 | 46.42 | 1.32 | 63.07 | 12.93 | 0.62 | rej 574 (mostly account_too_small) |
| session_breakout default + Shield | 1,000.00 | 190 | 36.84 | 0.71 | -19.77 | 20.16 | -0.44 | KILLED, 1 trips, rej 9 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 1,000.00 | 93 | 38.71 | 0.85 | -6.27 | 9.82 | -0.18 | rej 49 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 1,000.00 | 34 | 38.24 | 1.07 | 1.06 | 4.71 | 0.05 | rej 21 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 10,000.00 | 430 | 19.77 | 0.97 | -0.90 | 5.37 | -0.03 |  |
| atr_trend default + Shield | 10,000.00 | 67 | 41.79 | 1.18 | 6.21 | 12.28 | 0.17 |  |
| atr_trend IS-selected + Shield | 10,000.00 | 67 | 47.76 | 1.31 | 9.15 | 6.89 | 0.28 |  |
| mtf_pullback default + Shield | 10,000.00 | 389 | 46.53 | 1.23 | 58.99 | 20.16 | 0.54 | KILLED, 1 trips, rej 1 (mostly spread) |
| mtf_pullback IS-selected + Shield | 10,000.00 | 546 | 48.90 | 1.30 | 141.21 | 18.69 | 0.78 | rej 1 (mostly spread) |
| session_breakout default + Shield | 10,000.00 | 99 | 33.33 | 0.55 | -19.78 | 20.36 | -0.57 | KILLED, 1 trips |
| mean_reversion_bands default + Shield | 10,000.00 | 141 | 37.59 | 0.85 | -11.85 | 18.83 | -0.22 |  |
| mean_reversion_bands IS-selected + Shield | 10,000.00 | 55 | 36.36 | 1.01 | 0.40 | 8.28 | 0.02 |  |

<!-- random-benchmark:begin -->
## Random-entry benchmark (100 seeds per row)

Random entries with the strategy's own entry rate, median stop (ATR units), R:R and trail. Expectancy columns: fixed 0.10 lot, no breaker. Shield columns: $10k behind Shield. `p` = share of random seeds with avg R >= the strategy's (low = edge, ~0.5 = coin flip).

| Strategy | Window | Trades (strat / rand med) | Strat avg R | Random avg R mean [p05, p95] | Strat PF | Random PF med | p | Strat Shield ret % | Random Shield ret % med | Random kill rate |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| atr_trend default | IS | 67 / 63 | 0.102 | -0.036 [-0.251, 0.177] | 1.15 | 0.97 | 0.16 | 6.2 | -2.9 | 4% |
| atr_trend default | OOS | 17 / 16 | 0.086 | 0.002 [-0.475, 0.682] | 1.66 | 1.03 | 0.36 | 0.9 | -0.2 | 0% |
| mtf_pullback default | IS | 718 / 854 | 0.116 | -0.037 [-0.093, 0.026] | 1.19 | 0.96 | 0.00 | 59.0 (killed) | -17.6 | 98% |
| mtf_pullback default | OOS | 285 / 355 | 0.126 | 0.008 [-0.077, 0.112] | 1.16 | 1.02 | 0.04 | 29.7 | -6.3 | 50% |
| session_breakout default | IS | 1188 / 1004 | -0.081 | -0.090 [-0.158, -0.012] | 0.91 | 0.90 | 0.34 | -19.8 (killed) | -18.3 | 100% |
| session_breakout default | OOS | 412 / 359 | -0.048 | -0.039 [-0.173, 0.108] | 0.94 | 0.94 | 0.56 | -12.7 (killed) | -12.2 | 88% |
| mean_reversion_bands default | IS | 141 / 139 | -0.093 | -0.084 [-0.252, 0.090] | 0.79 | 0.90 | 0.53 | -11.8 | -11.8 | 40% |
| mean_reversion_bands default | OOS | 47 / 46 | 0.020 | -0.044 [-0.295, 0.247] | 1.35 | 0.85 | 0.33 | 1.0 | -1.8 | 2% |
| atr_trend IS-selected | IS | 67 / 62 | 0.152 | -0.014 [-0.233, 0.266] | 1.22 | 1.00 | 0.13 | 9.2 | -1.6 | 1% |
| atr_trend IS-selected | OOS | 17 / 16 | 0.276 | 0.011 [-0.420, 0.435] | 2.57 | 1.14 | 0.19 | 2.2 | -0.2 | 0% |
| mtf_pullback IS-selected | IS | 546 / 438 | 0.177 | -0.012 [-0.099, 0.084] | 1.26 | 1.02 | 0.00 | 141.2 | -11.6 | 75% |
| mtf_pullback IS-selected | OOS | 222 / 182 | 0.107 | 0.010 [-0.136, 0.162] | 1.21 | 1.05 | 0.17 | 20.8 | -1.1 | 19% |
| mean_reversion_bands IS-selected | IS | 55 / 53 | 0.007 | -0.077 [-0.367, 0.201] | 0.93 | 0.92 | 0.32 | 0.4 | -3.9 | 4% |
| mean_reversion_bands IS-selected | OOS | 17 / 17 | -0.193 | 0.014 [-0.598, 0.609] | 1.48 | 1.10 | 0.76 | -3.0 | 0.4 | 0% |
<!-- random-benchmark:end -->

<!-- buy-hold-overlay:begin -->
## Option B -- H4 mtf_pullback vs Buy & Hold (pre-registered, single pass)

| Window | Swap model | System | CAGR % | Max DD % | Sharpe | Sortino | Return % | Trades | PF | Notes |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| IS | fixed | mtf_pullback + Shield | 3.00 | 20.16 | 0.54 | 0.83 | 59.0 | 389 | 1.229 | KILLED |
| IS | fixed | Buy & Hold | 7.62 | 43.31 | 0.66 | 0.94 | 216.4 | 1 | - |  |
| IS | fixed | **criteria** | FAIL | ok | | | | | | FAIL |
| OOS | fixed | mtf_pullback + Shield | 3.91 | 18.98 | 0.58 | 0.92 | 28.9 | 296 | 1.221 |  |
| OOS | fixed | Buy & Hold | 13.79 | 30.60 | 0.76 | 1.07 | 135.4 | 1 | - |  |
| OOS | fixed | **criteria** | FAIL | ok | | | | | | FAIL |
| IS | price-scaled | mtf_pullback + Shield | 3.71 | 20.23 | 0.65 | 1.03 | 77.1 | 389 | 1.28 | KILLED |
| IS | price-scaled | Buy & Hold | 8.63 | 50.46 | 0.53 | 0.75 | 266.6 | 1 | - |  |
| IS | price-scaled | **criteria** | FAIL | ok | | | | | | FAIL |
| OOS | price-scaled | mtf_pullback + Shield | 4.21 | 18.51 | 0.63 | 0.99 | 31.4 | 296 | 1.24 |  |
| OOS | price-scaled | Buy & Hold | 14.32 | 29.95 | 0.81 | 1.13 | 142.8 | 1 | - |  |
| OOS | price-scaled | **criteria** | FAIL | ok | | | | | | FAIL |

**Overall: FAIL** (all windows x swap models must pass)
<!-- buy-hold-overlay:end -->
