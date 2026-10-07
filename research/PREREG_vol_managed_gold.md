# Pre-registration: volatility-managed long gold vs matched-exposure buy & hold

Status: written 2026-10-07, BEFORE any vol-managed computation has been run on gold data.
Criteria agreed with the user in conversation; parameters below are fixed and may not be tuned.

## Question
At the same average gold exposure, does scaling a long-only gold position inversely to
recent volatility give better risk-adjusted returns than holding that exposure constant?

## Data
XAUUSD H4 history already cached (MetaQuotes-Demo, 2004-06 onward), resampled to daily
closes (last H4 close of each server day). Windows: IS 2004-06-11 -> 2020-02-17,
OOS 2020-02-17 -> latest bar (the existing 70/30 H4 split). Each window starts fresh.

## Treatment (fixed parameters)
- Volatility estimate: sigma_t = std of the last 20 daily log returns x sqrt(252),
  using only returns up to and including day t-1.
- Target weight: w_t = min(1.0, 0.15 / sigma_t)   (sigma_target = 15%/yr, c_max = 1.0, no leverage).
- Rebalance: weekly, at the first daily close of each week, and only if
  |w_target - w_current| / w_current > 0.20. Otherwise keep the current weight.
- Weight applied from the next day's return (no look-ahead).

## Benchmark
Static long gold at w_bar = time-average of the Treatment's realised weight in that window.
Bought once at the start, never rebalanced.

## Costs (both)
Every change in gold notional pays spread 35 points + commission $6 per lot round turn
(half per side), on the traded notional. Long swap: price-scaled, -12.6 points/lot/night x
(price / 4147.62), triple on Wednesday, charged on the held notional.

## PASS (all must hold, in BOTH IS and OOS, after costs)
1. Sharpe (daily, x sqrt(252)) of Treatment > Sharpe of Benchmark.
2. Max drawdown (daily closes) of Treatment <= Max drawdown of Benchmark.
Anything else = FAIL. Reported but not gated: CAGR, Calmar, turnover, average weight.

## Trial accounting
This is one new trial. No variants (other sigma_target, lookback, band, frequency) will be
run on this data. If it FAILS, the idea is closed for this dataset.

## Amendment 1 (2026-10-07, before any computation)
- Capital: $10,000 per window (same as the Option B test). Weights are applied as exact
  fractional notional; no 0.01-lot rounding, so results measure the method, not lot granularity.
- The optional extra gate "post-cost return > benchmark return" suggested in conversation was
  NOT added: the question is risk-adjusted performance at matched exposure, and the two gates
  above stay the only criteria.
