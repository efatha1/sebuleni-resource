"""
Order Block Entry Strategy Implementation

Enter on Order Block retest. No time constraint, simple stop/target structure.

Strategy Specification from ICT Unified Trading Book:
- Time: Any time (no time constraint)
- HTF bias: Must agree with OB direction
- Stop: OB far edge + buffer

Portfolio Constructor: Portfolio.from_signals() (simple SL + single TP)

Deviation Notes:
- Simplified OB detection for demonstration
- In production, would use more sophisticated OB detection from ict_signals
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from dataclasses import dataclass
from typing import Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ict_signals import order_blocks, htf_bias, Direction
from data_loader import load_data
from config import OrderBlockConfig


def generate_signals(price_data: pd.DataFrame, cfg: OrderBlockConfig) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for Order Block Entry strategy.
    
    Args:
        price_data: DataFrame with OHLC data
        cfg: Strategy configuration
    
    Returns:
        Tuple of (entries, exits) Series
    """
    # Load HTF data for bias calculation
    htf_data = load_data(cfg.symbol, cfg.htf_timeframe)
    
    # Calculate HTF bias
    bias = htf_bias(htf_data, price_data.index)
    
    # Detect Order Blocks (simplified for demonstration)
    # In production, would use more sophisticated detection
    obs = order_blocks(price_data, Direction.LONG)  # Simplified - detect both directions in production
    
    # Create entry signals (simplified OB retest logic)
    entries = pd.Series(False, index=price_data.index)
    
    for _, ob in obs.iterrows():
        ob_time = ob['timestamp']
        ob_direction = ob['direction']
        
        # Check OB direction alignment with HTF bias
        if bias.loc[ob_time] == ob_direction.upper():
            # Entry on retest to OB zone (simplified)
            entry_zone = (price_data.index > ob_time) & \
                       (price_data['close'] >= ob['low'] - cfg.stop_buffer) & \
                       (price_data['close'] <= ob['high'] + cfg.stop_buffer)
            entries = entries | entry_zone
    
    # Calculate stops based on OB far edge
    stops = pd.Series(0.0, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            # Find most recent OB before entry
            recent_obs = obs[obs['timestamp'] <= price_data.index[i]]
            if len(recent_obs) > 0:
                latest_ob = recent_obs.iloc[-1]
                stop = latest_ob['high'] if latest_ob['direction'] == 'short' else latest_ob['low']
                stops.iloc[i] = stop
    
    # Calculate exits (take profit)
    exits = pd.Series(False, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            entry_price = price_data['close'].iloc[i]
            stop_price = stops.iloc[i]
            
            # Calculate target price
            risk = abs(entry_price - stop_price)
            target = entry_price + (risk * cfg.tp_r) if entry_price > stop_price else entry_price - (risk * cfg.tp_r)
            
            # Exit when target reached
            for j in range(i+1, len(price_data)):
                if price_data['high'].iloc[j] >= target >= price_data['low'].iloc[j]:
                    exits.iloc[j] = True
                    break
    
    return entries, exits


def run_backtest(cfg: OrderBlockConfig) -> vbt.Portfolio:
    """
    Run backtest for Order Block Entry strategy.
    
    Args:
        cfg: Strategy configuration
    
    Returns:
        vectorbt Portfolio object
    """
    # Load data
    price_data = load_data(cfg.symbol, cfg.ltf_timeframe)
    
    # Generate signals
    entries, exits = generate_signals(price_data, cfg)
    
    # Calculate stop distances as percentage of entry price
    stop_distances = pd.Series(0.0, index=price_data.index)
    for i, entry in enumerate(entries):
        if entry:
            entry_price = price_data['close'].iloc[i]
            # Estimate stop distance as 1% of entry price (simplified)
            stop_distances.iloc[i] = 0.01
    
    # Calculate take profit distances as percentage of entry price
    tp_distances = stop_distances * cfg.tp_r
    
    # Create portfolio using from_signals
    portfolio = vbt.Portfolio.from_signals(
        price_data['close'],
        entries,
        exits,
        init_cash=cfg.init_cash,
        fees=cfg.fees,
        sl_stop=stop_distances,
        tp_stop=tp_distances,
        freq='5T'
    )
    
    return portfolio


if __name__ == "__main__":
    import sys
    import os
    import json
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from backtest_agent import BacktestAgent
    from config import OrderBlockConfig
    
    cfg = OrderBlockConfig()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("order_block_entry", "1.0")
    
    print(f"Order Block Entry Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"Risk: {cfg.risk_pct * 100}%")
    print("=" * 60)
    
    try:
        results = agent.run_backtest(
            sys.modules[__name__],  # Current module
            cfg,
            start_date=cfg.start_date,
            end_date=cfg.end_date,
            save_results=True
        )
        
        print(f"\nBacktest Results:")
        print(f"Total Trades: {results['aggregate_metrics']['total_trades']}")
        print(f"Win Rate: {results['aggregate_metrics']['win_rate']}")
        print(f"Profit Factor: {results['aggregate_metrics']['profit_factor']}")
        print(f"Expectancy R: {results['aggregate_metrics']['expectancy_R']}")
        print(f"Net Profit: {results['aggregate_metrics']['net_profit']}")
        print(f"Max Drawdown: {results['aggregate_metrics']['max_drawdown']}")
        print(f"Sharpe: {results['aggregate_metrics']['sharpe']}")
        print(f"Sortino: {results['aggregate_metrics']['sortino']}")
        print(f"\nValidation: {results['validation']['passed']}")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Data file not found. Use sample data for testing:")
        print(">>> from data_loader import create_sample_data")
        print(">>> df = create_sample_data('XAUUSD', '5m')")
        print(">>> df.to_parquet('data/xauusd_5min.parquet')")
