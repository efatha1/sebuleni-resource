"""
Judas Swing Entry Strategy Configuration

Configuration dataclass for the Judas Swing Entry strategy from the ICT Unified Trading Book.
Session-anchored manipulation phase entry. Most common at London Open. Trade the reversal, not the manipulation itself.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class JudasSwingConfig:
    """Configuration for Judas Swing Entry Strategy"""
    
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
    session: Literal["london_open", "ny_am"] = "london_open"  # Primary session
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: London Open: 02:00-05:00 NY (primary), NY AM: 08:00-11:00 NY (smaller scale)
