# Falsifying "edge" in XAUUSD strategies: random-entry nulls, hard risk limits, NO-GO

A research project that tried to find a tradable edge in gold (XAUUSD) on MT5 data
and **did not find one**. The repository shows how each candidate was rejected:

- a **random-entry null model** that copies everything about a strategy except
  *when* it enters,
- a **bar-by-bar backtest engine** with deliberately pessimistic fills, and
- **Shield**, a pre-trade risk layer whose limits cannot be loosened by config.

The most useful result is a near miss. A strategy passed the usual null test and then
failed a stricter one, because what looked like an edge was gold's bull market.

| | |
|---|---|
| Data | Real XAUUSD bars from MetaQuotes-Demo: M15 2022-2026 (99k), H1 2009-2026 (99k), H4 2004-2026 (34k) |
| Candidates | Trend (EMA/ADX/ATR), multi-timeframe pullback, session breakout, Bollinger/RSI mean reversion, on M15/H1/H4 |
| Protocol | 70/30 in-sample/out-of-sample split, parameters tuned in-sample only, scored once out-of-sample |
| Gate | Out-of-sample p < 0.05 against a random twin, with a multiple-testing haircut |
| Verdict | **No valid candidate. Also failed a pre-registered comparison against buy & hold.** |

## The near miss: a coin-flip null overstates edge on a trending asset

`mtf_pullback` on H4 (daily EMA200 bias, H4 pullback entry) looked like a winner against
a 50/50 coin-flip null. It is 77% long. Over a 2020-2026 window in which gold more than
doubled, a random strategy with the same long share does almost as well:

| Null model (2,000 seeds) | Random OOS avg R [p05, p95] | Strategy OOS avg R | p |
|---|---|---:|---:|
| coin flip (50/50 side) | +0.007 [-0.091, +0.111] | +0.126 | 0.032 |
| **side-matched** (77% long) | +0.092 [-0.000, +0.182] | +0.126 | **0.272** |
| bias-matched (daily side, random timing) | +0.094 [+0.040, +0.149] | +0.126 | **0.171** |

The out-of-sample "edge" was long-drift beta. About 19 out-of-sample tests were run in
that round, so a Bonferroni threshold of about 0.003 applied anyway. Since then,
side-matched nulls are the default (`--null side`).

## What the null model is

[`core/strategies/random_entry.py`](gold_trading_system/core/strategies/random_entry.py)
builds a **random twin** for each strategy. The twin has the same entry rate, the same
median stop in ATR units, the same R:R, chandelier trail, costs, engine and Shield.
Only entry timing (and optionally side) is random. Then `p` = the share of seeds whose
average R is at least the strategy's. With 100 seeds, anything near p < 0.05 is re-run
with 2,000 seeds ([`skills/run_random_benchmark.py`](gold_trading_system/skills/run_random_benchmark.py)).

Other findings from the benchmark:

- **Costs are about -0.05R per trade.** The same random profile earns +0.002R with
  zero costs and -0.044R with 35-point spread, commission and swap (measured on the
  demo account). A real entry edge must clear that before it shows any profit.
- **Zero edge plus many trades means a guaranteed kill.** Random twins of a strategy
  that fires on about 13% of bars hit the 20% drawdown kill in 98-100% of seeds.
  Trade frequency is a risk in its own right when the edge is near zero.
- **Filters that "reduce drawdown" mostly reduce trades.** ADX/EMA200/ATR filters cut
  drawdown by trading less, not by adding edge.

## Backtest engine: pessimistic by design

[`core/backtester/m15_engine.py`](gold_trading_system/core/backtester/m15_engine.py)

- The signal is read on a **closed** bar and filled at the **next bar's open**.
  Higher-timeframe bias uses only higher-timeframe bars already closed at the current
  close. A test checks that truncating future bars never changes a past signal.
- MT5 bars are bid prices. Longs enter at the ask and exit at the bid. Spread is
  `max(bar spread, floor)`.
- If one bar touches both stop and target, the **stop fills first**. A bar that gaps
  through the stop fills at the open, not at the stop price.
- Commission per lot, and nightly swap with triple swap on Wednesday. A price-scaled
  swap option prevents fixed-point swap from distorting 2004-era prices.
- MT5-style margin checks and stop-out.

## Shield: risk limits that config cannot loosen

[`core/risk_guardrails/`](gold_trading_system/core/risk_guardrails/)

- `HARD_*` ceilings are module constants: 2% risk per trade, 5% daily loss, 20%
  drawdown, R:R >= 1.5, spread cap, open-risk cap. The YAML config loads into a frozen
  Pydantic model that **rejects any value looser than its ceiling**, so config can
  only tighten.
- Position sizing **rejects** a trade instead of rounding up to the broker's minimum
  lot. Rounding up would silently turn a 1% risk into 10%+ on a small account.
- `CircuitBreaker`: the daily loss halt resets the next server day. The drawdown kill
  is latched and only a human can reset it.
- Tests found a real bug: R:R computed from float prices rejected about 33% of trades
  at exactly the 1.5R minimum. It was fixed with a regression test.

### Risk-limit policy

Only a human, reviewed code change may raise a `HARD_*` constant. No strategy, script or
config file can do it.

## Pre-registered final check: does it beat buy & hold?

The criteria were committed before the comparison code was written. Pass required, in
both windows and under both swap models: strategy max drawdown at most 0.7× buy & hold,
**and** CAGR at least 0.7× buy & hold.

| Window | Swap | Strategy CAGR / max DD | Buy & hold CAGR / max DD | Result |
|---|---|---|---|---|
| 2004-2020 | fixed | 3.00% / 20.2% (killed) | 7.50% / 43.3% | FAIL (0.40× CAGR) |
| 2020-2026 | fixed | 4.00% / 19.2% | 13.83% / 30.5% | FAIL (0.29×) |
| 2004-2020 | price-scaled | 3.71% / 20.2% (killed) | 8.53% / 50.5% | FAIL (0.43×) |
| 2020-2026 | price-scaled | 4.41% / 18.9% | 14.36% / 29.8% | FAIL (0.31×) |

The lower drawdown came mostly from holding less gold, not from avoiding bad periods.
Sharpe was below buy & hold in 3 of 4 cases.

## Layout

```
gold_trading_system/
  core/strategies/        indicators, candidate strategies, random-entry twin
  core/backtester/        bar-by-bar engine + metrics
  core/risk_guardrails/   Shield validator and circuit breaker
  core/data_ingestion/    MT5 history download / CSV cache
  config/                 broker costs, risk limits (tighten-only), strategy grids
  skills/                 tournament, random benchmark, buy & hold overlay (CLIs)
  tests/                  Shield, engine fill and look-ahead tests
  reports/                STATE_SNAPSHOT.md (full research log) + generated tables
```

[`reports/STATE_SNAPSHOT.md`](gold_trading_system/reports/STATE_SNAPSHOT.md) is the
unedited research log, milestone by milestone, including dead ends.

## Running

```bash
pip install -r gold_trading_system/requirements.txt
pytest gold_trading_system/tests          # no data needed
# Backtests need XAUUSD history. Download it from a running, logged-in MT5 terminal
# (Windows); price data is not redistributed here.
python gold_trading_system/skills/run_backtest_tournament.py --timeframe H4
python gold_trading_system/skills/run_random_benchmark.py --timeframe H4 --null side
```
