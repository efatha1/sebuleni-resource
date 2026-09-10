"""
ICT 2023 Model Strategy Configuration

Configuration dataclass for the ICT 2023 Model from the ICT Unified Trading Book.
Evolution of 2022 Model with displacement strength filter and competing FVG filter.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ICT2023Config:
    """Configuration for ICT 2023 Model Strategy"""
    
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
    
    # 2023 Model specific
    min_range_pct: float = 1.5  # Displacement strength filter (≥1.5x average range)
    check_competing_fvg: bool = True  # Check for competing FVGs
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: 2023 evolution from 2022 Model adds displacement strength filter
