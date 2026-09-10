"""
Kaggle Setup Script

Run this in a Kaggle notebook to set up the ICT backtest environment.
This script handles cloning, data setup, and dependency installation.
"""

import os
import sys
from pathlib import Path

print("="*60)
print("ICT Backtest - Kaggle Setup")
print("="*60)

# Step 1: Clone repository (if not already cloned)
print("\n[1/5] Checking repository...")
if not Path('resources').exists():
    print("Cloning repository...")
    # Replace with your actual repository URL
    repo_url = input("Enter your GitHub repository URL (or press Enter to skip): ").strip()
    if repo_url:
        os.system(f"git clone {repo_url}")
    else:
        print("Skipping clone. Assuming repository already exists.")
else:
    print("✓ Repository already exists")

# Step 2: Change to project directory
print("\n[2/5] Changing to project directory...")
os.chdir('resources')
print(f"✓ Current directory: {os.getcwd()}")

# Step 3: Install dependencies
print("\n[3/5] Installing dependencies...")
print("Installing/Upgrading vectorbt...")
os.system("pip install vectorbt --upgrade --quiet")
print("Installing plotly 5.11.0 (compatible version)...")
os.system("pip install plotly==5.11.0 --quiet")
print("✓ Dependencies installed")

# Step 4: Setup data directory
print("\n[4/5] Setting up data directory...")
Path('data').mkdir(exist_ok=True)

# Check if data exists
data_files = list(Path('data').glob('*.parquet'))
if data_files:
    print(f"✓ Found {len(data_files)} data files in data/")
    for f in data_files[:5]:  # Show first 5
        print(f"  - {f.name}")
else:
    print("⚠ No data files found in data/")
    print("Please upload your parquet files to:")
    print("  1. Kaggle Datasets (recommended)")
    print("  2. Direct upload to notebook")
    print("\nAfter uploading, copy files to data/ directory:")
    print("  !cp -r /kaggle/input/your-dataset/* data/")

# Step 5: Verify installation
print("\n[5/5] Verifying installation...")
try:
    import vectorbt as vbt
    print(f"✓ VectorBT version: {vbt.__version__}")
except ImportError:
    print("✗ VectorBT not found. Installation may have failed.")

try:
    import plotly
    print(f"✓ Plotly version: {plotly.__version__}")
except ImportError:
    print("✗ Plotly not found.")

try:
    import pandas as pd
    print(f"✓ Pandas version: {pd.__version__}")
except ImportError:
    print("✗ Pandas not found.")

try:
    import numpy as np
    print(f"✓ NumPy version: {np.__version__}")
except ImportError:
    print("✗ NumPy not found.")

print("\n" + "="*60)
print("Setup Complete!")
print("="*60)
print("\nNext steps:")
print("1. Ensure data files are in data/ directory")
print("2. Run a test backtest:")
print("   python run_single_strategy.py --strategy fvg_ce_entry")
print("3. Or run all strategies:")
print("   python run_all_strategies.py --start-date 2024-01-01 --end-date 2024-03-31")
print("="*60)
