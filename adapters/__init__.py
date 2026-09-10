"""
Strategy Adapters for VECTORBT BACKTEST AGENT

This package provides strategy-specific adapters for complex strategies that require
special handling beyond the standard from_signals() constructor.

Adapters handle:
- Partial exit strategies (Silver Bullet, Unicorn)
- Aggressive trailing strategies (ICT 2024)
- Special entry logic (Venom, Asian Range Sweep, Judas Swing)
"""

from .base_adapter import BaseAdapter
from .silver_bullet_ny_am_adapter import SilverBulletNYAMAdapter
from .silver_bullet_london_adapter import SilverBulletLondonAdapter
from .unicorn_adapter import UnicornAdapter
from .ict_2024_adapter import ICT2024Adapter
from .venom_adapter import VenomAdapter
from .asian_range_sweep_adapter import AsianRangeSweepAdapter
from .judas_swing_adapter import JudasSwingAdapter

__all__ = [
    'BaseAdapter',
    'SilverBulletNYAMAdapter',
    'SilverBulletLondonAdapter',
    'UnicornAdapter',
    'ICT2024Adapter',
    'VenomAdapter',
    'AsianRangeSweepAdapter',
    'JudasSwingAdapter',
]
