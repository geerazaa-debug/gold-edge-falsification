# STATE_SNAPSHOT -- 2026-10-04 (milestone 6, Option B result)

Branch `feat/gold-shield-tournament` (from `master`).

## Done this milestone

- **Shield** `core/risk_guardrails/`: Pydantic `ShieldLimits` (YAML tighten-only
  vs `HARD_*` ceilings), `TradeRequest`/`ShieldValidator` (risk-% sizing that
  rejects instead of clamping up to min lot, R:R >= 1.5, spread cap, open-risk
  cap), `CircuitBreaker` (5% daily halt, 20% DD latched kill, human reset).
  Edits blocked by the `.claude/hooks/protect_shield.py` PreToolUse hook.
- **Scout** `core/data_ingestion/mt5_history.py`: 99,000 real XAUUSD M15 bars
  from MetaQuotes-Demo, 2022-07-18 -> 2026-10-02, cached to `data/history/`.
- **Arch** `core/strategies/m15_trend.py`: `BaselineCross` (EMA20/50, 0.01 lot,
  1000-pt SL; a stand-in, since the real EA's .mq5 is not in the repo) and
  `AtrTrendFilter` (EMA200 trend + slope, ADX >= min, ATR stop, R-multiple TP,
  chandelier trail). Wilder `adx()` added to `indicators.py`.
- **Worker** `core/backtester/m15_engine.py` + `skills/run_backtest_tournament.py`
  (70/30 IS/OOS split, 27-combo IS grid, single OOS scoring) and
  `skills/generate_daily_report.py`. 18 new tests; the stale
  "no MT5 installed" test now mocks the failure.

## Latest tournament (spread floor 30 pts, commission + swap from broker_costs.yaml)

OOS = 2025-06-24 -> 2026-10-02.

| Entrant | Capital | OOS trades | Win % | PF | Return | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| Baseline (0.01 lot, no Shield) | $100 | 72 | 27.8 | 0.84 | -66.5% | 83.4% |
| ATR trend + Shield (any params) | $100 | 0 | - | - | 0% | 0% |
| Baseline | $10,000 | 572 | 16.3 | 0.95 | -2.2% | 6.8% |
| ATR trend default + Shield | $10,000 | 45 | 35.6 | 0.75 | -5.2% | 6.1% |
| ATR trend IS-selected + Shield | $10,000 | 24 | 25.0 | 0.53 | -6.7% | 8.6% |

Findings:
1. **Shield works as specified.** It killed the default ATR strategy at exactly
   20% DD in-sample and kept every OOS run under 9% DD.
2. **None of the strategies has an edge.** All 27 IS grid combos had negative
   Sharpe; 1/13 eligible combos was profitable OOS. The ADX/EMA200/ATR
   filters cut drawdown by cutting trades, not by adding edge.
3. **$100 cannot be traded with 1% risk.** Median M15 ATR is ~820 points now,
   so a 2xATR stop at 0.01 lot risks ~$16 against a $1 budget. Even the 2%
   hard ceiling needs roughly $800-1,600 of equity per trade.
4. The baseline here is NOT the user's EA (their MT5 report: PF 1.36, 49%
   win). Results can't be compared until the real entry rules are ported.

## Milestone 2 -- multi-timeframe pullback (2026-10-04)

- `Indicators.htf_trend()`: H1/H4 bias built from M15 bars using only HTF bars
  CLOSED by the current M15 close (tested: removing future bars never changes
  a past value).
