"""
NY PM Reversal Strategy Configuration

Configuration dataclass for the NY PM Reversal strategy from the ICT Unified Trading Book.
Session-anchored reversal/continuation model during NY PM (13:30-16:00 NY).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NYPMReversalConfig:
    """Configuration for NY PM Reversal Strategy"""
    
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
    killzone: str = "ny_pm"
    killzone_start: str = "13:30"
    killzone_end: str = "16:00"
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: Continuation or reversal of NY AM direction
