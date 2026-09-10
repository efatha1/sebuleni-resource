"""
Venom Model Strategy Adapter

Handles pre-open range detection and false breakout confirmation.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Any, Tuple
from .base_adapter import BaseAdapter


class VenomAdapter(BaseAdapter):
    """
    Adapter for Venom Model strategy.

    Strategy specifics:
    - 2025 evolution model
    - Pre-open range detection
    - False breakout confirmation
    - May use from_order_func for complex entry logic
    - Can use from_signals if entry logic is simple
    """

    def get_strategy_id(self) -> str:
        return "venom"

    def validate_config(self, config: Any) -> bool:
        """Validate Venom config has required attributes."""
        required_attrs = [
            'pre_open_window',
            'range_threshold_pct',
            'false_breakout_threshold',
            'tp_r', 'init_cash', 'fees'
        ]
        for attr in required_attrs:
            if not hasattr(config, attr):
                return False
        return True

    def preprocess_signals(
        self,
        price_data: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        config: Any
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Preprocess signals for Venom strategy.

        Venom may require filtering entries based on pre-open range
        and false breakout confirmation. This can be done here if needed.
        """
        # For now, return signals as-is
        # Future enhancement: add pre-open range filtering
        return entries, exits

    def create_portfolio(
        self,
        price_data: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        config: Any,
        strategy_module: Any
    ) -> vbt.Portfolio:
        """
        Create portfolio for Venom strategy.

        Venom can use from_signals if entry logic is handled in generate_signals.
        If complex entry/exit management is needed, use from_order_func.
        """
        # Validate config
        if not self.validate_config(config):
            raise ValueError(f"Invalid config for {self.get_strategy_id()}")

        # Preprocess signals
        entries, exits = self.preprocess_signals(price_data, entries, exits, config)

        # Check if strategy has order_func (complex management)
        if hasattr(strategy_module, 'order_func'):
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
        else:
            # Use from_signals with stop/TP
            # Calculate stop distances (simplified)
            stop_distances = pd.Series(0.01, index=price_data.index)
            tp_distances = stop_distances * config.tp_r

            portfolio = vbt.Portfolio.from_signals(
                price_data['close'],
                entries,
                exits,
                init_cash=config.init_cash,
                fees=config.fees,
                sl_stop=stop_distances,
                tp_stop=tp_distances,
                freq='5T',
                init_position='cash',
                cash_sharing=True
            )

        return portfolio
