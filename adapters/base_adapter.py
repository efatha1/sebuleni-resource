"""
Base Adapter for Strategy-Specific Portfolio Creation

Provides the interface that all strategy adapters must implement.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Any, Tuple
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """
    Abstract base class for strategy-specific portfolio adapters.

    Each complex strategy should implement its own adapter to handle
    special requirements like partial exits, trailing stops, or custom
    entry/exit logic.
    """

    @abstractmethod
    def create_portfolio(
        self,
        price_data: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        config: Any,
        strategy_module: Any
    ) -> vbt.Portfolio:
        """
        Create a vectorbt Portfolio using strategy-specific logic.

        Args:
            price_data: OHLC DataFrame
            entries: Entry signal Series
            exits: Exit signal Series
            config: Strategy configuration
            strategy_module: Strategy module with generate_signals and order_func

        Returns:
            vectorbt Portfolio object
        """
        pass

    @abstractmethod
    def get_strategy_id(self) -> str:
        """Return the strategy ID this adapter handles."""
        pass

    def validate_config(self, config: Any) -> bool:
        """
        Validate that the config has required attributes.

        Override in subclass to add specific validation.
        """
        return True

    def preprocess_signals(
        self,
        price_data: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        config: Any
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Optional preprocessing of signals before portfolio creation.

        Override in subclass if signal modification is needed.
        """
        return entries, exits
