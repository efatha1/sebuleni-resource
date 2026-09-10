# Strategy Adapters

This package provides strategy-specific adapters for the VECTORBT BACKTEST AGENT.

## Purpose

Adapters handle complex strategy requirements that go beyond the standard `from_signals()` constructor:

- **Partial exit strategies** (Silver Bullet, Unicorn): Track and execute multiple take-profit levels
- **Aggressive trailing strategies** (ICT 2024): Implement dynamic stop-loss management
- **Special entry logic** (Venom, Asian Range Sweep, Judas Swing): Handle complex entry confirmation

## Architecture

### BaseAdapter

All adapters inherit from `BaseAdapter` which defines the interface:

```python
class BaseAdapter(ABC):
    @abstractmethod
    def create_portfolio(self, price_data, entries, exits, config, strategy_module) -> vbt.Portfolio:
        pass

    @abstractmethod
    def get_strategy_id(self) -> str:
        pass

    def validate_config(self, config: Any) -> bool:
        pass

    def preprocess_signals(self, price_data, entries, exits, config) -> Tuple[pd.Series, pd.Series]:
        pass
```

### Registered Adapters

| Strategy | Adapter | Special Requirements |
|----------|---------|---------------------|
| Silver Bullet (NY AM) | `SilverBulletNYAMAdapter` | Partial exits (33%/33%/34%), breakeven trailing |
| Silver Bullet (London) | `SilverBulletLondonAdapter` | Partial exits (33%/33%/34%), breakeven trailing |
| Unicorn | `UnicornAdapter` | Partial exits (25%/25%/50%), extended targets (8R+) |
| ICT 2024 Model | `ICT2024Adapter` | Aggressive trailing after 1.5R (move to 0.5R) |
| Venom Model | `VenomAdapter` | Pre-open range detection, false breakout confirmation |
| Asian Range Sweep | `AsianRangeSweepAdapter` | Asian session range detection, sweep confirmation |
| Judas Swing | `JudasSwingAdapter` | Liquidity sweep detection, counter-trend entry |

## Usage

### In BacktestAgent

The agent automatically selects the appropriate adapter based on `strategy_id`:

```python
agent = BacktestAgent("silver_bullet_ny_am", "1.0")
results = agent.run_backtest(strategy_module, config)
```

The agent checks the adapter registry:
```python
if self.strategy_id in self._adapter_registry:
    adapter = self._adapter_registry[self.strategy_id]
    portfolio = adapter.create_portfolio(price_data, entries, exits, config, strategy_module)
else:
    # Use default from_signals for simple strategies
    portfolio = vbt.Portfolio.from_signals(...)
```

### Creating a New Adapter

1. Create a new adapter class inheriting from `BaseAdapter`:

```python
from .base_adapter import BaseAdapter

class MyStrategyAdapter(BaseAdapter):
    def get_strategy_id(self) -> str:
        return "my_strategy"

    def validate_config(self, config: Any) -> bool:
        # Validate required config attributes
        return hasattr(config, 'required_attr')

    def create_portfolio(self, price_data, entries, exits, config, strategy_module):
        # Implement portfolio creation logic
        return portfolio
```

2. Register the adapter in `backtest_agent.py`:

```python
from adapters import MyStrategyAdapter

# In __init__:
self._adapter_registry = {
    # ... existing adapters ...
    'my_strategy': MyStrategyAdapter(),
}
```

3. Export from `adapters/__init__.py`:

```python
from .my_strategy_adapter import MyStrategyAdapter

__all__ = [
    # ... existing exports ...
    'MyStrategyAdapter',
]
```

## Benefits of Adapter Pattern

1. **Separation of Concerns**: Strategy-specific logic is isolated in adapter classes
2. **Extensibility**: New strategies can be added without modifying the core agent
3. **Maintainability**: Each adapter can be tested and modified independently
4. **Clear Interface**: BaseAdapter provides a consistent contract for all adapters
5. **Strategy Override**: Adapters can override preprocessing, validation, and portfolio creation

## State Tracking

For strategies using `from_order_func` (Silver Bullet, Unicorn, ICT 2024), the adapters rely on the module-level state tracker in `backtest_agent.py`:

```python
from backtest_agent import get_order_func_state_tracker

# In order_func:
state_tracker = get_order_func_state_tracker()
state_tracker[idx] = {'entry_price': ..., 'partial_exits': [...]}
```

This allows the agent to extract partial exit information after portfolio execution.

## Future Enhancements

Potential adapter enhancements:
- Add `preprocess_signals()` implementations for complex signal filtering
- Add `postprocess_portfolio()` for post-execution adjustments
- Add strategy-specific MAE/MFE calculation overrides
- Add custom validation logic per strategy
