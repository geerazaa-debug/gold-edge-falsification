# Tournament report -- H1

Generated 2026-10-04T09:44:00. XAUUSD H1, IS 2009-11-04 -> 2021-09-16, OOS 2021-09-16 -> 2026-10-02. Spread floor 35 pts; Shield risk 1.0%/trade.

## Grid searches (in-sample only)

| Strategy | Combos | Eligible | Selected params | IS Sharpe | IS DD % | Eligible combos profitable OOS |
|---|---:|---:|---|---:|---:|---:|
| atr_trend | 27 | 17 | `{'adx_min': 30, 'sl_atr_mult': 3.0, 'reward_risk': 3.0}` | 0.16 | 5.79 | 16/17 |
| mtf_pullback | 12 | 0 | none eligible | - | - | 0/0 |
| session_breakout | 18 | 0 | none eligible | - | - | 0/0 |
| mean_reversion_bands | 12 | 1 | `{'htf_minutes': 240, 'rsi_low': 25, 'reward_risk': 1.5}` | -0.05 | 19.41 | 0/1 |

## OOS results

| entrant | capital | trades | win_rate_pct | profit_factor | return_pct | max_equity_dd_pct | sharpe_daily_annualized | flags |
|---|---|---|---|---|---|---|---|---|
| baseline (0.01 lot, 1000pt SL) | 100.00 | 16 | 18.75 | 0.28 | -84.03 | 88.06 | -0.20 | rej 551 (mostly insufficient_margin) |
| atr_trend default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 57 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 14 (mostly account_too_small) |
| mtf_pullback default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 3885 (mostly account_too_small) |
| session_breakout default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 420 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 141 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 46 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 1,000.00 | 567 | 19.22 | 1.14 | 59.55 | 49.58 | 0.44 |  |
| atr_trend default + Shield | 1,000.00 | 18 | 38.89 | 1.05 | 0.39 | 3.44 | 0.05 | rej 39 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 1,000.00 | 1 | 0.00 | 0.00 | -0.89 | 1.16 | -0.44 | rej 13 (mostly account_too_small) |
| mtf_pullback default + Shield | 1,000.00 | 354 | 37.29 | 0.95 | -8.21 | 20.39 | -0.16 | KILLED, 1 trips, rej 383 (mostly account_too_small) |
| session_breakout default + Shield | 1,000.00 | 120 | 30.00 | 0.78 | -13.14 | 20.52 | -0.56 | KILLED, 1 trips, rej 5 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 1,000.00 | 77 | 37.66 | 0.96 | -1.18 | 9.98 | -0.05 | rej 64 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 1,000.00 | 30 | 26.67 | 0.58 | -6.83 | 8.95 | -0.56 | rej 16 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 10,000.00 | 567 | 19.22 | 1.14 | 5.96 | 6.59 | 0.34 |  |
| atr_trend default + Shield | 10,000.00 | 56 | 37.50 | 1.04 | 1.21 | 8.67 | 0.08 | rej 1 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 10,000.00 | 14 | 57.14 | 1.98 | 3.29 | 1.58 | 0.41 |  |
| mtf_pullback default + Shield | 10,000.00 | 401 | 43.39 | 0.97 | -6.35 | 20.50 | -0.08 | KILLED, 1 trips |
| session_breakout default + Shield | 10,000.00 | 112 | 31.25 | 0.81 | -12.78 | 20.32 | -0.44 | KILLED, 1 trips |
| mean_reversion_bands default + Shield | 10,000.00 | 133 | 39.85 | 0.90 | -7.00 | 14.70 | -0.22 | rej 6 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 10,000.00 | 45 | 28.89 | 0.59 | -11.82 | 13.57 | -0.70 | rej 1 (mostly account_too_small) |

## IS results

