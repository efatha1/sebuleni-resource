"""
Run Single Strategy Backtest

Simple script to run a single strategy backtest with the BacktestAgent.
Usage: python run_single_strategy.py --strategy fvg_ce_entry
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backtest_agent import BacktestAgent


def run_strategy(strategy_id: str, start_date: str = None, end_date: str = None, save_results: bool = True):
    """
    Run a single strategy backtest.

    Args:
        strategy_id: Strategy identifier (e.g., "fvg_ce_entry")
        start_date: Optional start date (e.g., "2024-01-01")
        end_date: Optional end date (e.g., "2024-12-31")
        save_results: Whether to save results to JSON file
    """
    # Strategy config mapping
    strategy_configs = {
        "fvg_ce_entry": ("strategies.fvg_ce_entry.config", "FVGCEConfig"),
        "order_block_entry": ("strategies.order_block_entry.config", "OrderBlockConfig"),
        "ict_2022_model": ("strategies.ict_2022_model.config", "ICT2022Config"),
        "ote_pd_array": ("strategies.ote_pd_array.config", "OTEPDArrayConfig"),
        "judas_swing": ("strategies.judas_swing.config", "JudasSwingConfig"),
        "asian_range_sweep": ("strategies.asian_range_sweep.config", "AsianRangeSweepConfig"),
        "bread_and_butter": ("strategies.bread_and_butter.config", "BreadAndButterConfig"),
        "ict_2023_model": ("strategies.ict_2023_model.config", "ICT2023Config"),
        "ict_2024_model": ("strategies.ict_2024_model.config", "ICT2024Config"),
        "silver_bullet_ny_am": ("strategies.silver_bullet_ny_am.config", "SilverBulletNYAMConfig"),
        "silver_bullet_london": ("strategies.silver_bullet_london.config", "SilverBulletLondonConfig"),
        "unicorn": ("strategies.unicorn.config", "UnicornConfig"),
        "venom": ("strategies.venom.config", "VenomConfig"),
        "london_close_reversal": ("strategies.london_close_reversal.config", "LondonCloseReversalConfig"),
        "ny_pm_reversal": ("strategies.ny_pm_reversal.config", "NYPMReversalConfig"),
    }

    if strategy_id not in strategy_configs:
        print(f"Error: Unknown strategy '{strategy_id}'")
        print(f"Available strategies: {', '.join(strategy_configs.keys())}")
        return None

    config_module, config_class = strategy_configs[strategy_id]

    print(f"{'='*60}")
    print(f"Running Backtest: {strategy_id}")
    print(f"{'='*60}")

    try:
        # Import config
        module = __import__(config_module, fromlist=[config_class])
        ConfigClass = getattr(module, config_class)

        # Initialize agent
        agent = BacktestAgent(strategy_id, "1.0")

        # Configure strategy
        cfg = ConfigClass()
        if start_date:
            cfg.start_date = start_date
        if end_date:
            cfg.end_date = end_date

        print(f"Symbol: {cfg.symbol}")
        print(f"Timeframe: {cfg.ltf_timeframe}")
        print(f"HTF Timeframe: {cfg.htf_timeframe}")
        print(f"Start Date: {cfg.start_date}")
        print(f"End Date: {cfg.end_date}")
        print(f"Initial Capital: ${cfg.init_cash:,.2f}")
        print(f"Risk: {cfg.risk_pct * 100}%")
        print(f"{'='*60}")

        # Run backtest
        results = agent.run_backtest(
            strategy_module=sys.modules[__name__],
            config=cfg,
            start_date=cfg.start_date,
            end_date=cfg.end_date,
            save_results=save_results
        )

        # Print results
        print(f"\n{'='*60}")
        print(f"Backtest Results")
        print(f"{'='*60}")
        print(f"Total Trades: {results['aggregate_metrics']['total_trades']}")
        print(f"Win Rate: {results['aggregate_metrics']['win_rate']:.2%}")
        print(f"Profit Factor: {results['aggregate_metrics']['profit_factor']:.2f}")
        print(f"Expectancy R: {results['aggregate_metrics']['expectancy_R']:.2f}")
        print(f"Net Profit: ${results['aggregate_metrics']['net_profit']:,.2f}")
        print(f"Max Drawdown: {results['aggregate_metrics']['max_drawdown']:.2%}")
        print(f"Sharpe: {results['aggregate_metrics']['sharpe']:.2f}")
        print(f"Sortino: {results['aggregate_metrics']['sortino']:.2f}")
        print(f"\nValidation: {'PASSED' if results['validation']['passed'] else 'FAILED'}")
        print(f"  - Lookahead Check: {results['validation']['lookahead_check']}")
        print(f"  - Timestamp Check: {results['validation']['timestamp_check']}")
        print(f"  - Data Integrity: {results['validation']['data_integrity']}")
        print(f"  - Signal Integrity: {results['validation']['signal_integrity']}")
        print(f"  - Execution Integrity: {results['validation']['execution_integrity']}")

        if save_results:
            print(f"\nResults saved to: results/ directory")

        return results

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Data file not found. Ensure parquet files exist in data/ directory.")
        print("Available data files:")
        data_dir = Path("data")
        if data_dir.exists():
            for file in data_dir.glob("*.parquet"):
                print(f"  - {file.name}")
        else:
            print("  data/ directory not found")
        return None

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Run a single ICT strategy backtest")
    parser.add_argument(
        "--strategy",
        type=str,
        required=True,
        help="Strategy ID (e.g., fvg_ce_entry, silver_bullet_ny_am)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date (e.g., 2024-01-01)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date (e.g., 2024-12-31)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to JSON file"
    )

    args = parser.parse_args()

    run_strategy(
        strategy_id=args.strategy,
        start_date=args.start_date,
        end_date=args.end_date,
        save_results=not args.no_save
    )


if __name__ == "__main__":
    main()
