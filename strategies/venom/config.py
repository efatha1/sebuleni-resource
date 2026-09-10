"""
Venom Model Strategy Configuration

Configuration dataclass for the Venom Model strategy from the ICT Unified Trading Book.
Time-constrained range reversal model. Pre-cash-open range sweep → false breakout → reversal.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VenomConfig:
    """Configuration for Venom Model Strategy"""
    
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
    pre_open_start: str = "08:00"  # Pre-cash-open range start (NY time)
    pre_open_end: str = "09:30"    # Pre-cash-open range end (NY time)
    trigger_start: str = "09:30"    # Trigger window start (NY time)
    trigger_end: str = "11:00"      # Trigger window end (NY time)
    stop_buffer: float = 0.50  # Stop buffer in dollars for XAUUSD (adapted from indices)
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: Designed for US indices (NQ, ES, YM). Adapted for XAUUSD with different stop_buffer.
