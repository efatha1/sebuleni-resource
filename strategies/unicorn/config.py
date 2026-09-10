"""
Unicorn Strategy Configuration

Configuration dataclass for the Unicorn strategy from the ICT Unified Trading Book.
High-conviction subset of 2022 Model with additional displacement strength filter.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UnicornConfig:
    """Configuration for Unicorn Strategy"""
    
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
    
    # Unicorn-specific filters
    min_body_ratio: float = 0.60  # Displacement must have ≥60% body
    max_opposing_wick_ratio: float = 0.20  # Displacement must have ≤20% opposing wick
    
    # Extended targets
    tp1_r: float = 2.0  # TP1 at 2.0R
    tp2_r: float = 4.0  # TP2 at 4.0R
    tp1_close_pct: float = 0.25  # Close 25% at TP1
    tp2_close_pct: float = 0.25  # Close 25% at TP2
    runner_pct: float = 0.50  # Hold 50% as runner
    expected_r: float = 8.0  # Expected R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: Requires Portfolio.from_order_func for partial exits and extended targets
