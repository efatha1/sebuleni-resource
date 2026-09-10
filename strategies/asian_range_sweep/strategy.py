"""
Asian Range Sweep Strategy Implementation

Trade the sweep of Asian range liquidity during London Open. Identify Asian range during Asia session, then trade the London sweep and reversal.

Strategy Specification from ICT Unified Trading Book:
- Time: London Open (02:00-05:00 NY)
- Session: Asia range established 18:00-03:00 NY
- Liquidity: Asian range high (BSL) and low (SSL)
- HTF bias: Determines which side will be true direction

Portfolio Constructor: Portfolio.from_signals() (simple SL + single TP)

Deviation Notes:
- Simplified Asian range detection for demonstration
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
    fair_value_gaps, fvg_ce_entry, convert_to_ny
)
from data_loader import load_data
from config import AsianRangeSweepConfig


def generate_signals(price_data: pd.DataFrame, cfg: AsianRangeSweepConfig) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for Asian Range Sweep strategy.
    
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
    
    # Asia session mask
    asia_start = pd.to_datetime(cfg.asia_start).time()
    asia_end = pd.to_datetime(cfg.asia_end).time()
    asia_mask = (time_only >= asia_start) | (time_only <= asia_end)
    
    # London open mask
    london_start = pd.to_datetime(cfg.london_start).time()
    london_end = pd.to_datetime(cfg.london_end).time()
    london_mask = (time_only >= london_start) & (time_only <= london_end)
    
    # Detect FVGs
    fvgs = fair_value_gaps(price_data, min_gap_pips=0.50)
    
    # Detect displacement
    displacement = detect_displacement(price_data, min_range_pct=1.5)
    
    # Create entry signals (simplified Asian range + London sweep detection)
    entries = pd.Series(False, index=price_data.index)
    
    # Simplified Asian range calculation (highest high during Asia session)
    asian_high = pd.Series(0.0, index=price_data.index)
    asian_low = pd.Series(999999.0, index=price_data.index)
    
    for i in range(len(price_data)):
        if asia_mask.iloc[i]:
            asian_high.iloc[i] = max(asian_high.iloc[i], price_data['high'].iloc[i])
            asian_low.iloc[i] = min(asian_low.iloc[i], price_data['low'].iloc[i])
    
    # Forward-fill Asian range for London session
    asian_high = asian_high.ffill()
    asian_low = asian_low.ffill()
    
    for i in range(len(price_data)):
        # Check London open window
        if not london_mask.iloc[i]:
            continue
        
        # Check HTF bias
        if bias.iloc[i] == "NEUTRAL":
            continue
        
        # Check for sweep of Asian range (simplified)
        if bias.iloc[i] == "LONG":
            # Looking for sweep of Asian low (SSL)
            if price_data['low'].iloc[i] < asian_low.iloc[i]:
                # Check for displacement after sweep
                if i < len(price_data) - 1 and displacement.iloc[i+1]:
                    # Entry on reversal
                    entries.iloc[i+1] = True
        else:  # SHORT
            # Looking for sweep of Asian high (BSL)
            if price_data['high'].iloc[i] > asian_high.iloc[i]:
                # Check for displacement after sweep
                if i < len(price_data) - 1 and displacement.iloc[i+1]:
                    # Entry on reversal
                    entries.iloc[i+1] = True
    
    # Calculate stops based on swept Asian level
    stops = pd.Series(0.0, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            # Estimate stop as swept Asian level + buffer
            if bias.iloc[i] == "LONG":
                stop = asian_low.iloc[i] - cfg.stop_buffer
            else:
                stop = asian_high.iloc[i] + cfg.stop_buffer
            stops.iloc[i] = stop
    
    # Calculate exits (take profit)
    exits = pd.Series(False, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            entry_price = price_data['close'].iloc[i]
            stop_price = stops.iloc[i]
            
            # Calculate target price (opposing Asian level)
            if bias.iloc[i] == "LONG":
                target = asian_high.iloc[i]
            else:
                target = asian_low.iloc[i]
            
            # Exit when target reached
            for j in range(i+1, len(price_data)):
                if price_data['high'].iloc[j] >= target >= price_data['low'].iloc[j]:
                    exits.iloc[j] = True
                    break
    
    return entries, exits


def run_backtest(cfg: AsianRangeSweepConfig) -> vbt.Portfolio:
    """
    Run backtest for Asian Range Sweep strategy.
    
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
    from config import AsianRangeSweepConfig
    
    cfg = AsianRangeSweepConfig()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("asian_range_sweep", "1.0")
    
    print(f"Asian Range Sweep Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"Asia Session: {cfg.asia_start}-{cfg.asia_end} NY")
    print(f"London Session: {cfg.london_start}-{cfg.london_end} NY")
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
