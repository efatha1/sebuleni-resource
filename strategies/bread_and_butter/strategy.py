"""
Bread-and-Butter Setup Strategy Implementation

Daily sequence framework (PM-Asia-London-NY). Executes 2022 model in London or NY AM.
Most frequent, dependable setup (not highest conviction, but most repeatable).

Strategy Specification from ICT Unified Trading Book:
- B&B is the daily sequence: PM range → Asia extension → London raid → NY delivery
- Trader executes during London or NY AM segments using standard 2022 model rules
- Most frequent, dependable setup

Portfolio Constructor: Portfolio.from_signals() (single SL + single TP)

Deviation Notes:
- Reuses ICT 2022 Model signal generation logic
- Daily sequence detection simplified for demonstration
- In production, would implement full PM-Asia-London-NY sequence detection
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
    fair_value_gaps, fvg_ce_entry
)
from data_loader import load_data
from config import BreadAndButterConfig


def generate_signals(price_data: pd.DataFrame, cfg: BreadAndButterConfig) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for Bread-and-Butter Setup strategy.
    
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
    
    # Execution window mask (London or NY AM)
    if cfg.execution_window == "london_open":
        window_mask = in_killzone(price_data.index, "london_open")
    else:  # ny_am
        window_mask = in_killzone(price_data.index, "ny_am")
    
    # Detect FVGs
    fvgs = fair_value_gaps(price_data, min_gap_pips=cfg.min_fvg_gap)
    
    # Detect displacement
    displacement = detect_displacement(price_data, min_range_pct=1.5)
    
    # Create entry signals (simplified B&B sequence detection)
    # In production, would detect full PM-Asia-London-NY sequence
    entries = pd.Series(False, index=price_data.index)
    
    for i in range(len(price_data)):
        # Check execution window
        if not window_mask.iloc[i]:
            continue
        
        # Check HTF bias
        if bias.iloc[i] == "NEUTRAL":
            continue
        
        # Check for displacement + FVG (standard 2022 model logic)
        if not displacement.iloc[i]:
            continue
        
        # Check for FVG formation with CE entry
        if i >= 2 and len(fvgs) > 0:
            recent_fvgs = fvgs[fvgs['timestamp'] <= price_data.index[i]]
            if len(recent_fvgs) > 0:
                latest_fvg = recent_fvgs.iloc[-1]
                fvg_direction = latest_fvg['direction']
                
                # Check FVG direction alignment with HTF bias
                if bias.iloc[i] == fvg_direction.upper():
                    # Check for CE retest
                    ce = latest_fvg['ce']
                    if abs(price_data['close'].iloc[i] - ce) <= cfg.stop_buffer:
                        entries.iloc[i] = True
    
    # Calculate stops based on FVG far edge
    stops = pd.Series(0.0, index=price_data.index)
    
    for i, entry in enumerate(entries):
        if entry:
            # Find most recent FVG before entry
            recent_fvgs = fvgs[fvgs['timestamp'] <= price_data.index[i]]
            if len(recent_fvgs) > 0:
                latest_fvg = recent_fvgs.iloc[-1]
                stop = latest_fvg['high'] if latest_fvg['direction'] == 'short' else latest_fvg['low']
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


def run_backtest(cfg: BreadAndButterConfig) -> vbt.Portfolio:
    """
    Run backtest for Bread-and-Butter Setup strategy.
    
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
    from config import BreadAndButterConfig
    
    cfg = BreadAndButterConfig()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("bread_and_butter", "1.0")
    
    print(f"Bread-and-Butter Setup Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"Execution Window: {cfg.execution_window}")
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
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Data file not found. Use sample data for testing:")
        print(">>> from data_loader import create_sample_data")
        print(">>> df = create_sample_data('XAUUSD', '5m')")
        print(">>> df.to_parquet('data/XAUUSD_5m.parquet')")
