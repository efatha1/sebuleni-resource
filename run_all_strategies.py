"""
Run All Strategies Backtest

Comprehensive script to run backtests for all 15 ICT strategies.
Generates a summary table and saves individual results.
Usage: python run_all_strategies.py --start-date 2024-01-01 --end-date 2024-03-31
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backtest_agent import BacktestAgent


# Strategy configurations
STRATEGIES = [
    ("fvg_ce_entry", "strategies.fvg_ce_entry.config", "FVGCEConfig"),
    ("order_block_entry", "strategies.order_block_entry.config", "OrderBlockConfig"),
    ("ict_2022_model", "strategies.ict_2022_model.config", "ICT2022Config"),
    ("ote_pd_array", "strategies.ote_pd_array.config", "OTEPDArrayConfig"),
    ("judas_swing", "strategies.judas_swing.config", "JudasSwingConfig"),
    ("asian_range_sweep", "strategies.asian_range_sweep.config", "AsianRangeSweepConfig"),
    ("bread_and_butter", "strategies.bread_and_butter.config", "BreadAndButterConfig"),
    ("ict_2023_model", "strategies.ict_2023_model.config", "ICT2023Config"),
    ("ict_2024_model", "strategies.ict_2024_model.config", "ICT2024Config"),
    ("silver_bullet_ny_am", "strategies.silver_bullet_ny_am.config", "SilverBulletNYAMConfig"),
    ("silver_bullet_london", "strategies.silver_bullet_london.config", "SilverBulletLondonConfig"),
    ("unicorn", "strategies.unicorn.config", "UnicornConfig"),
    ("venom", "strategies.venom.config", "VenomConfig"),
    ("london_close_reversal", "strategies.london_close_reversal.config", "LondonCloseReversalConfig"),
    ("ny_pm_reversal", "strategies.ny_pm_reversal.config", "NYPMReversalConfig"),
]


def run_single_strategy(
    strategy_id: str,
    config_module: str,
    config_class: str,
    start_date: str = None,
    end_date: str = None,
    save_results: bool = True
) -> Dict[str, Any]:
    """
    Run a single strategy backtest.

    Returns:
        Summary dictionary with key metrics
    """
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

        # Run backtest
        results = agent.run_backtest(
            strategy_module=sys.modules[__name__],
            config=cfg,
            start_date=cfg.start_date,
            end_date=cfg.end_date,
            save_results=save_results
        )

        # Extract summary
        summary = {
            "strategy_id": strategy_id,
            "total_trades": results['aggregate_metrics']['total_trades'],
            "win_rate": results['aggregate_metrics']['win_rate'],
            "profit_factor": results['aggregate_metrics']['profit_factor'],
            "expectancy_R": results['aggregate_metrics']['expectancy_R'],
            "net_profit": results['aggregate_metrics']['net_profit'],
            "max_drawdown": results['aggregate_metrics']['max_drawdown'],
            "sharpe": results['aggregate_metrics']['sharpe'],
            "sortino": results['aggregate_metrics']['sortino'],
            "validation_passed": results['validation']['passed'],
            "lookahead_check": results['validation']['lookahead_check'],
            "timestamp_check": results['validation']['timestamp_check'],
            "data_integrity": results['validation']['data_integrity'],
            "signal_integrity": results['validation']['signal_integrity'],
            "execution_integrity": results['validation']['execution_integrity'],
        }

        return summary, results

    except Exception as e:
        return {
            "strategy_id": strategy_id,
            "error": str(e),
            "total_trades": 0,
            "win_rate": None,
            "profit_factor": None,
            "expectancy_R": None,
            "net_profit": None,
            "max_drawdown": None,
            "sharpe": None,
            "sortino": None,
            "validation_passed": False,
            "lookahead_check": "ERROR",
            "timestamp_check": "ERROR",
            "data_integrity": "ERROR",
            "signal_integrity": "ERROR",
            "execution_integrity": "ERROR",
        }, None


def print_summary_table(all_results: List[Dict[str, Any]]):
    """Print a formatted summary table of all results."""
    print(f"\n{'='*100}")
    print(f"{'STRATEGY BACKTEST SUMMARY':^100}")
    print(f"{'='*100}")
    print(f"{'Strategy':<25} {'Trades':<8} {'Win Rate':<10} {'Profit Factor':<13} {'Expectancy R':<12} {'Net Profit':<12} {'Max DD':<10} {'Sharpe':<8} {'Valid':<6}")
    print(f"{'-'*100}")

    for result in all_results:
        if 'error' in result:
            print(f"{result['strategy_id']:<25} {'ERROR':<8} {'':<10} {'':<13} {'':<12} {'':<12} {'':<10} {'':<8} {'NO':<6}")
        else:
            win_rate = f"{result['win_rate']:.2%}" if result['win_rate'] is not None else "N/A"
            profit_factor = f"{result['profit_factor']:.2f}" if result['profit_factor'] is not None else "N/A"
            expectancy = f"{result['expectancy_R']:.2f}" if result['expectancy_R'] is not None else "N/A"
            net_profit = f"${result['net_profit']:,.0f}" if result['net_profit'] is not None else "N/A"
            max_dd = f"{result['max_drawdown']:.2%}" if result['max_drawdown'] is not None else "N/A"
            sharpe = f"{result['sharpe']:.2f}" if result['sharpe'] is not None else "N/A"
            valid = "YES" if result['validation_passed'] else "NO"

            print(f"{result['strategy_id']:<25} {result['total_trades']:<8} {win_rate:<10} {profit_factor:<13} {expectancy:<12} {net_profit:<12} {max_dd:<10} {sharpe:<8} {valid:<6}")

    print(f"{'='*100}")


def print_validation_summary(all_results: List[Dict[str, Any]]):
    """Print validation check summary."""
    print(f"\n{'='*80}")
    print(f"{'VALIDATION SUMMARY':^80}")
    print(f"{'='*80}")
    print(f"{'Strategy':<25} {'Lookahead':<12} {'Timestamp':<12} {'Data':<12} {'Signal':<12} {'Exec':<12}")
    print(f"{'-'*80}")

    for result in all_results:
        if 'error' in result:
            print(f"{result['strategy_id']:<25} {'ERROR':<12} {'ERROR':<12} {'ERROR':<12} {'ERROR':<12} {'ERROR':<12}")
        else:
            print(f"{result['strategy_id']:<25} {result['lookahead_check']:<12} {result['timestamp_check']:<12} {result['data_integrity']:<12} {result['signal_integrity']:<12} {result['execution_integrity']:<12}")

    print(f"{'='*80}")


def run_all_strategies(
    start_date: str = None,
    end_date: str = None,
    save_results: bool = True,
    skip_on_error: bool = False
):
    """
    Run backtests for all 15 strategies.

    Args:
        start_date: Optional start date (e.g., "2024-01-01")
        end_date: Optional end date (e.g., "2024-12-31")
        save_results: Whether to save individual results to JSON files
        skip_on_error: If True, continue on error; if False, stop on first error
    """
    print(f"{'='*60}")
    print(f"Running All 15 ICT Strategy Backtests")
    print(f"{'='*60}")
    print(f"Start Date: {start_date or 'All available data'}")
    print(f"End Date: {end_date or 'All available data'}")
    print(f"Save Results: {save_results}")
    print(f"Skip on Error: {skip_on_error}")
    print(f"{'='*60}")

    all_results = []
    errors = []

    for i, (strategy_id, config_module, config_class) in enumerate(STRATEGIES, 1):
        print(f"\n[{i}/{len(STRATEGIES)}] Testing: {strategy_id}")
        print(f"{'-'*60}")

        summary, full_results = run_single_strategy(
            strategy_id=strategy_id,
            config_module=config_module,
            config_class=config_class,
            start_date=start_date,
            end_date=end_date,
            save_results=save_results
        )

        all_results.append(summary)

        if 'error' in summary:
            errors.append((strategy_id, summary['error']))
            print(f"✗ Error: {summary['error']}")
            if not skip_on_error:
                print("\nStopping due to error. Use --skip-on-error to continue.")
                break
        else:
            print(f"✓ Total Trades: {summary['total_trades']}")
            print(f"✓ Win Rate: {summary['win_rate']:.2%}")
            print(f"✓ Profit Factor: {summary['profit_factor']:.2f}")
            print(f"✓ Validation: {'PASSED' if summary['validation_passed'] else 'FAILED'}")

    # Print summary tables
    print_summary_table(all_results)
    print_validation_summary(all_results)

    # Print error summary
    if errors:
        print(f"\n{'='*80}")
        print(f"ERRORS ENCOUNTERED ({len(errors)} strategies)")
        print(f"{'='*80}")
        for strategy_id, error in errors:
            print(f"✗ {strategy_id}: {error}")

    # Calculate overall statistics
    successful = [r for r in all_results if 'error' not in r]
    if successful:
        total_trades_all = sum(r['total_trades'] for r in successful)
        avg_win_rate = sum(r['win_rate'] for r in successful if r['win_rate'] is not None) / len(successful)
        avg_profit_factor = sum(r['profit_factor'] for r in successful if r['profit_factor'] is not None) / len(successful)
        total_net_profit = sum(r['net_profit'] for r in successful if r['net_profit'] is not None)

        print(f"\n{'='*80}")
        print(f"OVERALL STATISTICS ({len(successful)} successful strategies)")
        print(f"{'='*80}")
        print(f"Total Trades (all strategies): {total_trades_all}")
        print(f"Average Win Rate: {avg_win_rate:.2%}")
        print(f"Average Profit Factor: {avg_profit_factor:.2f}")
        print(f"Total Net Profit (all strategies): ${total_net_profit:,.2f}")
        print(f"{'='*80}")

    # Save summary to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = f"results/backtest_summary_{timestamp}.json"
    Path("results").mkdir(exist_ok=True)

    with open(summary_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "start_date": start_date,
            "end_date": end_date,
            "strategies_tested": len(all_results),
            "strategies_successful": len(successful),
            "strategies_failed": len(errors),
            "results": all_results
        }, f, indent=2, default=str)

    print(f"\n✓ Summary saved to: {summary_file}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Run backtests for all 15 ICT strategies")
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
        help="Don't save individual results to JSON files"
    )
    parser.add_argument(
        "--skip-on-error",
        action="store_true",
        help="Continue running strategies even if one fails"
    )

    args = parser.parse_args()

    run_all_strategies(
        start_date=args.start_date,
        end_date=args.end_date,
        save_results=not args.no_save,
        skip_on_error=args.skip_on_error
    )


if __name__ == "__main__":
    main()
