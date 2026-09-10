"""
Bread-and-Butter Setup Strategy Configuration

Configuration dataclass for the Bread-and-Butter Setup strategy from the ICT Unified Trading Book.
Daily sequence framework (PM-Asia-London-NY). Executes 2022 model in London or NY AM.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class BreadAndButterConfig:
    """Configuration for Bread-and-Butter Setup Strategy"""
    
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
    execution_window: Literal["london_open", "ny_am"] = "london_open"
    min_fvg_gap: float = 0.50  # Minimum FVG gap in dollars for XAUUSD
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    tp_r: float = 2.0  # Target R-multiple
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: B&B is a framework, not a specific entry methodology
    # Uses standard 2022 model rules in London or NY AM window
