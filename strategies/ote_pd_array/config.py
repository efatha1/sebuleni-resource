"""
OTE + PD Array Entry Strategy Configuration

Configuration dataclass for the OTE + PD Array Entry strategy from the ICT Unified Trading Book.
Canonical OTE methodology with PD array confluence. Continuation setup (no counter-sweep required).
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class OTEPDArrayConfig:
    """Configuration for OTE + PD Array Entry Strategy"""
    
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
    ote_zone_low: float = 0.625  # ICT 0.625 fib level
    ote_zone_high: float = 0.79   # ICT 0.79 fib level
    stop_method: Literal["fixed_pips", "leg_origin"] = "fixed_pips"  # 2020 era
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    era: str = "2020"  # 2020 era uses fixed pips, 2017 uses leg origin
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: Era-fork stop placement (2017 = leg origin; 2020 = fixed pips)
    # Using 2020 era (fixed pips) as default
