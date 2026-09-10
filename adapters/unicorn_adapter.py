"""
Unicorn Strategy Adapter

Handles partial exits (25% TP1, 25% TP2, 50% runner) with extended targets.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Any, Tuple
from .base_adapter import BaseAdapter


class UnicornAdapter(BaseAdapter):
    """
    Adapter for Unicorn strategy.

    Strategy specifics:
    - High-conviction subset of 2022 Model
    - Displacement strength filter (≥60% body, ≤20% opposing wick)
    - Extended targets (8R+)
    - Partial exits: 25% TP1 at 2.0R, 25% TP2 at 4.0R, 50% runner
    - Uses from_order_func for stateful management
    """

    def get_strategy_id(self) -> str:
        return "unicorn"

    def validate_config(self, config: Any) -> bool:
        """Validate Unicorn config has required attributes."""
        required_attrs = [
            'tp1_r', 'tp1_close_pct',
            'tp2_r', 'tp2_close_pct',
            'runner_pct', 'expected_r',
            'min_body_pct', 'max_opposing_wick_ratio',
            'init_cash', 'fees'
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
        Create portfolio using from_order_func for partial exits.

        The strategy module must have an order_func that:
        - Handles entry at FVG CE with displacement filter
        - Implements TP1/TP2 partial exits
        - Tracks partial exits in state for trade recording
        """
        # Validate config
        if not self.validate_config(config):
            raise ValueError(f"Invalid config for {self.get_strategy_id()}")

        # Preprocess signals (no modification needed for Unicorn)
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
