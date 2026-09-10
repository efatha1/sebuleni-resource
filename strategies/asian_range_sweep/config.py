"""
Asian Range Sweep Strategy Configuration

Configuration dataclass for the Asian Range Sweep strategy from the ICT Unified Trading Book.
Trade the sweep of Asian range liquidity during London Open.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AsianRangeSweepConfig:
    """Configuration for Asian Range Sweep Strategy"""
    
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
    asia_start: str = "18:00"  # Asia session start (NY time)
    asia_end: str = "03:00"    # Asia session end (NY time)
    london_start: str = "02:00"  # London open start (NY time)
    london_end: str = "05:00"    # London open end (NY time)
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: Asia range established 18:00-03:00 NY, London sweep 02:00-05:00 NY
