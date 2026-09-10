"""
NY PM Reversal Strategy Implementation

Session-anchored reversal/continuation model during NY PM (13:30-16:00 NY).
Continuation or reversal of NY AM direction. PM range formation.

Strategy Specification from ICT Unified Trading Book:
- Time: 13:30-16:00 NY
- NY AM direction must be established
- PM range formation
- Stop: PM range extreme
- Can be continuation or reversal

Portfolio Constructor: Portfolio.from_signals() (simple SL + single TP)

Deviation Notes:
- Simplified NY AM/PM session detection for demonstration
- In production, would use more sophisticated session and range detection
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
    in_killzone, htf_bias, Direction, detect_displacement,
    convert_to_ny
)
from data_loader import load_data
from config import NYPMReversalConfig


def generate_signals(price_data: pd.DataFrame, cfg: NYPMReversalConfig) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for NY PM Reversal strategy.
    
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
    
    # NY PM mask (13:30-16:00)
    killzone_mask = in_killzone(price_data.index, "ny_pm")
    
    # Convert to NY time for session detection
    ny_index = convert_to_ny(price_data.index)
    time_only = ny_index.time
    
    # NY AM mask (08:00-11:00)
    ny_am_start = pd.to_datetime("08:00").time()
    ny_am_end = pd.to_datetime("11:00").time()
    ny_am_mask = (time_only >= ny_am_start) & (time_only <= ny_am_end)
    
    # NY PM mask (13:30-16:00)
    ny_pm_start = pd.to_datetime("13:30").time()
    ny_pm_end = pd.to_datetime("16:00").time()
    ny_pm_session_mask = (time_only >= ny_pm_start) & (time_only <= ny_pm_end)
    
    # Detect displacement
    displacement = detect_displacement(price_data, min_range_pct=1.5)
    
    # Calculate NY AM direction (simplified)
    ny_am_direction = pd.Series("NEUTRAL", index=price_data.index)
    for i in range(len(price_data)):
        if ny_am_mask.iloc[i]:
            if price_data['close'].iloc[i] > price_data['open'].iloc[i]:
                ny_am_direction.iloc[i] = "LONG"
            else:
                ny_am_direction.iloc[i] = "SHORT"
    
    # Forward-fill NY AM direction for PM session
    ny_am_direction = ny_am_direction.ffill()
    
    # Calculate PM range (simplified)
    pm_high = pd.Series(0.0, index=price_data.index)
    pm_low = pd.Series(999999.0, index=price_data.index)
    
    for i in range(len(price_data)):
        if ny_pm_session_mask.iloc[i]:
            pm_high.iloc[i] = max(pm_high.iloc[i], price_data['high'].iloc[i])
            pm_low.iloc[i] = min(pm_low.iloc[i], price_data['low'].iloc[i])
    
    # Forward-fill PM range
    pm_high = pm_high.ffill()
    pm_low = pm_low.ffill()
    
    # Create entry signals (simplified NY PM reversal/continuation detection)
    entries = pd.Series(False, index=price_data.index)
    
    for i in range(len(price_data)):
        # Check NY PM window
        if not killzone_mask.iloc[i]:
            continue
        
        # Check HTF bias
        if bias.iloc[i] == "NEUTRAL":
            continue
        
        # Check for displacement through PM range
        if not displacement.iloc[i]:
            continue
        
        # Simplified: Entry on displacement during NY PM
        # In production, would detect actual continuation or reversal of NY AM direction
        entries.iloc[i] = True
    
    # Calculate stops based on PM range extreme
    stops = pd.Series(0.0, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            # Stop at PM range extreme + buffer
            if bias.iloc[i] == "LONG":
                stop = pm_low.iloc[i] - cfg.stop_buffer
            else:
                stop = pm_high.iloc[i] + cfg.stop_buffer
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


def run_backtest(cfg: NYPMReversalConfig) -> vbt.Portfolio:
    """
    Run backtest for NY PM Reversal strategy.
    
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
    from config import NYPMReversalConfig
    
    cfg = NYPMReversalConfig()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("ny_pm_reversal", "1.0")
    
    print(f"NY PM Reversal Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"Killzone: {cfg.killzone_start}-{cfg.killzone_end} NY")
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
