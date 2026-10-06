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
