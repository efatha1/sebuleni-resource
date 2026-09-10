"""
Kaggle Notebook Template for ICT Backtests

Copy this entire file into a Kaggle notebook cell to run backtests.
"""

# Cell 1: Setup
print("="*60)
print("ICT Backtest - Kaggle Notebook")
print("="*60)

# Clone repository (update URL if needed)
import os
if not os.path.exists('resources'):
    print("Cloning repository...")
    os.system('git clone https://github.com/YOUR_USERNAME/resources.git')
else:
    print("Repository already exists")

# Change to project directory
os.chdir('resources')

# Install dependencies
print("Installing dependencies...")
os.system('pip install vectorbt --upgrade --quiet')
os.system('pip install plotly==5.11.0 --quiet')

# Setup data directory
os.makedirs('data', exist_ok=True)

# Copy data from Kaggle input (update dataset name)
print("Copying data files...")
# Uncomment and update with your dataset name
# os.system('cp -r /kaggle/input/your-dataset-name/* data/')

print("Setup complete!")
print("="*60)

# Cell 2: Verify Data
import os
from pathlib import Path

print("\nChecking data files...")
data_dir = Path('data')
if data_dir.exists():
    files = list(data_dir.glob('*.parquet'))
    if files:
        print(f"Found {len(files)} data files:")
        for f in files:
            print(f"  - {f.name}")
    else:
        print("⚠ No data files found in data/")
        print("Please upload data files to Kaggle and copy to data/ directory")
else:
    print("⚠ data/ directory not found")

# Cell 3: Run Test Backtest
import sys
sys.path.insert(0, '/kaggle/working/resources')

from backtest_agent import BacktestAgent
from strategies.fvg_ce_entry.config import FVGCEConfig

print("\n" + "="*60)
print("Running Test Backtest: FVG/CE Entry")
print("="*60)

agent = BacktestAgent("fvg_ce_entry", "1.0")
cfg = FVGCEConfig()
cfg.start_date = "2024-01-01"
cfg.end_date = "2024-03-31"  # Shorter range for testing

try:
    results = agent.run_backtest(
        strategy_module=sys.modules[__name__],
        config=cfg,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        save_results=True
    )

    print(f"\nResults:")
    print(f"Total Trades: {results['aggregate_metrics']['total_trades']}")
    print(f"Win Rate: {results['aggregate_metrics']['win_rate']:.2%}")
    print(f"Profit Factor: {results['aggregate_metrics']['profit_factor']:.2f}")
    print(f"Validation: {'PASSED' if results['validation']['passed'] else 'FAILED'}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Cell 4: Run All Strategies (Optional)
# Uncomment to run all 15 strategies
"""
import sys
sys.path.insert(0, '/kaggle/working/resources')

from run_all_strategies import run_all_strategies

print("\n" + "="*60)
print("Running All 15 Strategies")
print("="*60)

results = run_all_strategies(
    start_date="2024-01-01",
    end_date="2024-03-31",
    save_results=True,
    skip_on_error=True
)
"""

# Cell 5: Copy Results to Working Directory
import shutil
from pathlib import Path

print("\n" + "="*60)
print("Copying Results")
print("="*60)

# Copy results to working directory for download
if Path('results').exists():
    shutil.copytree('results', '/kaggle/working/results', dirs_exist_ok=True)
    print("✓ Results copied to /kaggle/working/results/")
    print("Download from the output tab")
else:
    print("No results directory found")

print("="*60)
print("Notebook execution complete!")
print("="*60)
