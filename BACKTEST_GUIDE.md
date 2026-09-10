# ICT Strategy Backtest Guide

This guide provides comprehensive instructions for running, interpreting, and customizing backtests using the VECTORBT BACKTEST AGENT implementation.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Running Backtests](#running-backtests)
3. [Interpreting Results](#interpreting-results)
4. [Date Range Filtering](#date-range-filtering)
5. [Customizing Output](#customizing-output)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Python 3.8+
- Required packages: pandas, numpy, vectorbt, pytz
- Parquet data files in `data/` directory

### Run Your First Backtest

```python
from backtest_agent import BacktestAgent
from strategies.fvg_ce_entry.config import FVGCEConfig
import sys

# Initialize agent
agent = BacktestAgent("fvg_ce_entry", "1.0")

# Configure strategy
cfg = FVGCEConfig()

# Run backtest
results = agent.run_backtest(
    strategy_module=sys.modules[__name__],
    config=cfg,
    save_results=True
)

# Print results
print(f"Total Trades: {results['aggregate_metrics']['total_trades']}")
print(f"Win Rate: {results['aggregate_metrics']['win_rate']}")
print(f"Profit Factor: {results['aggregate_metrics']['profit_factor']}")
```

### Run from Command Line

```bash
cd strategies/fvg_ce_entry
python strategy.py
```

---

## Running Backtests

### Using BacktestAgent (Recommended)

The `BacktestAgent` provides a unified interface for all 15 strategies:

```python
from backtest_agent import BacktestAgent
from strategies.silver_bullet_ny_am.config import SilverBulletNYAMConfig
import sys

# Initialize agent with strategy ID
agent = BacktestAgent("silver_bullet_ny_am", "1.0")

# Configure strategy
cfg = SilverBulletNYAMConfig()
cfg.init_cash = 100000.0
cfg.risk_pct = 0.01

# Run backtest
results = agent.run_backtest(
    strategy_module=sys.modules[__name__],
    config=cfg,
    start_date="2024-01-01",
    end_date="2024-12-31",
    save_results=True
)
```

### Available Strategies

| Strategy ID | Strategy Name | Adapter |
|-------------|---------------|---------|
| fvg_ce_entry | FVG/CE Entry | None (simple) |
| order_block_entry | Order Block Entry | None (simple) |
| ict_2022_model | ICT 2022 Model | None (simple) |
| ote_pd_array | OTE + PD Array Entry | None (simple) |
| judas_swing | Judas Swing Entry | JudasSwingAdapter |
| asian_range_sweep | Asian Range Sweep | AsianRangeSweepAdapter |
| bread_and_butter | Bread-and-Butter Setup | None (simple) |
| ict_2023_model | ICT 2023 Model | None (simple) |
| ict_2024_model | ICT 2024 Model | ICT2024Adapter |
| silver_bullet_ny_am | Silver Bullet (NY AM) | SilverBulletNYAMAdapter |
| silver_bullet_london | Silver Bullet (London) | SilverBulletLondonAdapter |
| unicorn | Unicorn | UnicornAdapter |
| venom | Venom Model | VenomAdapter |
| london_close_reversal | London Close Reversal | None (simple) |
| ny_pm_reversal | NY PM Reversal | None (simple) |

### Strategy-Specific Configuration

Each strategy has its own config class with specific parameters:

```python
# Silver Bullet NY AM
from strategies.silver_bullet_ny_am.config import SilverBulletNYAMConfig
cfg = SilverBulletNYAMConfig()
cfg.tp1_r = 1.5  # TP1 at 1.5R
cfg.tp1_close_pct = 0.33  # Close 33% at TP1
cfg.tp2_r = 2.0  # TP2 at 2.0R
cfg.tp2_close_pct = 0.33  # Close 33% at TP2
cfg.runner_pct = 0.34  # Hold 34% as runner

# Unicorn
from strategies.unicorn.config import UnicornConfig
cfg = UnicornConfig()
cfg.tp1_r = 2.0  # TP1 at 2.0R
cfg.tp1_close_pct = 0.25  # Close 25% at TP1
cfg.tp2_r = 4.0  # TP2 at 4.0R
cfg.tp2_close_pct = 0.25  # Close 25% at TP2
cfg.expected_r = 8.0  # Expected R multiple
```

---

## Interpreting Results

### Aggregate Metrics

The `aggregate_metrics` section provides a performance summary:

```json
{
  "aggregate_metrics": {
    "total_trades": 150,
    "win_rate": 0.45,
    "profit_factor": 1.2,
    "expectancy_R": 0.8,
    "net_profit": 5000.0,
    "max_drawdown": -0.05,
    "sharpe": 1.5,
    "sortino": 2.0
  }
}
```

**Key Metrics Explained:**

- **total_trades**: Number of completed trades
  - Higher is generally better (more data points)
  - Too low (< 20) may indicate insufficient data

- **win_rate**: Percentage of winning trades (0-1)
  - 0.45 = 45% win rate
  - ICT strategies typically target 40-60% win rate
  - High win rate alone doesn't guarantee profitability

- **profit_factor**: Gross profit / gross loss
  - > 1.0 = profitable
  - > 1.5 = good
  - > 2.0 = excellent
  - Accounts for both win rate and R-multiples

- **expectancy_R**: Mean R-multiple per trade
  - Positive = profitable
  - > 0.5 = good
  - > 1.0 = excellent
  - Shows average reward-to-risk

- **net_profit**: Total realized PnL
  - Positive = profitable
  - In currency units (e.g., dollars)

- **max_drawdown**: Maximum drawdown (negative)
  - -0.05 = 5% drawdown
  - Lower magnitude is better
  - Shows worst-case loss

- **sharpe**: Risk-adjusted return (Sharpe ratio)
  - > 1.0 = acceptable
  - > 2.0 = good
  - > 3.0 = excellent
  - Higher is better

- **sortino**: Downside risk-adjusted return
  - Similar to Sharpe but only penalizes downside
  - Higher is better

### Trade Records

The `trades` section contains detailed information for each trade:

```json
{
  "trade_id": 0,
  "entry_time": "2024-01-15T10:00:00Z",
  "exit_time": "2024-01-15T10:30:00Z",
  "direction": "LONG",
  "entry": 2015.50,
  "stop": 2010.00,
  "target": 2025.00,
  "exit": 2025.00,
  "R_multiple": 2.0,
  "PnL": 9.50,
  "MAE": -2.50,
  "MFE": 10.00,
  "MAE_R": -0.5,
  "MFE_R": 2.0,
  "duration": 30,
  "exit_reason": "TAKE_PROFIT",
  "partial_exits": null
}
```

**Key Fields:**

- **exit_reason**: How the trade exited
  - "TAKE_PROFIT": Hit target
  - "STOP_LOSS": Hit stop loss
  - "OTHER": End of data or other reason

- **MAE** (Maximum Adverse Excursion): Worst price against position
  - Shows how much the trade went against you
  - In price units (dollars for XAUUSD)

- **MFE** (Maximum Favorable Excursion): Best price for position
  - Shows how much the trade went in your favor
  - In price units

- **MAE_R** / **MFE_R**: MAE/MFE in R units
  - Shows adverse/favorable excursion relative to risk
  - Useful for assessing trade quality

- **partial_exits**: For multi-target strategies (Silver Bullet, Unicorn)
  - Array of partial exit records
  - Each entry shows target hit, price, time, and size

### Market State

The `market_state` section captures market conditions at each entry:

```json
{
  "entry_time": "2024-01-15T10:00:00Z",
  "core_state": {
    "HTF_bias": "LONG",
    "LTF_bias": "LONG",
    "session": "NY_AM",
    "kill_zone": "ny_am"
  },
  "strategy_specific_state": {
    "FVG": {
      "present": true,
      "direction": "long",
      "high": 2018.00,
      "low": 2015.00,
      "ce": 2016.50
    }
  },
  "used_vs_observed": {
    "HTF_bias": {"observed_at_entry": true, "used_by_strategy": true},
    "FVG": {"observed_at_entry": true, "used_by_strategy": true}
  }
}
```

**Understanding used_vs_observed:**

- `observed_at_entry`: Concept was present at entry time
- `used_by_strategy`: Strategy used this concept in entry logic

This distinction is critical for research:
- If `used_by_strategy: true` but `observed_at_entry: false` → potential look-ahead bias
- If `observed_at_entry: true` but `used_by_strategy: false` → confounding factor

### Validation Results

The `validation` section shows validation check results:

```json
{
  "validation": {
    "passed": true,
    "lookahead_check": "PASS",
    "timestamp_check": "PASS",
    "data_integrity": "PASS",
    "signal_integrity": "PASS",
    "execution_integrity": "PASS"
  }
}
```

**If validation fails:**
- Do not trust the results
- Check the failed check for specific issues
- Fix the issue and re-run

---

## Date Range Filtering

### Setting Date Ranges

Filter backtests by date range using config fields:

```python
cfg = FVGCEConfig()
cfg.start_date = "2024-01-01"  # Start date (inclusive)
cfg.end_date = "2024-06-30"    # End date (inclusive)
```

### Supported Formats

- **Date-only**: "2024-01-01"
  - Interpreted as midnight UTC

- **Date-time**: "2024-01-01T00:00:00Z"
  - Explicit time with timezone

- **None**: No filtering
  - Uses all available data

### Examples

```python
# Backtest 2024 Q1
cfg.start_date = "2024-01-01"
cfg.end_date = "2024-03-31"

# Backtest a specific month
cfg.start_date = "2024-02-01"
cfg.end_date = "2024-02-29"

# Backtest from a specific date onwards
cfg.start_date = "2024-06-01"
cfg.end_date = None  # No end date

# Backtest up to a specific date
cfg.start_date = None  # No start date
cfg.end_date = "2024-12-31"
```

### Timezone Handling

- All date ranges are normalized to UTC
- Data timestamps are assumed to be UTC
- Killzone detection converts to New York time internally

---

## Customizing Output

### JSON Output Location

Results are saved to timestamped JSON files in the `results/` directory:

```
results/
  fvg_ce_entry_20240910_153045.json
  silver_bullet_ny_am_20240910_153105.json
```

Filename format: `{strategy_id}_{timestamp}.json`

### Disabling JSON Output

If you don't want to save results to file:

```python
results = agent.run_backtest(
    strategy_module=sys.modules[__name__],
    config=cfg,
    save_results=False  # Don't save to file
)
```

### Accessing Results Programmatically

Results are returned as a Python dictionary:

```python
results = agent.run_backtest(...)

# Access aggregate metrics
total_trades = results['aggregate_metrics']['total_trades']
win_rate = results['aggregate_metrics']['win_rate']

# Access trade records
for trade in results['trades']:
    print(f"Trade {trade['trade_id']}: {trade['PnL']}")

# Access market state
for state in results['market_state']:
    print(f"Entry at {state['entry_time']}: HTF bias = {state['core_state']['HTF_bias']}")

# Check validation
if results['validation']['passed']:
    print("Validation passed")
else:
    print("Validation failed")
```

### Exporting to CSV

You can export trade records to CSV for analysis:

```python
import pandas as pd

results = agent.run_backtest(...)
trades_df = pd.DataFrame(results['trades'])
trades_df.to_csv('trades.csv', index=False)
```

### Custom Metric Calculation

Add custom metrics from the results:

```python
results = agent.run_backtest(...)

# Calculate custom metrics
trades = results['trades']
winning_trades = [t for t in trades if t['PnL'] > 0]
losing_trades = [t for t in trades if t['PnL'] < 0]

avg_win = sum(t['PnL'] for t in winning_trades) / len(winning_trades)
avg_loss = sum(t['PnL'] for t in losing_trades) / len(losing_trades)

print(f"Average Win: ${avg_win:.2f}")
print(f"Average Loss: ${avg_loss:.2f}")
print(f"Reward/Risk Ratio: {abs(avg_win / avg_loss):.2f}")
```

---

## Troubleshooting

### Common Issues

#### 1. FileNotFoundError: Data file not found

**Error:**
```
FileNotFoundError: No matching parquet file found for XAUUSD_5m
```

**Solution:**
- Ensure parquet files exist in `data/` directory
- Check filename format (case-insensitive, accepts both "XAUUSD_5m.parquet" and "xauusd_5min.parquet")
- Create sample data for testing:
  ```python
  from data_loader import create_sample_data
  df = create_sample_data("XAUUSD", "5min", "2024-01-01", "2024-01-31")
  df.to_parquet("data/xauusd_5min.parquet")
  ```

#### 2. ValueError: Invalid config for strategy

**Error:**
```
ValueError: Invalid config for silver_bullet_ny_am
```

**Solution:**
- Ensure config has all required attributes
- Check strategy-specific config class for required fields
- Example for Silver Bullet:
  ```python
  cfg = SilverBulletNYAMConfig()
  cfg.tp1_r = 1.5
  cfg.tp1_close_pct = 0.33
  cfg.tp2_r = 2.0
  cfg.tp2_close_pct = 0.33
  cfg.runner_pct = 0.34
  ```

#### 3. Zero trades generated

**Problem:** Backtest runs but `total_trades: 0`

**Possible causes:**
- Date range too narrow
- Data doesn't cover strategy's required timeframe
- Strategy conditions too strict
- No matching killzone periods

**Solutions:**
- Expand date range
- Check data coverage
- Relax strategy parameters (e.g., `min_fvg_gap`)
- Verify killzone times match data timezone

#### 4. Validation failed

**Problem:** `validation.passed: false`

**Solution:**
- Check which specific check failed
- Read the error message in the failed check
- Common issues:
  - **lookahead_check**: Signal uses future data
  - **timestamp_check**: Timestamps not ordered
  - **data_integrity**: Null values or invalid OHLC
  - **signal_integrity**: Signal generation error
  - **execution_integrity**: Trade execution error

#### 5. Plotly/VectorBT compatibility error

**Error:**
```
ValueError: Invalid property specified for object of type plotly.graph_objs.layout.template.Data: 'scattermapbox'
```

**Solution:**
This is a plotly/vectorbt version incompatibility. Downgrade plotly:

```bash
pip install plotly==5.11.0
```

Or upgrade both:
```bash
pip install --upgrade vectorbt plotly
```

#### 6. Memory error with large datasets

**Problem:** Out of memory when loading large parquet files

**Solution:**
- Use date range filtering to load less data
- Reduce timeframe resolution (e.g., use 15min instead of 1min)
- Process data in chunks
- Increase system memory

#### 7. Partial exits not recorded

**Problem:** `partial_exits` is null for multi-target strategies

**Solution:**
- Ensure strategy uses `from_order_func` (not `from_signals`)
- Check that `order_func` writes to state tracker
- Verify `get_order_func_state_tracker()` is imported in strategy
- Example:
  ```python
  from backtest_agent import get_order_func_state_tracker

  def order_func(context, cfg):
      state_tracker = get_order_func_state_tracker()
      # ... existing logic ...
      state['partial_exits'].append({...})
      state_tracker[idx] = state
  ```

### Debug Mode

For detailed debugging, enable verbose output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

agent = BacktestAgent("fvg_ce_entry", "1.0")
results = agent.run_backtest(...)
```

### Getting Help

If issues persist:
1. Check `IMPLEMENTATION_DOCUMENTATION.md` for detailed technical docs
2. Check `adapters/README.md` for adapter-specific information
3. Review strategy-specific config and implementation files
4. Verify data quality and coverage
5. Check vectorbt and dependency versions

---

## Best Practices

1. **Always check validation results** before trusting metrics
2. **Use date range filtering** to test specific periods
3. **Save results to JSON** for reproducibility and analysis
4. **Review trade records** to understand individual trade behavior
5. **Check market state** to verify entry conditions
6. **Start with simple strategies** (FVG/CE, Order Block) before complex ones
7. **Use consistent parameters** across runs for comparison
8. **Document your configurations** for reproducibility
9. **Validate data quality** before running backtests
10. **Review MAE/MFE** to assess trade quality beyond simple win/loss

---

## Additional Resources

- **IMPLEMENTATION_DOCUMENTATION.md**: Technical implementation details
- **adapters/README.md**: Adapter pattern documentation
- **ICT-UNIFIED-TRADING-BOOK.md**: Strategy specifications
- **ict_signals.py**: Shared signal primitives documentation
- **data_loader.py**: Data loading utilities
