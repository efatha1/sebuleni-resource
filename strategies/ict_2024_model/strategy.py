"""
ICT 2024 Model Strategy Implementation

Evolution of 2023 Model with stricter competing FVG filter and aggressive trailing after 1.5R.

Strategy Specification from ICT Unified Trading Book:
- Evolution of 2023 Model
- Stricter competing FVG filter
- Aggressive trailing after 1.5R (move SL to 0.5R from entry)
- Same sequence as 2022/2023 Model

Portfolio Constructor: Portfolio.from_order_func() (aggressive trailing requires stateful management)

Deviation Notes:
- Uses from_order_func for aggressive trailing functionality
- Trailing stop implemented in order_func
- Simplified displacement detection for demonstration
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
    fair_value_gaps, fvg_ce_entry, htf_bias, Direction,
    in_killzone, detect_displacement, displacement_strength
)
from data_loader import load_data
from config import ICT2024Config


def generate_signals(price_data: pd.DataFrame, cfg: ICT2024Config) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for ICT 2024 Model strategy.
    
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
    
    # Killzone mask (if specified)
    if cfg.killzone != "any":
        killzone_mask = in_killzone(price_data.index, cfg.killzone)
    else:
        killzone_mask = pd.Series(True, index=price_data.index)
    
    # Detect FVGs
    fvgs = fair_value_gaps(price_data, min_gap_pips=cfg.min_fvg_gap)
    
    # Detect displacement
    displacement = detect_displacement(price_data, min_range_pct=cfg.min_range_pct)
    
    # Calculate displacement strength
    strength = displacement_strength(price_data)
    
    # Create entry signals
    entries = pd.Series(False, index=price_data.index)
    
    for i in range(len(price_data)):
        # Check killzone
        if not killzone_mask.iloc[i]:
            continue
        
        # Check HTF bias
        if bias.iloc[i] == "NEUTRAL":
            continue
        
        # Check for displacement with strength filter
        if not displacement.iloc[i]:
            continue
        
        # Check displacement strength
        if strength['body_ratio'].iloc[i] < cfg.min_range_pct:
            continue
        
        # Check for competing FVGs (stricter in 2024)
        if cfg.check_competing_fvg:
            recent_fvgs = fvgs[fvgs['timestamp'] <= price_data.index[i]]
            if len(recent_fvgs) > 0:
                latest_fvg = recent_fvgs.iloc[-1]
                fvg_direction = latest_fvg['direction']
                expected_direction = 'short' if bias.iloc[i] == 'LONG' else 'long'
                if fvg_direction == expected_direction:
                    continue  # Competing FVG present, skip
        
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
    
    # No exits here - handled by order_func
    exits = pd.Series(False, index=price_data.index)
    
    return entries, exits


def order_func(context, cfg):
    """
    Custom order function for ICT 2024 Model with aggressive trailing.
    
    Implements:
    - Entry at FVG CE
    - Stop at FVG far edge
    - Trailing stop after 1.5R (move to 0.5R from entry)
    - Exit at TP (2R) or when stop hit
    """
    # Access context
    entries = context['entries']
    close = context['close']
    idx = context['idx']
    
    # Get stop price from context state
    if not hasattr(context, 'state'):
        context.state = {}
    
    order_df = pd.DataFrame(index=entries.index)
    order_df['size'] = 0.0
    order_df['price'] = np.nan
    
    # Entry logic
    if entries.iloc[idx]:
        order_df.iloc[idx, order_df.columns.get_loc('size')] = 1.0
        order_df.iloc[idx, order_df.columns.get_loc('price')] = close.iloc[idx]
        
        # Store entry info in state
        if idx not in context.state:
            context.state[idx] = {
                'entry_price': close.iloc[idx],
                'stop_price': None,
                'trail_started': False
            }
    
    # Trailing logic for open positions
    for entry_idx, state in context.state.items():
        if entry_idx < idx and 'entry_price' in state:
            entry_price = state['entry_price']
            current_price = close.iloc[idx]
            
            # Calculate R-multiple
            if state['stop_price'] is None:
                risk = abs(entry_price - (entry_price * 0.99))  # Simplified risk
            else:
                risk = abs(entry_price - state['stop_price'])
            
            r_multiple = abs(current_price - entry_price) / risk if risk > 0 else 0
            
            # Start trailing after 1.5R
            if r_multiple >= cfg.trail_after_r and not state['trail_started']:
                state['trail_started'] = True
                # Move stop to 0.5R from entry
                if entry_price < current_price:  # Long
                    state['stop_price'] = entry_price + (risk * cfg.trail_to_r)
                else:  # Short
                    state['stop_price'] = entry_price - (risk * cfg.trail_to_r)
            
            # Check stop hit
            if state['stop_price'] is not None:
                if entry_price < current_price and current_price < state['stop_price']:  # Long stop hit
                    order_df.iloc[idx, order_df.columns.get_loc('size')] = -1.0
                    order_df.iloc[idx, order_df.columns.get_loc('price')] = current_price
                elif entry_price > current_price and current_price > state['stop_price']:  # Short stop hit
                    order_df.iloc[idx, order_df.columns.get_loc('size')] = -1.0
                    order_df.iloc[idx, order_df.columns.get_loc('price')] = current_price
            
            # Check TP hit (2R)
            if r_multiple >= cfg.tp_r:
                order_df.iloc[idx, order_df.columns.get_loc('size')] = -1.0
                order_df.iloc[idx, order_df.columns.get_loc('price')] = current_price
    
    return order_df


def run_backtest(cfg: ICT2024Config) -> vbt.Portfolio:
    """
    Run backtest for ICT 2024 Model strategy.
    
    Args:
        cfg: Strategy configuration
    
    Returns:
        vectorbt Portfolio object
    """
    # Load data
    price_data = load_data(cfg.symbol, cfg.ltf_timeframe)
    
    # Generate signals
    entries, exits = generate_signals(price_data, cfg)
    
    # Create portfolio using from_order_func for aggressive trailing
    portfolio = vbt.Portfolio.from_order_func(
        price_data['close'],
        entries,
        exits,
        init_cash=cfg.init_cash,
        fees=cfg.fees,
        order_func=lambda context: order_func(context, cfg),
        freq='5T'
    )
    
    return portfolio


if __name__ == "__main__":
    import sys
    import os
    import json
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from backtest_agent import BacktestAgent
    from config import ICT2024Config
    
    cfg = ICT2024Config()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("ict_2024_model", "1.0")
    
    print(f"ICT 2024 Model Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"Killzone: {cfg.killzone}")
    print(f"Trail After: {cfg.trail_after_r}R")
    print(f"Trail To: {cfg.trail_to_r}R")
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
