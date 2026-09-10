"""
Silver Bullet (NY AM) Strategy Implementation

Highest-probability Silver Bullet window during NY AM killzone (10:00–11:00 NY).
Combines time constraint with full 2022 Model sequence. Highest conviction of the three SB windows.

Strategy Specification from ICT Unified Trading Book:
- Time: 10:00–11:00 NY (NY AM killzone + London Close overlap)
- Session: NY AM with London Close overlap
- HTF bias: Must be clear (D/W aligned)
- Partial exits: 33% TP1, 33% TP2, 34% runner
- Breakeven after TP1

Portfolio Constructor: Portfolio.from_order_func() (partial exits + breakeven trailing)

Deviation Notes:
- Uses from_order_func for partial exits and breakeven trailing
- Simplified displacement and liquidity sweep detection for demonstration
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
    in_killzone, detect_displacement, liquidity_sweep
)
from data_loader import load_data
from config import SilverBulletNYAMConfig
from backtest_agent import get_order_func_state_tracker


def generate_signals(price_data: pd.DataFrame, cfg: SilverBulletNYAMConfig) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry and exit signals for Silver Bullet (NY AM) strategy.
    
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
    
    # NY AM killzone mask (10:00-11:00)
    killzone_mask = in_killzone(price_data.index, "ny_am")
    
    # Detect FVGs
    fvgs = fair_value_gaps(price_data, min_gap_pips=cfg.min_fvg_gap)
    
    # Detect displacement
    displacement = detect_displacement(price_data, min_range_pct=1.5)
    
    # Create entry signals
    entries = pd.Series(False, index=price_data.index)
    
    for i in range(len(price_data)):
        # Check killzone (10:00-11:00 NY)
        if not killzone_mask.iloc[i]:
            continue
        
        # Check HTF bias
        if bias.iloc[i] == "NEUTRAL":
            continue
        
        # Check for displacement
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
    
    # No exits here - handled by order_func
    exits = pd.Series(False, index=price_data.index)
    
    return entries, exits


def order_func(context, cfg):
    """
    Custom order function for Silver Bullet (NY AM) with partial exits and breakeven trailing.

    Implements:
    - Entry at FVG CE
    - Stop at swept level + buffer
    - TP1 at 1.5R (close 33%)
    - TP2 at 2.0R (close 33%)
    - Breakeven after TP1
    - Hold 34% as runner
    """
    # Access context
    entries = context['entries']
    close = context['close']
    idx = context['idx']

    # Get state tracker for partial exit recording
    state_tracker = get_order_func_state_tracker()

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
                'stop_price': close.iloc[idx] * 0.99,  # Simplified stop
                'tp1_hit': False,
                'tp2_hit': False,
                'position_size': 1.0,
                'partial_exits': []  # Track partial exits for trade recording
            }
            # Also store in module-level tracker for access after execution
            state_tracker[idx] = context.state[idx]
    
    # Partial exit and trailing logic for open positions
    for entry_idx, state in context.state.items():
        if entry_idx < idx and 'entry_price' in state:
            entry_price = state['entry_price']
            current_price = close.iloc[idx]
            stop_price = state['stop_price']
            
            # Calculate R-multiple
            risk = abs(entry_price - stop_price)
            r_multiple = abs(current_price - entry_price) / risk if risk > 0 else 0
            
            # TP1 at 1.5R (close 33%)
            if r_multiple >= cfg.tp1_r and not state['tp1_hit']:
                state['tp1_hit'] = True
                state['position_size'] *= (1 - cfg.tp1_close_pct)  # Reduce position
                order_df.iloc[idx, order_df.columns.get_loc('size')] = -cfg.tp1_close_pct
                order_df.iloc[idx, order_df.columns.get_loc('price')] = current_price

                # Track partial exit for trade recording
                state['partial_exits'].append({
                    "target_id": "TP1",
                    "target_price": current_price,
                    "target_hit_time": idx,
                    "partial_exit_size": cfg.tp1_close_pct,
                    "remaining_position": state['position_size']
                })
                # Sync with module-level tracker
                if entry_idx in state_tracker:
                    state_tracker[entry_idx] = state

                # Move SL to breakeven
                state['stop_price'] = entry_price
            
            # TP2 at 2.0R (close 33%)
            if r_multiple >= cfg.tp2_r and not state['tp2_hit']:
                state['tp2_hit'] = True
                state['position_size'] *= (1 - cfg.tp2_close_pct)  # Reduce position
                order_df.iloc[idx, order_df.columns.get_loc('size')] = -cfg.tp2_close_pct
                order_df.iloc[idx, order_df.columns.get_loc('price')] = current_price

                # Track partial exit for trade recording
                state['partial_exits'].append({
                    "target_id": "TP2",
                    "target_price": current_price,
                    "target_hit_time": idx,
                    "partial_exit_size": cfg.tp2_close_pct,
                    "remaining_position": state['position_size']
                })
                # Sync with module-level tracker
                if entry_idx in state_tracker:
                    state_tracker[entry_idx] = state
            
            # Check stop hit
            if entry_price < current_price and current_price < stop_price:  # Long stop hit
                order_df.iloc[idx, order_df.columns.get_loc('size')] = -state['position_size']
                order_df.iloc[idx, order_df.columns.get_loc('price')] = current_price
            elif entry_price > current_price and current_price > stop_price:  # Short stop hit
                order_df.iloc[idx, order_df.columns.get_loc('size')] = -state['position_size']
                order_df.iloc[idx, order_df.columns.get_loc('price')] = current_price
    
    return order_df


def run_backtest(cfg: SilverBulletNYAMConfig) -> vbt.Portfolio:
    """
    Run backtest for Silver Bullet (NY AM) strategy.
    
    Args:
        cfg: Strategy configuration
    
    Returns:
        vectorbt Portfolio object
    """
    # Load data
    price_data = load_data(cfg.symbol, cfg.ltf_timeframe)
    
    # Generate signals
    entries, exits = generate_signals(price_data, cfg)
    
    # Create portfolio using from_order_func for partial exits and trailing
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
    from config import SilverBulletNYAMConfig
    
    cfg = SilverBulletNYAMConfig()
    cfg.start_date = "2024-01-01"  # Optional date filtering
    cfg.end_date = "2024-12-31"
    
    agent = BacktestAgent("silver_bullet_ny_am", "1.0")
    
    print(f"Silver Bullet (NY AM) Strategy Backtest")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.ltf_timeframe}")
    print(f"Killzone: {cfg.killzone_start}-{cfg.killzone_end} NY")
    print(f"TP1: {cfg.tp1_r}R (close {cfg.tp1_close_pct * 100}%)")
    print(f"TP2: {cfg.tp2_r}R (close {cfg.tp2_close_pct * 100}%)")
    print(f"Runner: {cfg.runner_pct * 100}%")
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
