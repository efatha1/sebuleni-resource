"""
Silver Bullet (NY AM) Strategy Configuration

Configuration dataclass for the Silver Bullet (NY AM) strategy from the ICT Unified Trading Book.
Highest-probability Silver Bullet window during NY AM killzone (10:00–11:00 NY).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SilverBulletNYAMConfig:
    """Configuration for Silver Bullet (NY AM) Strategy"""
    
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
    killzone: str = "ny_am"
    killzone_start: str = "10:00"
    killzone_end: str = "11:00"
    min_fvg_gap: float = 0.50  # Minimum FVG gap in dollars for XAUUSD
    stop_buffer: float = 0.30  # Stop buffer in dollars for XAUUSD
    
    # Partial exits
    tp1_r: float = 1.5  # TP1 at 1.5R
    tp2_r: float = 2.0  # TP2 at 2.0R
    tp1_close_pct: float = 0.33  # Close 33% at TP1
    tp2_close_pct: float = 0.33  # Close 33% at TP2
    runner_pct: float = 0.34  # Hold 34% as runner
    
    # Backtest parameters
    init_cash: float = 100000.0
    fees: float = 0.0
    
    # Date filtering for backtest
    start_date: Optional[str] = None  # e.g., "2024-01-01"
    end_date: Optional[str] = None    # e.g., "2024-12-31"
    
    # Note: Requires Portfolio.from_order_func for partial exits and breakeven trailing
