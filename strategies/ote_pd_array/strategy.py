"""
OTE + PD Array Entry Strategy Implementation

Canonical OTE methodology with PD array confluence. Continuation setup (no counter-sweep required).

Strategy Specification from ICT Unified Trading Book:
- Time: Any time (no time constraint)
- HTF bias: Must agree with entry direction
- Structure: Measured swing leg with structural break
- Era-Fork: Stop placement (2017 = leg origin; 2020 = fixed pips)

Portfolio Constructor: Portfolio.from_signals() (simple SL + single TP)

Deviation Notes:
- Simplified swing leg detection for demonstration
- In production, would use more sophisticated swing detection from ict_signals
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

from ict_signals import (
    calculate_fib_levels, calculate_ote_zone, htf_bias, Direction
)
from data_loader import load_data
from config import OTEPDArrayConfig


def generate_signals(price_data: pd.DataFrame, cfg: OTEPDArrayConfig) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for OTE + PD Array Entry strategy.
    
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
    
    # Simplified swing leg detection (for demonstration)
    # In production, would use sophisticated swing detection
    swing_highs = price_data['high'].rolling(20).max()
    swing_lows = price_data['low'].rolling(20).min()
    
    # Create entry signals (simplified OTE detection)
    entries = pd.Series(False, index=price_data.index)
    
    for i in range(len(price_data)):
        # Check HTF bias
        if bias.iloc[i] == "NEUTRAL":
            continue
        
        # Determine swing leg direction based on bias
        if bias.iloc[i] == "LONG":
            leg_start = swing_lows.iloc[i]
            leg_end = swing_highs.iloc[i]
            direction = Direction.LONG
        else:  # SHORT
            leg_start = swing_highs.iloc[i]
            leg_end = swing_lows.iloc[i]
            direction = Direction.SHORT
        
        # Calculate OTE zone
        ote_low, ote_high = calculate_ote_zone(leg_start, leg_end, direction)
        
        # Check if price is in OTE zone
        if direction == Direction.LONG:
            in_ote = (price_data['close'].iloc[i] >= ote_low) & \
                    (price_data['close'].iloc[i] <= ote_high)
        else:  # SHORT
            in_ote = (price_data['close'].iloc[i] >= ote_low) & \
                    (price_data['close'].iloc[i] <= ote_high)
        
        entries.iloc[i] = in_ote
    
    # Calculate stops based on era parameter
    stops = pd.Series(0.0, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            entry_price = price_data['close'].iloc[i]
            
            if cfg.stop_method == "fixed_pips":
                # 2020 era: fixed pip stop
                stop = entry_price - cfg.stop_buffer if bias.iloc[i] == "LONG" else entry_price + cfg.stop_buffer
            else:  # leg_origin
                # 2017 era: stop at leg origin
                if bias.iloc[i] == "LONG":
                    stop = swing_lows.iloc[i]
                else:
                    stop = swing_highs.iloc[i]
            
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


def run_backtest(cfg: OTEPDArrayConfig) -> vbt.Portfolio:
    """
    Run backtest for OTE + PD Array Entry strategy.
    
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
    from config import OTEPDArrayConfig
    
    cfg = OTEPDArrayConfig()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("ote_pd_array", "1.0")
    
    print(f"OTE + PD Array Entry Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"OTE Zone: {cfg.ote_zone_low}-{cfg.ote_zone_high}")
    print(f"Era: {cfg.era}")
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
