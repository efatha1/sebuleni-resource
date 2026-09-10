"""
Order Block Entry Strategy Configuration

Configuration dataclass for the Order Block Entry strategy from the ICT Unified Trading Book.
This strategy enters on Order Block retest.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderBlockConfig:
    """Configuration for Order Block Entry Strategy"""
    
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
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