- `MtfPullback`: HTF EMA200 bias + slope, M15 pullback to EMA20, resume
  trigger (close beyond prior bar's high/low), structure stop clamped to
  0.75-2.5 ATR, R-multiple TP, chandelier trail, exit on HTF bias flip.
- Tournament now tunes several strategies, adds a $1,000 capital row, and
  writes `reports/tournament_report.md` (full tables; regenerate with the skill).

Result: **no edge.** All 12 IS combos (H1/H4 x RR 1.5/2/3 x session on/off)
hit the 20% kill in-sample, so none was eligible. Without the breaker, at a
fixed lot, it averages ~0R/trade (IS PF 0.96-0.97 over ~2,000 trades; OOS PF
0.87-0.98). The one positive OOS row ($10k default, +5.2%) was killed at 20%
DD in the same run -- a lucky stretch, not an edge.

Engine fidelity note: kills land at 20.2-21.1% DD, not exactly 20%, because the
backtest breaker acts at the bar close after seeing the intrabar low. A live
tick-level breaker would cut closer to 20%.

## Milestone 3 -- random-entry benchmark (2026-10-04)

- `core/strategies/random_entry.py`: seeded coin-flip entries; everything
  after entry (ATR stop, R:R TP, chandelier trail, engine, costs, Shield)
  matches the trend strategies.
- `skills/run_random_benchmark.py`: for each strategy, a random twin with the
  same entry rate and median stop (ATR units, measured from the strategy's own
  signals), 100 seeds x IS/OOS. Table in `reports/random_benchmark.md`, also
  spliced into `tournament_report.md`.

| Strategy | Window | Strat avg R | Random avg R mean [p05, p95] | p |
|---|---|---:|---|---:|
| atr_trend default | IS / OOS | -0.207 / -0.116 | -0.074 / -0.031 | 0.86 / 0.67 |
| atr_trend IS-selected | IS / OOS | -0.019 / -0.311 | -0.103 / -0.044 | 0.38 / 0.76 |
| mtf_pullback H1 | IS / OOS | -0.037 / +0.002 | -0.047 [-0.082, +0.001] / -0.016 [-0.080, +0.057] | 0.34 / 0.33 |
| mtf_pullback H4 | IS / OOS | -0.050 / -0.013 | -0.047 / -0.011 | 0.56 / 0.50 |

(`p` = share of random seeds at or above the strategy; an edge would need p < ~0.05.)

Findings:
1. **No strategy beats random entries.** Every p is 0.33-0.86, in both windows.
2. **The ~-0.05R per trade is cost friction.** The same random profile earns
   +0.002R with zero costs and -0.044R with costs (30 seeds, IS). A real
   entry edge must clear ~0.05R/trade before it shows a profit.
3. **Zero-edge + many trades = guaranteed kill.** Random twins of the MTF
   strategy (signals on ~13% of bars) hit the 20% kill at $10k in 98-100% of
   seeds: -0.05R x hundreds of trades x 1% risk > 20%. Trade frequency is a
   risk in itself when edge is ~0.
4. MTF's structure stop is effectively always the 2.5 ATR cap (median 2.49):
   the "structure" part adds nothing; its pullback condition is loose enough
   to fire on 13% of bars.

## Milestone 4 -- new edge hypotheses (2026-10-04)

EA scan: no new .mq5/.mq4 in the repo or MT5 data folder (only MetaQuotes'
stock ExpertMACD/MAMA/MAPSAR and ZeroMQ_Listener).

Costs updated to values measured on MetaQuotes-Demo: spread floor 35 points
($0.35), swap -12.6 / -4.6 per lot per night (was 30 / -6.5 / -2.3). All
numbers below and in `tournament_report.md` use them.

- `core/strategies/edge_candidates.py`
  - **A `SessionBreakout`**: first close outside the Asian (03-10 server) or
    pre-NY (12-16) range, one trade/day, squeeze filter (range <= factor x
    20-day median), stop at range mid, flat by 22:00.
  - **B `MeanReversionBands`**: close back inside Bollinger(20,2) after an
    outside close with RSI <= 30 (>= 70), optional H1/H4 bias filter.
  - Both tested for look-ahead (truncating future bars leaves past signals unchanged).

### Gate: OOS p < 0.05 vs random twin (100 seeds)

| Candidate | IS avg R / p | OOS avg R / p | Verdict |
|---|---|---|---|
| session_breakout default | -0.236 / 0.98 | +0.078 / 0.19 | REJECT |
| mean_reversion_bands default | -0.077 / 0.15 | -0.041 / 0.42 | REJECT |
| mean_reversion_bands IS-selected (H1, RSI 25, 1.5R) | -0.042 / 0.16 | -0.009 / 0.43 | REJECT |
| (re-run) atr_trend, mtf_pullback H1/H4 | p 0.35-0.86 | p 0.35-0.76 | REJECT |

**VALID CANDIDATES: none.** Grid search found 0 IS-eligible session_breakout
combos (all hit the 20% kill). The breakout's positive OOS (+0.078R, +8.2%
at $10k) does not survive its IS (-0.236R, p 0.98) and is not significant
(p 0.19). With ~5 candidates tested, a single p just under 0.05 would still
deserve a 1000-seed re-run and a multiple-testing haircut.

