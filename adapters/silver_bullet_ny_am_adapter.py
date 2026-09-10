"""
Silver Bullet (NY AM) Strategy Adapter

Handles partial exits (33% TP1, 33% TP2, 34% runner) and breakeven trailing.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Any, Tuple
from .base_adapter import BaseAdapter


class SilverBulletNYAMAdapter(BaseAdapter):
    """
    Adapter for Silver Bullet (NY AM) strategy.

    Strategy specifics:
    - Time constraint: 10:00-11:00 NY
    - Partial exits: 33% TP1 at 1.5R, 33% TP2 at 2.0R, 34% runner
    - Breakeven trailing after TP1
    - Uses from_order_func for stateful management
    """

    def get_strategy_id(self) -> str:
        return "silver_bullet_ny_am"

    def validate_config(self, config: Any) -> bool:
        """Validate Silver Bullet NY AM config has required attributes."""
        required_attrs = [
            'tp1_r', 'tp1_close_pct',
            'tp2_r', 'tp2_close_pct',
            'runner_pct', 'init_cash', 'fees'
        ]
        for attr in required_attrs:
            if not hasattr(config, attr):
                return False
        return True

    def create_portfolio(
        self,
        price_data: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        config: Any,
        strategy_module: Any
    ) -> vbt.Portfolio:
        """
        Create portfolio using from_order_func for partial exits and trailing.

        The strategy module must have an order_func that:
        - Handles entry at FVG CE
        - Implements TP1/TP2 partial exits
        - Moves stop to breakeven after TP1
        - Tracks partial exits in state for trade recording
        """
        # Validate config
        if not self.validate_config(config):
            raise ValueError(f"Invalid config for {self.get_strategy_id()}")

        # Preprocess signals (no modification needed for Silver Bullet)
        entries, exits = self.preprocess_signals(price_data, entries, exits, config)

        # Create portfolio using from_order_func
        portfolio = vbt.Portfolio.from_order_func(
            price_data['close'],
            entries,
            exits,
            init_cash=config.init_cash,
            fees=config.fees,
            order_func=lambda context: strategy_module.order_func(context, config),
            freq='5T',
            init_position='cash',
            cash_sharing=True
        )

        return portfolio
