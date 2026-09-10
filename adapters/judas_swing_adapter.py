"""
Judas Swing Strategy Adapter

Handles liquidity sweep detection and counter-trend entry logic.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Any, Tuple
from .base_adapter import BaseAdapter


class JudasSwingAdapter(BaseAdapter):
    """
    Adapter for Judas Swing strategy.

    Strategy specifics:
    - Liquidity sweep detection (stop hunt)
    - Counter-trend entry after sweep
    - May use from_order_func for sweep confirmation logic
    - Can use from_signals if entry logic is handled in generate_signals
    """

    def get_strategy_id(self) -> str:
        return "judas_swing"

    def validate_config(self, config: Any) -> bool:
        """Validate Judas Swing config has required attributes."""
        required_attrs = [
            'liquidity_level_lookback',
            'sweep_threshold_pct',
            'entry_confirmation_candles',
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
        Preprocess signals for Judas Swing strategy.

        Judas Swing may require filtering entries based on
        confirmed liquidity sweeps. This can be done here.
        """
        # For now, return signals as-is
        # Future enhancement: add sweep confirmation filtering
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
        Create portfolio for Judas Swing strategy.

        Judas Swing can use from_signals if entry logic is handled
        in generate_signals. If complex sweep confirmation is needed,
        use from_order_func.
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
