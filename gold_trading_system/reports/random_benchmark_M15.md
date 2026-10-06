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
