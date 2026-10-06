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