### Shield bug found -- FIXED in milestone 5 (user approved, commit 53f767b)

`ShieldValidator.validate()` computes `reward_risk` from float prices, so a
request at exactly the minimum (1.5R) is rejected as `reward_risk < 1.5`
about **33% of the time** (326/1000 random 1.5R requests). Every rr=1.5
config's Shield-mode rows are understated (e.g. mean_reversion "rej mostly
reward_risk"). p-values are NOT affected (expectancy mode bypasses Shield).
Proposed one-line fix in `core/risk_guardrails/validator.py`:
`reward_risk = round(tp_points / sl_points, 6)`.

## Milestone 5 -- H1 / H4 timeframes (2026-10-04)

- Shield R:R float bug fixed with user sign-off (`round(..., 6)`), regression
  test fails without it. NOTE: the protect-Shield hook was not active -- it
  only loads when Claude Code starts in `gold_trading_system/`.
- `--timeframe M15|H1|H4` on both skills; per-timeframe overrides in
  `strategy_config.yaml` (`timeframes:`), checked so htf_minutes > bar size.
  History: H1 2009-2026 (99k bars), H4 2004-2026 (34k bars). Reports are now
  `tournament_report_<TF>.md`, `random_benchmark_<TF>.md`.
- `RandomEntry` / benchmark gained stricter nulls: `--null side` (default --
  random twin uses the strategy's own long share) and `--null bias` (side =
  the strategy's HTF bias, only timing random).

### 100-seed screen (coin-flip null), OOS p < 0.05 hits

| Candidate | IS avg R / p | OOS avg R / p |
|---|---|---|
| H4 mtf_pullback default (D1 bias + H4 pullback) | +0.116 / 0.00 | +0.126 / 0.04 |
| H1 mtf_pullback default (H4 bias) | -0.054 / 0.57 | +0.043 / 0.01 |

Everything else on M15/H1/H4: p 0.13-0.98 (tables in `random_benchmark_<TF>.md`).
~19 OOS tests this round -> Bonferroni threshold ~0.003.

### 2000-seed re-test of H4 mtf_pullback default

| Null model | IS random mean / p | OOS random mean [p05, p95] / p |
|---|---|---|
| coin (50/50) | -0.038 / 0.000 | +0.007 [-0.091, +0.111] / 0.032 |
| side (77% long, as strategy) | -0.007 / 0.001 | +0.092 [-0.000, +0.182] / **0.272** |
| bias (D1 side, random timing) | +0.051 / 0.000 | +0.094 [+0.040, +0.149] / **0.171** |

**Verdict: REJECT.** The OOS "edge" is long exposure during gold's
2020-2026 bull run: random entries with the same long share earn +0.092R vs
the strategy's +0.126R (p 0.27). In-sample (2004-2020) the pullback timing
did beat every null (p <= 0.001, +0.065R over random D1-bias timing) -- that
did not carry into OOS. By year: 17/22 positive, longs +0.167R, shorts
+0.012R.

The H1 candidate (IS p 0.57) is inconsistent across windows; its 2000-seed
side-null run was stopped by Claude Code for low system memory before
finishing and was not restarted.

**VALID CANDIDATES: none.**

## Milestone 6 -- Option B: H4 mtf_pullback vs Buy & Hold gold (PRE-REGISTERED)

Criteria locked and committed BEFORE the comparison code was written or run.
One pass, no parameter changes; the result is reported whatever it is.

**Subject:** `mtf_pullback` on H4 with the H4 defaults in
`config/strategy_config.yaml` as of this commit (D1 EMA200 bias, EMA20
pullback, RR 2.0, 2.5 ATR stop cap, 3 ATR trail), behind Shield exactly as
configured (1% risk/trade, 5% daily halt, 20% DD kill), $10,000 start.

**Benchmark:** Buy & Hold gold on the same H4 bars: buy at the first bar's
ask with lot = $10,000 / (price x 100 oz), rounded down to 0.01 (1x notional,
unlevered, no rebalancing), mark at bid, sell at the last bar. No Shield.

**Windows:** IS 2004-06-11 -> 2020-02-17 and OOS 2020-02-17 -> 2026-10-02
(the existing 70/30 H4 split), each started fresh at $10,000.

**Costs (both sides):** spread 35 points; commission $6/lot round turn;
long swap -12.6 / short -4.6 points/lot/night, triple on Wednesday.
Two swap models, both required:
  1. *fixed* -- the demo's points/lot/night as given (as the user specified).
  2. *price-scaled* -- the same rate as a share of notional: points x
     (price / 4147.62), the 2026-10-04 reference price. Model 1 charges an
     unrealistic ~11.5%/yr to a 2004 long at $400 vs ~1.1%/yr today; model 2
     guards against that flattering the strategy.

**Metrics:** CAGR, max equity drawdown (intrabar, % of running peak),
Sharpe and Sortino (daily, annualized sqrt(252)), total return; strategy
also profit factor and trades.

**PASS requires ALL of, in BOTH windows and under BOTH swap models:**
  - DD:   strategy max DD <= 0.70 x B&H max DD (at least 30% lower)
  - CAGR: strategy CAGR >= 0.70 x B&H CAGR; if B&H CAGR <= 0, strategy
          CAGR >= B&H CAGR instead
Anything else = FAIL. A Shield KILL during a window is not excluded: the
strategy's numbers are whatever the full system produced.

### Option B result -- single pass, run 2026-10-04 (`skills/run_buy_hold_overlay.py`)

| Window | Swap | Strategy CAGR / DD / Sharpe | B&H CAGR / DD / Sharpe | DD <= 0.7x | CAGR >= 0.7x | Result |
|---|---|---|---|---|---|---|
| IS 2004-2020 | fixed | 3.00% / 20.16% / 0.54 (KILLED) | 7.50% / 43.31% / 0.65 | ok | FAIL (0.40x) | FAIL |
| OOS 2020-2026 | fixed | 4.00% / 19.23% / 0.60 | 13.83% / 30.48% / 0.77 | ok | FAIL (0.29x) | FAIL |
| IS 2004-2020 | price-scaled | 3.71% / 20.23% / 0.65 (KILLED) | 8.53% / 50.46% / 0.53 | ok | FAIL (0.43x) | FAIL |
| OOS 2020-2026 | price-scaled | 4.41% / 18.93% / 0.65 | 14.36% / 29.84% / 0.82 | ok | FAIL (0.31x) | FAIL |

**OVERALL: FAIL.** The drawdown criterion passed in all four cases; the
return criterion failed in all four (strategy kept 29-43% of B&H CAGR vs
the 70% required).

Reading it:
- Shield killed the strategy in IS (20% DD) after 389 trades; it sat flat
  for the rest of 2004-2020, which is part of the low IS CAGR.
- The lower drawdown comes mostly from holding less gold, not from dodging
  the bad periods: at 1% risk/trade the strategy is far below 1x notional
  much of the time. Its Sharpe (0.54-0.65) is below B&H's in 3 of 4 cases,
  so it does not deliver more return per unit of risk either. Roughly, a
  half-size buy & hold would have had ~half the DD with more CAGR than the
  strategy (back-of-envelope, not a tested result).
- PF 1.23-1.28 with ~45 trades/yr is real money-making but, per milestone
  5, mostly long-drift beta.

## Open questions / next step

- **Blocked:** port the real EA. Its .mq5 is not in the repo or in the MT5
  data folder (only `QuantMind/ZeroMQ_Listener.mq5` there; tester logs don't
  name it). The user needs to supply the file or its entry/exit rules.
- Done: random-entry null model (milestone 3). Any new candidate (including
  the ported EA) must show p < 0.05 vs its random twin on OOS before
  further work on it.
- Option B is closed (FAIL). If pursued further, the honest next question is
  "does it beat a matched-exposure buy & hold?" -- a NEW pre-registered test,
  not a retune of this one.
- Any future null must be side-matched (`--null side`, now the default):
  coin-flip nulls overstate edge for long-biased strategies on gold.
- Lower cost drag is the cheapest lever: wider stops / fewer trades shrink
  spread+swap in R terms, and a raw-spread/commission account changes the
  floor. Check the demo account's actual spread before assuming 30 points.
- At $1,000 with 1% risk, most ATR-stop trades are rejected (0.01 lot
  needs ~$10 or less of risk). Raising `risk_per_trade_pct` toward the 2%
  ceiling is a Shield change the user must make themselves.
