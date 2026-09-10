"""
ICT 2024 Model Strategy Configuration

Configuration dataclass for the ICT 2024 Model from the ICT Unified Trading Book.
Evolution of 2023 Model with stricter competing FVG filter and aggressive trailing after 1.5R.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ICT2024Config:
    """Configuration for ICT 2024 Model Strategy"""
    
    # Instrument and data
    symbol: str = "XAUUSD"
    htf_timeframe: str = "1d"
    ltf_timeframe: str = "5m"
    htf_bias_lookback: int = 20
    
    # Account and risk
    equity: float = 100000.0
    risk_pct: float = 0.01
    pip_value: float = 0.01  # For XAUUSD (dollars)
    
    # Strategy-specific parameters
    killzone: str = "any"  # Any killzone (no specific hour constraint)
    min_fvg_gap: float = 0.50  # Minimum FVG gap in dollars for XAUUSD
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # 2024 Model specific
    min_range_pct: float = 1.5  # Displacement strength filter
    check_competing_fvg: bool = True  # Stricter competing FVG filter
    trail_after_r: float = 1.5  # Start trailing after 1.5R
    trail_to_r: float = 0.5  # Trail stop to 0.5R from entry
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: 2024 evolution adds aggressive trailing after 1.5R
    # Requires Portfolio.from_order_func for stateful trailing
