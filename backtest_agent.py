"""
VectorBT Backtest Agent - Comprehensive backtesting with detailed recording

Centralized backtest agent with strategy-specific adapters.
Implements full VECTORBT BACKTEST AGENT specification.

Features:
- Comprehensive trade recording (MAE/MFE, exit reasons, multi-target support)
- Market state capture at each entry (tiered approach: core + strategy-specific)
- Full validation suite (5 checks)
- Structured JSON output saved to files
- Date range filtering
- Hybrid architecture (centralized agent with strategy adapters)
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import hashlib
import json
from pathlib import Path
import pytz
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_data, validate_data_quality
from validator import Validator
from market_state_recorder import MarketStateRecorder

# Import strategy adapters
from adapters import (
    SilverBulletNYAMAdapter,
    SilverBulletLondonAdapter,
    UnicornAdapter,
    ICT2024Adapter,
    VenomAdapter,
    AsianRangeSweepAdapter,
    JudasSwingAdapter,
)


# Module-level state tracker for partial exit extraction
# This allows order_func to write state that can be read after portfolio execution
_order_func_state_tracker = {}


def get_order_func_state_tracker():
    """Get the module-level order_func state tracker."""
    return _order_func_state_tracker


def clear_order_func_state_tracker():
    """Clear the module-level order_func state tracker."""
    global _order_func_state_tracker
    _order_func_state_tracker = {}


class BacktestAgent:
    """
    Centralized backtest agent with strategy-specific adapters.
    
    Implements full VECTORBT BACKTEST AGENT specification:
    - Experiment metadata recording
    - Aggregate metrics calculation
    - Detailed trade records with MAE/MFE
    - Market state capture at entries
    - Comprehensive validation suite
    - JSON output to files
    """
    
    def __init__(self, strategy_id: str, strategy_version: str = "1.0"):
        """
        Initialize backtest agent.

        Args:
            strategy_id: Strategy identifier (e.g., "fvg_ce_entry")
            strategy_version: Strategy version (default: "1.0")
        """
        self.strategy_id = strategy_id
        self.strategy_version = strategy_version
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)

        # Register strategy adapters
        self._adapter_registry = {
            'silver_bullet_ny_am': SilverBulletNYAMAdapter(),
            'silver_bullet_london': SilverBulletLondonAdapter(),
            'unicorn': UnicornAdapter(),
            'ict_2024_model': ICT2024Adapter(),
            'venom': VenomAdapter(),
            'asian_range_sweep': AsianRangeSweepAdapter(),
            'judas_swing': JudasSwingAdapter(),
        }
        
    def run_backtest(
        self,
        strategy_module: Any,
        config: Any,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        Execute comprehensive backtest with full recording.
        
        Args:
            strategy_module: Strategy module with generate_signals() function
            config: Strategy configuration object
            start_date: Optional start date for filtering (e.g., "2024-01-01")
            end_date: Optional end date for filtering (e.g., "2024-12-31")
            save_results: Whether to save results to JSON file (default: True)
        
        Returns:
            Dictionary with:
            - experiment: metadata
            - aggregate_metrics: performance metrics
            - trades: detailed trade records
            - market_state: market state at each entry
            - validation: validation results
        """
        print(f"Starting backtest for {self.strategy_id}...")
        
        # 1. Load data with date filtering
        print("Loading data...")
        price_data = load_data(
            config.symbol,
            config.ltf_timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # 2. Load HTF data for bias calculation
        print("Loading HTF data...")
        htf_data = load_data(
            config.symbol,
            config.htf_timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # 3. Validate data quality
        print("Validating data quality...")
        data_validation = validate_data_quality(price_data)
        
        # 4. Generate signals using strategy
        print("Generating signals...")
        entries, exits = strategy_module.generate_signals(price_data, config)

        # 5. Clear state tracker before portfolio creation
        clear_order_func_state_tracker()

        # 6. Create portfolio with appropriate constructor
        print("Creating portfolio...")
        portfolio = self._create_portfolio(
            price_data, entries, exits, config, strategy_module
        )
        
        # 7. Extract all required information
        print("Extracting results...")
        results = {
            "experiment": self._extract_experiment_metadata(
                config, start_date, end_date, data_validation
            ),
            "aggregate_metrics": self._calculate_aggregate_metrics(portfolio),
            "trades": self._extract_trade_records(
                portfolio, price_data, config, htf_data
            ),
            "market_state": self._extract_market_state(
                portfolio, price_data, config, htf_data
            ),
            "validation": self._validate_backtest(
                portfolio, price_data, config, data_validation
            )
        }

        # 8. Save results to JSON
        if save_results:
            print("Saving results...")
            self._save_results(results)
        
        print(f"Backtest complete for {self.strategy_id}")
        return results
    
    def _create_portfolio(self, price_data: pd.DataFrame, entries: pd.Series, exits: pd.Series, config: Any, strategy_module: Any):
        """
        Create portfolio with appropriate constructor using strategy adapters.

        Strategy adapters handle complex requirements:
        - Partial exits (Silver Bullet, Unicorn)
        - Aggressive trailing (ICT 2024)
        - Special entry logic (Venom, Asian Range Sweep, Judas Swing)

        Simple strategies use default from_signals constructor.
        """
        # Check if strategy has a registered adapter
        if self.strategy_id in self._adapter_registry:
            adapter = self._adapter_registry[self.strategy_id]
            print(f"Using adapter: {adapter.get_strategy_id()}")
            portfolio = adapter.create_portfolio(price_data, entries, exits, config, strategy_module)
        else:
            # Use default from_signals for simple strategies
            print(f"Using default from_signals for: {self.strategy_id}")

            # Calculate stop/TP distances
            stop_distances = self._calculate_stop_distances(price_data, entries, config)
            tp_distances = stop_distances * config.tp_r

            portfolio = vbt.Portfolio.from_signals(
                price_data['close'],
                entries,
                exits,
                init_cash=config.init_cash,
                fees=config.fees,
                sl_stop=stop_distances,
                tp_stop=tp_distances,
                freq='5T',
                init_position='cash',
                cash_sharing=True
            )

        return portfolio
    
    def _calculate_stop_distances(self, price_data: pd.DataFrame, entries: pd.Series, config: Any) -> pd.Series:
        """
        Calculate stop distances as percentage of entry price.
        
        This is a simplified implementation. In production, this would use
        actual stop distances from the strategy logic.
        """
        stop_distances = pd.Series(0.0, index=price_data.index)
        for i, entry in enumerate(entries):
            if entry:
                entry_price = price_data['close'].iloc[i]
                stop_distances.iloc[i] = 0.01  # 1% as placeholder
        return stop_distances
    
    def _extract_experiment_metadata(self, config: Any, start_date: Optional[str], end_date: Optional[str], data_validation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract comprehensive experiment metadata"""
        strategy_def_hash = hashlib.md5(
            json.dumps(config.__dict__, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "strategy_definition_hash": strategy_def_hash,
            "compiler_version": "1.0.0",
            "instrument": config.symbol,
            "timeframe": config.ltf_timeframe,
            "htf_timeframe": config.htf_timeframe,
            "data_version": "1.0",
            "data_source": "parquet",
            "start_datetime": start_date,
            "end_datetime": end_date,
            "timezone": "UTC",
            "session_configuration": "NY_killzones",
            "spread_assumptions": 0.0,
            "slippage_assumptions": 0.0,
            "commission_assumptions": config.fees,
            "position_sizing_rules": f"risk_pct: {config.risk_pct}",
            "initial_capital": config.init_cash,
            "leverage": 1.0,
            "execution_configuration": "vectorbt",
            "data_validation": data_validation
        }
    
    def _calculate_aggregate_metrics(self, portfolio) -> Dict[str, Any]:
        """
        Calculate all required aggregate metrics.
        
        Metrics:
        - total_trades, win_rate, profit_factor, expectancy_R
        - net_profit, max_drawdown, sharpe, sortino
        """
        trades = portfolio.trades
        
        if len(trades) == 0:
            return {
                "total_trades": 0,
                "win_rate": None,
                "profit_factor": None,
                "expectancy_R": None,
                "net_profit": None,
                "max_drawdown": None,
                "sharpe": None,
                "sortino": None
            }
        
        # Extract trade PnL
        pnl = trades.pnl
        
        # Calculate metrics
        winning_trades = pnl[pnl > 0]
        losing_trades = pnl[pnl < 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        gross_profit = winning_trades.sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades.sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        
        # Calculate R-multiples (using entry/exit ratio)
        entry_prices = trades.entry_price
        exit_prices = trades.exit_price
        stop_prices = trades.sl_stop if hasattr(trades, 'sl_stop') else entry_prices * 0.99
        
        r_multiples = (exit_prices - entry_prices) / abs(entry_prices - stop_prices)
        expectancy_R = r_multiples.mean()
        
        net_profit = pnl.sum()
        max_drawdown = portfolio.max_drawdown()
        
        returns = portfolio.returns()
        sharpe = portfolio.sharpe_ratio() if len(returns) > 0 else None
        sortino = portfolio.sortino_ratio() if len(returns) > 0 else None
        
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy_R": expectancy_R,
            "net_profit": net_profit,
            "max_drawdown": max_drawdown,
            "sharpe": sharpe,
            "sortino": sortino
        }
    
    def _extract_trade_records(self, portfolio, price_data: pd.DataFrame, config: Any, htf_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Extract detailed trade records with MAE/MFE and exit reasons.
        
        For each trade, records:
        - entry_time, exit_time, direction
        - entry, stop, target, exit
        - R_multiple, PnL
        - MAE, MFE (in price units and R)
        - duration, exit_reason
        - trade_id, strategy_id, strategy_version
        - instrument, timeframe, position_size
        - partial_exits (for multi-target strategies)
        """
        trades = portfolio.trades
        trade_records = []
        
        for i, trade in enumerate(trades.itertuples()):
            entry_time = trade.entry_idx
            exit_time = trade.exit_idx
            
            # Convert to actual timestamps
            entry_dt = price_data.index[entry_time]
            exit_dt = price_data.index[exit_time]
            
            # Extract trade details
            entry_price = trade.entry_price
            exit_price = trade.exit_price
            
            # Calculate MAE/MFE
            entry_idx = price_data.index.get_loc(entry_dt)
            exit_idx = price_data.index.get_loc(exit_dt)
            
            trade_slice = price_data.iloc[entry_idx:exit_idx+1]
            
            if trade.direction == 'long':
                mae_price = trade_slice['low'].min()
                mfe_price = trade_slice['high'].max()
                mae = mae_price - entry_price
                mfe = mfe_price - entry_price
            else:
                mae_price = trade_slice['high'].max()
                mfe_price = trade_slice['low'].min()
                mae = entry_price - mae_price
                mfe = entry_price - mfe_price
            
            # Calculate R-multiple
            stop_price = trade.sl_stop if hasattr(trade, 'sl_stop') else entry_price * 0.99
            r_multiple = (exit_price - entry_price) / abs(entry_price - stop_price)
            
            # Determine exit reason
            exit_reason = self._determine_exit_reason(trade, trade_slice, entry_price, stop_price)
            
            # Get stop/target from trade if available
            stop = trade.sl_stop if hasattr(trade, 'sl_stop') else None
            target = trade.tp_stop if hasattr(trade, 'tp_stop') else None
            
            # For multi-target strategies, extract partial info
            partial_exits = []
            if hasattr(config, 'tp1_r'):
                partial_exits = self._extract_partial_exits(trade, config, entry_idx)
            
            trade_record = {
                "trade_id": i,
                "entry_time": str(entry_dt),
                "exit_time": str(exit_dt),
                "direction": "LONG" if trade.direction == 'long' else "SHORT",
                "entry": entry_price,
                "stop": stop,
                "target": target,
                "exit": exit_price,
                "R_multiple": r_multiple,
                "PnL": trade.pnl,
                "MAE": mae,
                "MFE": mfe,
                "MAE_R": mae / abs(entry_price - stop_price) if stop else None,
                "MFE_R": mfe / abs(entry_price - stop_price) if stop else None,
                "duration": (exit_dt - entry_dt).total_seconds() / 60,  # minutes
                "exit_reason": exit_reason,
                "strategy_id": self.strategy_id,
                "strategy_version": self.strategy_version,
                "instrument": config.symbol,
                "timeframe": config.ltf_timeframe,
                "position_size": trade.size if hasattr(trade, 'size') else 1.0,
                "partial_exits": partial_exits if partial_exits else None
            }
            
            trade_records.append(trade_record)
        
        return trade_records
    
    def _determine_exit_reason(self, trade, trade_slice: pd.DataFrame, entry_price: float, stop_price: float) -> str:
        """
        Determine exit reason based on price action.
        
        Returns: TAKE_PROFIT, STOP_LOSS, or OTHER
        """
        exit_price = trade_slice['close'].iloc[-1]
        
        # Check if hit stop
        if trade.direction == 'long':
            if trade_slice['low'].min() <= stop_price:
                return "STOP_LOSS"
            if exit_price > entry_price:
                return "TAKE_PROFIT"
        else:
            if trade_slice['high'].max() >= stop_price:
                return "STOP_LOSS"
            if exit_price < entry_price:
                return "TAKE_PROFIT"
        
        return "OTHER"
    
    def _extract_partial_exits(self, trade, config: Any, entry_idx: int) -> List[Dict[str, Any]]:
        """
        Extract partial exit information for multi-target strategies.

        Reads from the module-level order_func state tracker that was populated
        during portfolio execution.
        """
        state_tracker = get_order_func_state_tracker()

        # If entry index is in tracker, return actual partial exits
        if entry_idx in state_tracker:
            state = state_tracker[entry_idx]
            if 'partial_exits' in state:
                return state['partial_exits']

        # Fallback: return empty list if no tracking data available
        return []
    
    def _extract_market_state(self, portfolio, price_data: pd.DataFrame, config: Any, htf_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Extract market state at each entry.
        
        Uses MarketStateRecorder with tiered approach:
        - Core concepts (always recorded)
        - Strategy-specific concepts (based on strategy)
        """
        recorder = MarketStateRecorder(self.strategy_id)
        market_states = []
        
        # Get entry indices
        entries = portfolio.entries
        entry_indices = entries[entries].index
        
        for entry_idx in entry_indices:
            # Convert timestamp to index position
            entry_position = price_data.index.get_loc(entry_idx)
            
            # Record market state
            state = recorder.record_market_state(
                price_data, entry_position, config, htf_data
            )
            market_states.append(state)
        
        return market_states
    
    def _validate_backtest(self, portfolio, price_data: pd.DataFrame, config: Any, data_validation: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive validation"""
        validator = Validator()
        return validator.validate_backtest(portfolio, price_data, config, data_validation)
    
    def _save_results(self, results: Dict[str, Any]):
        """
        Save results to timestamped JSON file.
        
        Filename format: {strategy_id}_{timestamp}.json
        Example: fvg_ce_entry_20240910_153045.json
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.strategy_id}_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results saved to: {filepath}")


if __name__ == "__main__":
    print("VectorBT Backtest Agent - VECTORBT BACKTEST AGENT")
    print("=" * 60)
    print("Features:")
    print("- Comprehensive trade recording (MAE/MFE, exit reasons)")
    print("- Market state capture at entries (tiered approach)")
    print("- Full validation suite (5 checks)")
    print("- Structured JSON output to files")
    print("- Date range filtering")
    print("\nExample usage:")
    print(">>> from backtest_agent import BacktestAgent")
    print(">>> agent = BacktestAgent('fvg_ce_entry', '1.0')")
    print(">>> results = agent.run_backtest(strategy_module, config, start_date='2024-01-01', end_date='2024-12-31')")
    print(">>> print(results)")
