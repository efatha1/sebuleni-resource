"""
Venom Model Strategy Implementation

Time-constrained range reversal model. Pre-cash-open range sweep → false breakout → reversal.
Designed for US indices (NQ, ES, YM) but adapted for XAUUSD.

Strategy Specification from ICT Unified Trading Book:
- Pre-cash-open range: High and low formed during 08:00-09:30 NY
- After 09:30 (US equities cash open), price sweeps one bound
- False breakout: Wick continues briefly past swept bound
- Reversal: Price reverses back through range with displacement
- Target: Opposite side of pre-open range, then HTF DOL
- Window: ~90 minutes from 09:30 → 11:00 NY

Portfolio Constructor: Portfolio.from_signals() (simple SL + single TP)

Deviation Notes:
- Adapted from indices to XAUUSD with different stop_buffer
- Simplified pre-open range and false breakout detection for demonstration
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
    detect_displacement, htf_bias, Direction, convert_to_ny
)
from data_loader import load_data
from config import VenomConfig


def generate_signals(price_data: pd.DataFrame, cfg: VenomConfig) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for Venom Model strategy.
    
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
    
    # Convert to NY time for session logic
    ny_index = convert_to_ny(price_data.index)
    time_only = ny_index.time
    
    # Pre-open range mask (08:00-09:30 NY)
    pre_open_start = pd.to_datetime(cfg.pre_open_start).time()
    pre_open_end = pd.to_datetime(cfg.pre_open_end).time()
    pre_open_mask = (time_only >= pre_open_start) & (time_only <= pre_open_end)
    
    # Trigger window mask (09:30-11:00 NY)
    trigger_start = pd.to_datetime(cfg.trigger_start).time()
    trigger_end = pd.to_datetime(cfg.trigger_end).time()
    trigger_mask = (time_only >= trigger_start) & (time_only <= trigger_end)
    
    # Detect displacement
    displacement = detect_displacement(price_data, min_range_pct=1.5)
    
    # Calculate pre-open range (simplified)
    pre_open_high = pd.Series(0.0, index=price_data.index)
    pre_open_low = pd.Series(999999.0, index=price_data.index)
    
    for i in range(len(price_data)):
        if pre_open_mask.iloc[i]:
            pre_open_high.iloc[i] = max(pre_open_high.iloc[i], price_data['high'].iloc[i])
            pre_open_low.iloc[i] = min(pre_open_low.iloc[i], price_data['low'].iloc[i])
    
    # Forward-fill pre-open range for trigger window
    pre_open_high = pre_open_high.ffill()
    pre_open_low = pre_open_low.ffill()
    
    # Create entry signals (simplified Venom pattern detection)
    entries = pd.Series(False, index=price_data.index)
    
    for i in range(len(price_data)):
        # Check trigger window
        if not trigger_mask.iloc[i]:
            continue
        
        # Check HTF bias
        if bias.iloc[i] == "NEUTRAL":
            continue
        
        # Check for sweep of pre-open range
        if bias.iloc[i] == "LONG":
            # Looking for sweep of pre-open low (false breakout)
            if price_data['low'].iloc[i] < pre_open_low.iloc[i]:
                # Check for displacement after sweep
                if i < len(price_data) - 1 and displacement.iloc[i+1]:
                    # Entry on reversal back through range
                    entries.iloc[i+1] = True
        else:  # SHORT
            # Looking for sweep of pre-open high (false breakout)
            if price_data['high'].iloc[i] > pre_open_high.iloc[i]:
                # Check for displacement after sweep
                if i < len(price_data) - 1 and displacement.iloc[i+1]:
                    # Entry on reversal back through range
                    entries.iloc[i+1] = True
    
    # Calculate stops based on false breakout extreme
    stops = pd.Series(0.0, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            # Estimate stop as false breakout extreme + buffer
            if bias.iloc[i] == "LONG":
                stop = pre_open_low.iloc[i] - cfg.stop_buffer
            else:
                stop = pre_open_high.iloc[i] + cfg.stop_buffer
            stops.iloc[i] = stop
    
    # Calculate exits (take profit - opposite range bound)
    exits = pd.Series(False, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            # Target is opposite side of pre-open range
            if bias.iloc[i] == "LONG":
                target = pre_open_high.iloc[i]
            else:
                target = pre_open_low.iloc[i]
            
            # Exit when target reached
            for j in range(i+1, len(price_data)):
                if price_data['high'].iloc[j] >= target >= price_data['low'].iloc[j]:
                    exits.iloc[j] = True
                    break
    
    return entries, exits


def run_backtest(cfg: VenomConfig) -> vbt.Portfolio:
    """
    Run backtest for Venom Model strategy.
    
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
    from config import VenomConfig
    
    cfg = VenomConfig()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("venom", "1.0")
    
    print(f"Venom Model Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"Pre-Open Range: {cfg.pre_open_start}-{cfg.pre_open_end} NY")
    print(f"Trigger Window: {cfg.trigger_start}-{cfg.trigger_end} NY")
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
        print(">>> from data_loader import create_sample_data")
        print(">>> df = create_sample_data('XAUUSD', '5m')")
        print(">>> df.to_parquet('data/XAUUSD_5m.parquet')")
