# Backtest Run Scripts

This directory contains scripts for running ICT strategy backtests.

## Available Scripts

### 1. `run_single_strategy.py`

Run a single strategy backtest with the BacktestAgent.

**Usage:**
```bash
python run_single_strategy.py --strategy fvg_ce_entry
```

**Options:**
- `--strategy`: Strategy ID (required)
  - Available: fvg_ce_entry, order_block_entry, ict_2022_model, ote_pd_array, judas_swing, asian_range_sweep, bread_and_butter, ict_2023_model, ict_2024_model, silver_bullet_ny_am, silver_bullet_london, unicorn, venom, london_close_reversal, ny_pm_reversal
- `--start-date`: Start date (optional, e.g., "2024-01-01")
- `--end-date`: End date (optional, e.g., "2024-12-31")
- `--no-save`: Don't save results to JSON file

**Examples:**
```bash
# Run FVG/CE strategy with default date range
python run_single_strategy.py --strategy fvg_ce_entry

# Run Silver Bullet NY AM with specific date range
python run_single_strategy.py --strategy silver_bullet_ny_am --start-date 2024-01-01 --end-date 2024-03-31

# Run without saving results
python run_single_strategy.py --strategy ict_2022_model --no-save
```

### 2. `run_all_strategies.py`

Run backtests for all 15 ICT strategies with comprehensive summary.

**Usage:**
```bash
python run_all_strategies.py
```

**Options:**
- `--start-date`: Start date (optional, e.g., "2024-01-01")
- `--end-date`: End date (optional, e.g., "2024-12-31")
- `--no-save`: Don't save individual results to JSON files
- `--skip-on-error`: Continue running strategies even if one fails

**Examples:**
```bash
# Run all strategies with default date range
python run_all_strategies.py

# Run all strategies for Q1 2024
python run_all_strategies.py --start-date 2024-01-01 --end-date 2024-03-31

# Run without saving individual results (saves summary only)
python run_all_strategies.py --no-save

# Continue on error (don't stop if one strategy fails)
python run_all_strategies.py --skip-on-error
```

**Output:**
- Individual strategy results saved to `results/{strategy_id}_{timestamp}.json`
- Summary table printed to console
- Summary saved to `results/backtest_summary_{timestamp}.json`

### 3. `kaggle_setup.py`

Setup script for Kaggle notebooks.

**Usage in Kaggle:**
```python
# In a Kaggle notebook cell
%run kaggle_setup.py
```

**What it does:**
1. Clones the repository (if not already present)
2. Changes to project directory
3. Installs/updates dependencies (vectorbt, plotly)
4. Sets up data directory
5. Verifies installation

## Prerequisites

### Data Files

Ensure parquet data files exist in the `data/` directory:

```
data/
  xauusd_5min.parquet
  xauusd_1h.parquet
  xauusd_1D.parquet
```

**Filename formats supported:**
- `XAUUSD_5m.parquet` (uppercase, 'm' suffix)
- `xauusd_5min.parquet` (lowercase, 'min' suffix)
- Both formats are handled automatically

### Python Dependencies

Required packages:
- Python 3.8+
- pandas
- numpy
- vectorbt
- pytz
- plotly

Install with:
```bash
pip install pandas numpy vectorbt pytz plotly==5.11.0
```

## Output Files

### Individual Strategy Results

Saved to `results/` directory with format:
```
results/
  fvg_ce_entry_20240910_153045.json
  silver_bullet_ny_am_20240910_153105.json
  ...
```

### Summary Results

Saved to `results/` directory with format:
```
results/
  backtest_summary_20240910_153045.json
```

Summary JSON structure:
```json
{
  "timestamp": "20240910_153045",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "strategies_tested": 15,
  "strategies_successful": 15,
  "strategies_failed": 0,
  "results": [...]
}
```

## Quick Start

### Windows (Command Prompt)
```cmd
cd C:\Users\Spirt Embassy\Documents\GitHub\resources
python run_single_strategy.py --strategy fvg_ce_entry
```

### Windows (PowerShell)
```powershell
cd "C:\Users\Spirt Embassy\Documents\GitHub\resources"
python run_single_strategy.py --strategy fvg_ce_entry
```

### Linux/Mac
```bash
cd /path/to/resources
python run_single_strategy.py --strategy fvg_ce_entry
```

### Kaggle Notebook
```python
# In a Kaggle notebook cell
%run kaggle_setup.py
%run run_all_strategies.py --start-date 2024-01-01 --end-date 2024-03-31
```

## Troubleshooting

### ModuleNotFoundError

**Error:** `ModuleNotFoundError: No module named 'vectorbt'`

**Solution:**
```bash
pip install vectorbt plotly==5.11.0
```

### FileNotFoundError

**Error:** `FileNotFoundError: No matching parquet file found`

**Solution:**
- Ensure data files exist in `data/` directory
- Check filename format (case-insensitive, accepts both '5m' and '5min')
- Upload data files if missing

### Plotly Compatibility Error

**Error:** `ValueError: Invalid property specified ... 'scattermapbox'`

**Solution:**
```bash
pip install plotly==5.11.0
```

### Zero Trades Generated

**Problem:** Backtest runs but shows 0 trades

**Possible causes:**
- Date range too narrow
- Data doesn't cover required timeframe
- Strategy conditions too strict

**Solution:**
- Expand date range
- Check data coverage
- Relax strategy parameters
- Verify killzone times match data timezone

## Advanced Usage

### Running from Python Script

```python
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from run_single_strategy import run_strategy

# Run a strategy
results = run_strategy(
    strategy_id="fvg_ce_entry",
    start_date="2024-01-01",
    end_date="2024-03-31",
    save_results=True
)

# Access results
print(f"Total Trades: {results['aggregate_metrics']['total_trades']}")
```

### Custom Date Ranges

```python
# Backtest a specific quarter
python run_all_strategies.py --start-date 2024-01-01 --end-date 2024-03-31

# Backtest a specific month
python run_all_strategies.py --start-date 2024-02-01 --end-date 2024-02-29

# Backtest from a date onwards
python run_all_strategies.py --start-date 2024-06-01

# Backtest up to a date
python run_all_strategies.py --end-date 2024-12-31
```

### Batch Processing

Run multiple date ranges in sequence:

```bash
# Create a batch script
for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
    python run_all_strategies.py --start-date 2024-${month}-01 --end-date 2024-${month}-31
done
```

## Performance Tips

1. **Use shorter date ranges for testing**
   - Full year may take considerable time
   - Start with Q1 (3 months) to verify setup

2. **Skip strategies on error if desired**
   - Use `--skip-on-error` to continue despite failures
   - Useful for identifying problematic strategies

3. **Disable saving for quick tests**
   - Use `--no-save` to skip JSON file writing
   - Faster for quick validation

4. **Monitor memory usage**
   - Large datasets may exceed memory limits
   - Use date filtering to reduce data size

## Best Practices

1. **Always verify data files exist** before running backtests
2. **Start with simple strategies** (FVG/CE, Order Block) before complex ones
3. **Use date range filtering** to test specific periods
4. **Check validation results** before trusting metrics
5. **Review individual trade records** to understand behavior
6. **Save results** for reproducibility and comparison
7. **Document your configurations** for future reference

## Additional Resources

- `BACKTEST_GUIDE.md` - Comprehensive user guide
- `IMPLEMENTATION_DOCUMENTATION.md` - Technical documentation
- `adapters/README.md` - Adapter pattern documentation
- `ICT-UNIFIED-TRADING-BOOK.md` - Strategy specifications
