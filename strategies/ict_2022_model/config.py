"""
ICT 2022 Model Strategy Configuration

Configuration dataclass for the ICT 2022 Model (flagship framework) from the ICT Unified Trading Book.
Same sequence as Silver Bullet but without the 60-minute time constraint.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class ICT2022Config:
    """Configuration for ICT 2022 Model Strategy"""
    
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
    killzone: Literal["any", "london_open", "ny_am", "london_close"] = "any"
    min_fvg_gap: float = 0.50  # Minimum FVG gap in dollars for XAUUSD
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: 2022 Model can work in any killzone, unlike Silver Bullet
    # Uses same displacement + FVG + CE entry sequence as Silver Bullet
