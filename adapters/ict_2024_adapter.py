"""
ICT 2024 Model Strategy Adapter

Handles aggressive trailing stop after 1.5R (move to 0.5R from entry).
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Any, Tuple
from .base_adapter import BaseAdapter


class ICT2024Adapter(BaseAdapter):
    """
    Adapter for ICT 2024 Model strategy.

    Strategy specifics:
    - Evolution of 2023 Model with stricter competing FVG filter
    - Aggressive trailing after 1.5R (move stop to 0.5R from entry)
    - No partial exits (uses full position with trailing)
    - Uses from_order_func for stateful trailing management
    """

    def get_strategy_id(self) -> str:
        return "ict_2024_model"

    def validate_config(self, config: Any) -> bool:
        """Validate ICT 2024 config has required attributes."""
        required_attrs = [
            'trail_after_r', 'trail_to_r',
            'min_range_pct', 'check_competing_fvg',
            'tp_r', 'init_cash', 'fees'
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
        Create portfolio using from_order_func for aggressive trailing.

        The strategy module must have an order_func that:
        - Handles entry at FVG CE
        - Implements aggressive trailing after 1.5R
        - Moves stop to 0.5R from entry when trailing starts
        - Exits at TP (2R) or when stop hit
        """
        # Validate config
        if not self.validate_config(config):
            raise ValueError(f"Invalid config for {self.get_strategy_id()}")

        # Preprocess signals (no modification needed for ICT 2024)
        entries, exits = self.preprocess_signals(price_data, entries, exits, config)

        # Create portfolio using from_order_func for trailing
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
