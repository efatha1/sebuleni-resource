"""
London Close Reversal Strategy Configuration

Configuration dataclass for the London Close Reversal strategy from the ICT Unified Trading Book.
Session-anchored reversal/continuation model during London Close (10:00-12:00 NY).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LondonCloseReversalConfig:
    """Configuration for London Close Reversal Strategy"""
    
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
    killzone: str = "london_close"
    killzone_start: str = "10:00"
    killzone_end: str = "12:00"
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: European book unwind, reversal of London-open direction
