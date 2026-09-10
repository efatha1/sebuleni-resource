"""
FVG/CE Entry Strategy Configuration

Configuration dataclass for the FVG/CE Entry strategy from the ICT Unified Trading Book.
This strategy uses the 2025 primary entry methodology using FVG Consequent Encroachment (CE).
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class FVGCEConfig:
    """Configuration for FVG/CE Entry Strategy"""
    
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
    min_fvg_gap: float = 0.50  # Minimum FVG gap in dollars for XAUUSD
    stop_method: Literal["far_edge", "ce_tight"] = "far_edge"
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0  # No fees for this backtest
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: Book specifies "min_gap_pips" but XAUUSD uses dollars
    # Conversion: Book says "min_gap_pips" → Use dollar values (e.g., 0.50 dollars)
    # Stop buffer: Book says "stop_buffer" → Use dollar values (e.g., 0.30 dollars)