| entrant | capital | trades | win_rate_pct | profit_factor | return_pct | max_equity_dd_pct | sharpe_daily_annualized | flags |
|---|---|---|---|---|---|---|---|---|
| baseline (0.01 lot, 1000pt SL) | 100.00 | 954 | 26.00 | 0.98 | -89.43 | 98.57 | 0.30 | rej 353 (mostly insufficient_margin) |
| atr_trend default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 138 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 50 (mostly account_too_small) |
| mtf_pullback default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 8236 (mostly account_too_small) |
| session_breakout default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 1084 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 347 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 100.00 | 0 | 0.00 | - | 0.00 | 0.00 | 0.00 | rej 117 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 1,000.00 | 1307 | 25.40 | 1.02 | 15.47 | 62.05 | 0.16 |  |
| atr_trend default + Shield | 1,000.00 | 110 | 39.09 | 0.88 | -5.65 | 18.93 | -0.16 | rej 27 (mostly account_too_small) |
| atr_trend IS-selected + Shield | 1,000.00 | 19 | 47.37 | 1.77 | 4.62 | 4.19 | 0.29 | rej 31 (mostly account_too_small) |
| mtf_pullback default + Shield | 1,000.00 | 262 | 36.26 | 0.82 | -20.19 | 20.38 | -0.35 | KILLED, 1 trips, rej 227 (mostly account_too_small) |
| session_breakout default + Shield | 1,000.00 | 194 | 29.90 | 0.78 | -19.48 | 20.10 | -0.41 | KILLED, 1 trips, rej 22 (mostly account_too_small) |
| mean_reversion_bands default + Shield | 1,000.00 | 230 | 37.83 | 0.84 | -16.61 | 20.51 | -0.35 | KILLED, 1 trips, rej 30 (mostly account_too_small) |
| mean_reversion_bands IS-selected + Shield | 1,000.00 | 100 | 39.00 | 0.84 | -7.95 | 13.65 | -0.24 | rej 16 (mostly account_too_small) |
| baseline (0.01 lot, 1000pt SL) | 10,000.00 | 1307 | 25.40 | 1.02 | 1.55 | 9.57 | 0.07 |  |
| atr_trend default + Shield | 10,000.00 | 80 | 33.75 | 0.70 | -13.80 | 20.15 | -0.43 | KILLED, 1 trips, rej 1 (mostly spread) |
| atr_trend IS-selected + Shield | 10,000.00 | 48 | 47.92 | 1.20 | 3.91 | 5.79 | 0.16 | rej 1 (mostly spread) |
| mtf_pullback default + Shield | 10,000.00 | 299 | 40.80 | 0.86 | -20.03 | 20.39 | -0.29 | KILLED, 1 trips |
| session_breakout default + Shield | 10,000.00 | 98 | 29.59 | 0.64 | -20.40 | 20.48 | -0.54 | KILLED, 1 trips |
| mean_reversion_bands default + Shield | 10,000.00 | 249 | 42.17 | 0.97 | -4.85 | 20.51 | -0.06 | KILLED, 1 trips |
| mean_reversion_bands IS-selected + Shield | 10,000.00 | 116 | 42.24 | 0.96 | -2.76 | 19.41 | -0.05 |  |

<!-- random-benchmark:begin -->
## Random-entry benchmark (100 seeds per row)

Random entries with the strategy's own entry rate, median stop (ATR units), R:R and trail. Expectancy columns: fixed 0.10 lot, no breaker. Shield columns: $10k behind Shield. `p` = share of random seeds with avg R >= the strategy's (low = edge, ~0.5 = coin flip).

| Strategy | Window | Trades (strat / rand med) | Strat avg R | Random avg R mean [p05, p95] | Strat PF | Random PF med | p | Strat Shield ret % | Random Shield ret % med | Random kill rate |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| atr_trend default | IS | 137 / 134 | -0.073 | -0.058 [-0.219, 0.137] | 0.80 | 0.91 | 0.49 | -13.8 (killed) | -9.9 | 36% |
| atr_trend default | OOS | 57 / 54 | 0.013 | -0.012 [-0.289, 0.290] | 0.81 | 0.95 | 0.47 | 1.2 | 0.0 | 0% |
| mtf_pullback default | IS | 2354 / 2219 | -0.054 | -0.049 [-0.085, 0.008] | 0.95 | 0.92 | 0.57 | -20.0 (killed) | -13.4 | 100% |
| mtf_pullback default | OOS | 1006 / 1022 | 0.043 | -0.036 [-0.097, 0.020] | 1.08 | 0.96 | 0.01 | -6.3 (killed) | -15.8 | 99% |
| session_breakout default | IS | 1083 / 946 | -0.146 | -0.110 [-0.187, -0.042] | 0.77 | 0.84 | 0.80 | -20.4 (killed) | -15.6 | 100% |
| session_breakout default | OOS | 420 / 371 | -0.103 | -0.041 [-0.144, 0.072] | 0.94 | 0.98 | 0.82 | -12.8 (killed) | -11.5 | 88% |
| mean_reversion_bands default | IS | 342 / 340 | -0.105 | -0.121 [-0.233, -0.002] | 0.85 | 0.82 | 0.43 | -4.8 (killed) | -16.6 | 96% |
| mean_reversion_bands default | OOS | 137 / 135 | -0.066 | -0.046 [-0.192, 0.110] | 0.70 | 0.93 | 0.60 | -7.0 | -6.2 | 29% |
| atr_trend IS-selected | IS | 49 / 47 | 0.090 | -0.021 [-0.339, 0.284] | 0.85 | 0.96 | 0.26 | 3.9 | -0.4 | 1% |
| atr_trend IS-selected | OOS | 14 / 13 | 0.281 | -0.005 [-0.613, 0.541] | 2.64 | 1.04 | 0.17 | 3.3 | -0.1 | 0% |
| mean_reversion_bands IS-selected | IS | 116 / 116 | -0.014 | -0.115 [-0.291, 0.091] | 1.17 | 0.85 | 0.17 | -2.8 | -13.5 | 41% |
| mean_reversion_bands IS-selected | OOS | 46 / 46 | -0.299 | -0.056 [-0.345, 0.269] | 0.42 | 0.94 | 0.89 | -11.8 | -2.4 | 1% |
<!-- random-benchmark:end -->
