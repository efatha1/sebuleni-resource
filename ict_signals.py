"""
ICT Signals - Vectorized ICT Detection Primitives

Complete library of vectorized ICT detection primitives for backtesting with vectorbt.
All functions are designed to work with pandas DataFrames and use vectorized operations
rather than row-by-row loops for performance.

Timezone Assumption:
- All DataFrames are assumed to have datetime index in UTC
- Timezone conversion to America/New_York is handled by in_killzone() function
- DST is handled automatically via pytz/zoneinfo

No Volume Constraint:
- All primitives work with OHLC data only (open, high, low, close)
- No volume-based calculations are performed
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, Literal
from enum import Enum
import pytz

# ============================================================================
# Direction Enum
# ============================================================================

class Direction(Enum):
    """Trade direction"""
    LONG = "long"
    SHORT = "short"

# ============================================================================
# Timezone Conversion Functions
# ============================================================================

def convert_to_ny(index: pd.DatetimeIndex, source_tz: str = 'UTC') -> pd.DatetimeIndex:
    """
    Convert datetime index to New York timezone.
    
    Args:
        index: DatetimeIndex (assumed to be in source_tz)
        source_tz: Source timezone (default: 'UTC')
    
    Returns:
        DatetimeIndex in America/New_York timezone
    """
    if index.tz is None:
        index = index.tz_localize(source_tz)
    elif index.tz.zone != source_tz:
        index = index.tz_convert(source_tz)
    
    return index.tz_convert('America/New_York')

# ============================================================================
# Time/Session Functions
# ============================================================================

def in_killzone(index: pd.DatetimeIndex, killzone_name: str) -> pd.Series:
    """
    Check if timestamps are within specified killzone window.
    
    Killzones (NY time):
    - london_open: 02:00-05:00
    - ny_am: 08:00-11:00
    - ny_pm: 13:30-16:00
    - london_close: 10:00-12:00
    
    Args:
        index: DatetimeIndex (assumed UTC, will convert to NY)
        killzone_name: Name of killzone to check
    
    Returns:
        Boolean Series (True if within killzone)
    """
    ny_index = convert_to_ny(index)
    time_only = ny_index.time
    
    killzones = {
        'london_open': (pd.to_datetime('02:00').time(), pd.to_datetime('05:00').time()),
        'ny_am': (pd.to_datetime('08:00').time(), pd.to_datetime('11:00').time()),
        'ny_pm': (pd.to_datetime('13:30').time(), pd.to_datetime('16:00').time()),
        'london_close': (pd.to_datetime('10:00').time(), pd.to_datetime('12:00').time()),
    }
    
    if killzone_name not in killzones:
        raise ValueError(f"Unknown killzone: {killzone_name}")
    
    start_time, end_time = killzones[killzone_name]
    mask = (time_only >= start_time) & (time_only <= end_time)
    
    return pd.Series(mask, index=index)


def is_in_macro_window(index: pd.DatetimeIndex) -> pd.Series:
    """
    Check if timestamps are within 30 minutes of macro times.
    
    Macro times (NY time): 02:00, 08:00, 13:30, 17:00
    
    Args:
        index: DatetimeIndex (assumed UTC, will convert to NY)
    
    Returns:
        Boolean Series (True if within 30 minutes of macro time)
    """
    ny_index = convert_to_ny(index)
    time_only = ny_index.time
    
    macro_times = [
        pd.to_datetime('02:00').time(),
        pd.to_datetime('08:00').time(),
        pd.to_datetime('13:30').time(),
        pd.to_datetime('17:00').time(),
    ]
    
    mask = pd.Series(False, index=index)
    for macro_time in macro_times:
        macro_minutes = macro_time.hour * 60 + macro_time.minute
        current_minutes = time_only.apply(lambda t: t.hour * 60 + t.minute)
        diff = (current_minutes - macro_minutes).abs()
        mask = mask | (diff <= 30)
    
    return mask


def get_90min_cycle(index: pd.DatetimeIndex) -> pd.Series:
    """
    Get current 90-minute cycle identifier.
    
    Args:
        index: DatetimeIndex (assumed UTC, will convert to NY)
    
    Returns:
        Series of cycle identifiers (e.g., "Cycle 1", "Cycle 2", etc.)
    """
    ny_index = convert_to_ny(index)
    minutes_since_midnight = ny_index.hour * 60 + ny_index.minute
    cycle_number = (minutes_since_midnight // 90) + 1
    return pd.Series(f"Cycle {cycle_number}", index=index)

# ============================================================================
# Market Structure Detection Functions
# ============================================================================

def swing_highs(df: pd.DataFrame, lookback: int = 3) -> pd.Series:
    """
    Detect swing highs using rolling window comparison.
    
    Args:
        df: DataFrame with 'high' column
        lookback: Number of bars on each side to check
    
    Returns:
        Boolean Series (True at swing high)
    """
    highs = df['high']
    
    # Create shifted high series for comparison
    shifted_highs = [highs.shift(i) for i in range(-lookback, lookback + 1)]
    
    # Check if current high is highest in lookback window
    is_swing = pd.Series(True, index=df.index)
    for i, shifted in enumerate(shifted_highs):
        if i != lookback:  # Skip the current bar
            is_swing = is_swing & (highs >= shifted)
    
    return is_swing


def swing_lows(df: pd.DataFrame, lookback: int = 3) -> pd.Series:
    """
    Detect swing lows using rolling window comparison.
    
    Args:
        df: DataFrame with 'low' column
        lookback: Number of bars on each side to check
    
    Returns:
        Boolean Series (True at swing low)
    """
    lows = df['low']
    
    # Create shifted low series for comparison
    shifted_lows = [lows.shift(i) for i in range(-lookback, lookback + 1)]
    
    # Check if current low is lowest in lookback window
    is_swing = pd.Series(True, index=df.index)
    for i, shifted in enumerate(shifted_lows):
        if i != lookback:  # Skip the current bar
            is_swing = is_swing & (lows <= shifted)
    
    return is_swing


def bos(df: pd.DataFrame, swings: pd.DataFrame, direction: Direction) -> pd.Series:
    """
    Detect Break of Structure (BOS).
    
    BOS is confirmed when price breaks the last swing point in direction of trend.
    
    Args:
        df: DataFrame with 'close' column
        swings: DataFrame with swing points (must have 'price', 'direction', 'timestamp' columns)
        direction: LONG for bullish BOS, SHORT for bearish BOS
    
    Returns:
        Boolean Series (True at BOS confirmation)
    """
    bos_events = pd.Series(False, index=df.index)
    
    if len(swings) == 0:
        return bos_events
    
    if direction == Direction.LONG:
        # Bullish BOS: price breaks swing high
        recent_highs = swings[swings['direction'] == 'short']
        if len(recent_highs) > 0:
            last_high = recent_highs.iloc[-1]['price']
            last_high_time = recent_highs.iloc[-1]['timestamp']
            bos_events = (df.index > last_high_time) & (df['close'] > last_high)
    else:  # SHORT
        # Bearish BOS: price breaks swing low
        recent_lows = swings[swings['direction'] == 'long']
        if len(recent_lows) > 0:
            last_low = recent_lows.iloc[-1]['price']
            last_low_time = recent_lows.iloc[-1]['timestamp']
            bos_events = (df.index > last_low_time) & (df['close'] < last_low)
    
    return bos_events


def choch(df: pd.DataFrame, swings: pd.DataFrame, direction: Direction) -> pd.Series:
    """
    Detect Change of Character (CHoCH).
    
    CHoCH is confirmed when price breaks the last swing point against current trend.
    
    Args:
        df: DataFrame with 'close' column
        swings: DataFrame with swing points
        direction: Current trend direction (LONG expects bearish CHoCH, SHORT expects bullish CHoCH)
    
    Returns:
        Boolean Series (True at CHoCH confirmation)
    """
    choch_events = pd.Series(False, index=df.index)
    
    if len(swings) == 0:
        return choch_events
    
    if direction == Direction.LONG:
        # Looking for bearish CHoCH: price breaks swing low
        recent_lows = swings[swings['direction'] == 'long']
        if len(recent_lows) > 0:
            last_low = recent_lows.iloc[-1]['price']
            last_low_time = recent_lows.iloc[-1]['timestamp']
            choch_events = (df.index > last_low_time) & (df['close'] < last_low)
    else:  # SHORT
        # Looking for bullish CHoCH: price breaks swing high
        recent_highs = swings[swings['direction'] == 'short']
        if len(recent_highs) > 0:
            last_high = recent_highs.iloc[-1]['price']
            last_high_time = recent_highs.iloc[-1]['timestamp']
            choch_events = (df.index > last_high_time) & (df['close'] > last_high)
    
    return choch_events


def mss(df: pd.DataFrame, swings: pd.DataFrame, direction: Direction) -> pd.Series:
    """
    Detect Market Structure Shift (MSS).
    
    MSS is the first CHoCH that leads to trend change.
    
    Args:
        df: DataFrame with 'close' column
        swings: DataFrame with swing points
        direction: Current trend direction
    
    Returns:
        Boolean Series (True at MSS confirmation)
    """
    # MSS is essentially the first CHoCH
    choch_events = choch(df, swings, direction)
    
    # Take only the first CHoCH as MSS
    if choch_events.any():
        first_choch = choch_events[choch_events].index[0]
        mss_events = pd.Series(False, index=df.index)
        mss_events.loc[first_choch] = True
        return mss_events
    
    return choch_events

# ============================================================================
# Liquidity Detection Functions
# ============================================================================

def liquidity_pools(df: pd.DataFrame, min_equal: int = 2, buffer_pips: float = 2.0) -> pd.DataFrame:
    """
    Detect liquidity pools (equal highs or equal lows).
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        min_equal: Minimum number of equal points to form pool
        buffer_pips: Maximum deviation for points to be considered equal
    
    Returns:
        DataFrame with columns: high, low, pool_type, timestamp
    """
    pools = []
    
    # Detect equal highs (BSL)
    highs = df['high']
    for i in range(len(df)):
        equal_count = 0
        for j in range(len(df)):
            if i != j and abs(highs.iloc[i] - highs.iloc[j]) <= buffer_pips:
                equal_count += 1
        if equal_count >= min_equal:
            pools.append({
                'price': highs.iloc[i],
                'pool_type': 'BSL',
                'timestamp': df.index[i]
            })
    
    # Detect equal lows (SSL)
    lows = df['low']
    for i in range(len(df)):
        equal_count = 0
        for j in range(len(df)):
            if i != j and abs(lows.iloc[i] - lows.iloc[j]) <= buffer_pips:
                equal_count += 1
        if equal_count >= min_equal:
            pools.append({
                'price': lows.iloc[i],
                'pool_type': 'SSL',
                'timestamp': df.index[i]
            })
    
    return pd.DataFrame(pools)


def liquidity_sweep(df: pd.DataFrame, pools: pd.DataFrame, buffer_pips: float = 5.0) -> pd.Series:
    """
    Detect liquidity sweep (price trading through a level with wick).
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        pools: DataFrame of liquidity pools
        buffer_pips: Minimum wick beyond level to qualify as sweep
    
    Returns:
        Boolean Series (True at sweep event)
    """
    sweeps = pd.Series(False, index=df.index)
    
    for _, pool in pools.iterrows():
        level = pool['price']
        pool_type = pool['pool_type']
        pool_time = pool['timestamp']
        
        # Check if bar's wick trades through level after pool formation
        if pool_type == 'BSL':
            # Bullish sweep: high trades through level
            high_wick = df['high'] - level
            sweeps = sweeps | ((df.index > pool_time) & (df['high'] >= level) & (high_wick >= buffer_pips))
        else:  # SSL
            # Bearish sweep: low trades through level
            low_wick = level - df['low']
            sweeps = sweeps | ((df.index > pool_time) & (df['low'] <= level) & (low_wick >= buffer_pips))
    
    return sweeps


def draw_on_liquidity(df: pd.DataFrame, pools: pd.DataFrame, threshold: float = 20) -> pd.Series:
    """
    Detect draw on liquidity (approach toward liquidity pool).
    
    Args:
        df: DataFrame with 'close' column
        pools: DataFrame of liquidity pools
        threshold: Maximum distance to qualify as draw
    
    Returns:
        Boolean Series (True at draw event)
    """
    draws = pd.Series(False, index=df.index)
    
    for _, pool in pools.iterrows():
        level = pool['price']
        pool_time = pool['timestamp']
        
        # Check if bar approaches pool within threshold
        distance = (df['close'] - level).abs()
        draws = draws | ((df.index > pool_time) & (distance <= threshold))
    
    return draws

# ============================================================================
# Price Level Detection Functions
# ============================================================================

def fair_value_gaps(df: pd.DataFrame, min_gap_pips: float = 1.0) -> pd.DataFrame:
    """
    Detect Fair Value Gap formation.
    
    FVG is the gap between candle 1 high and candle 3 low (bullish) or
    candle 1 low and candle 3 high (bearish).
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        min_gap_pips: Minimum gap size in price units
    
    Returns:
        DataFrame with columns: high, low, ce, direction, filled
    """
    fvgs = []
    
    for i in range(2, len(df)):
        # Bullish FVG: candle i-2 low > candle i high
        bullish_gap = df['low'].iloc[i-2] - df['high'].iloc[i]
        if bullish_gap > min_gap_pips:
            fvgs.append({
                'high': df['low'].iloc[i-2],
                'low': df['high'].iloc[i],
                'ce': (df['low'].iloc[i-2] + df['high'].iloc[i]) / 2,
                'direction': 'long',
                'filled': False,
                'timestamp': df.index[i]
            })
        
        # Bearish FVG: candle i-2 high < candle i low
        bearish_gap = df['low'].iloc[i] - df['high'].iloc[i-2]
        if bearish_gap > min_gap_pips:
            fvgs.append({
                'high': df['low'].iloc[i],
                'low': df['high'].iloc[i-2],
                'ce': (df['low'].iloc[i] + df['high'].iloc[i-2]) / 2,
                'direction': 'short',
                'filled': False,
                'timestamp': df.index[i]
            })
    
    return pd.DataFrame(fvgs)


def fvg_ce_entry(df: pd.DataFrame, fvgs: pd.DataFrame, buffer_pips: float = 5.0) -> pd.Series:
    """
    Detect FVG CE entry opportunities.
    
    Args:
        df: DataFrame with 'close' column
        fvgs: DataFrame of FVG zones
        buffer_pips: Buffer around CE for entry
    
    Returns:
        Boolean Series (True at CE entry opportunity)
    """
    entries = pd.Series(False, index=df.index)
    
    for _, fvg in fvgs.iterrows():
        ce = fvg['ce']
        fvg_time = fvg['timestamp']
        direction = fvg['direction']
        
        if direction == 'long':
            # Bullish entry: price retraces to CE
            entries = entries | ((df.index > fvg_time) & 
                                (df['close'] >= ce - buffer_pips) & 
                                (df['close'] <= ce + buffer_pips))
        else:  # short
            # Bearish entry: price retraces to CE
            entries = entries | ((df.index > fvg_time) & 
                                (df['close'] <= ce + buffer_pips) & 
                                (df['close'] >= ce - buffer_pips))
    
    return entries


def order_blocks(df: pd.DataFrame, direction: Direction) -> pd.DataFrame:
    """
    Detect Order Blocks (last bullish candle before bearish move or vice versa).
    
    Args:
        df: DataFrame with 'open', 'high', 'low', 'close' columns
        direction: LONG for bullish OB, SHORT for bearish OB
    
    Returns:
        DataFrame with columns: high, low, timestamp, direction, type
    """
    obs = []
    lookback = 10
    
    for i in range(lookback, len(df)):
        current_bar = df.iloc[i]
        current_range = current_bar['high'] - current_bar['low']
        prev_range = df.iloc[i-1]['high'] - df.iloc[i-1]['low']
        
        if direction == Direction.LONG:
            # Look for last bullish candle before bearish move
            if current_bar['close'] < current_bar['open'] and current_range > prev_range:
                # Found bearish move, find last bullish candle
                for j in range(i-1, max(0, i-lookback), -1):
                    if df.iloc[j]['close'] > df.iloc[j]['open']:
                        obs.append({
                            'high': df.iloc[j]['high'],
                            'low': df.iloc[j]['low'],
                            'timestamp': df.index[j],
                            'direction': 'long',
                            'type': 'bullish'
                        })
                        break
        else:  # SHORT
            # Look for last bearish candle before bullish move
            if current_bar['close'] > current_bar['open'] and current_range > prev_range:
                # Found bullish move, find last bearish candle
                for j in range(i-1, max(0, i-lookback), -1):
                    if df.iloc[j]['close'] < df.iloc[j]['open']:
                        obs.append({
                            'high': df.iloc[j]['high'],
                            'low': df.iloc[j]['low'],
                            'timestamp': df.index[j],
                            'direction': 'short',
                            'type': 'bearish'
                        })
                        break
    
    return pd.DataFrame(obs)


def breaker_blocks(df: pd.DataFrame, order_blocks: pd.DataFrame) -> pd.DataFrame:
    """
    Detect Breaker Blocks (failed Order Blocks with polarity flip).
    
    Args:
        df: DataFrame with 'close' column
        order_blocks: DataFrame of Order Blocks
    
    Returns:
        DataFrame with columns: high, low, original_direction, current_direction
    """
    breakers = []
    
    for _, ob in order_blocks.iterrows():
        ob_high = ob['high']
        ob_low = ob['low']
        ob_time = ob['timestamp']
        original_direction = ob['direction']
        
        # Check if price returns to OB and closes opposite
        if original_direction == 'long':
            # Bullish OB becomes bearish breaker if price closes below OB low
            breaker_condition = (df.index > ob_time) & (df['close'] < ob_low)
            if breaker_condition.any():
                breakers.append({
                    'high': ob_high,
                    'low': ob_low,
                    'original_direction': 'long',
                    'current_direction': 'short'
                })
        else:  # short
            # Bearish OB becomes bullish breaker if price closes above OB high
            breaker_condition = (df.index > ob_time) & (df['close'] > ob_high)
            if breaker_condition.any():
                breakers.append({
                    'high': ob_high,
                    'low': ob_low,
                    'original_direction': 'short',
                    'current_direction': 'long'
                })
    
    return pd.DataFrame(breakers)


def calculate_premium_discount(range_high: float, range_low: float, current_price: float) -> str:
    """
    Classify price as premium, discount, or equilibrium.
    
    Args:
        range_high: High of the dealing range
        range_low: Low of the dealing range
        current_price: Current price
    
    Returns:
        "premium", "discount", or "equilibrium"
    """
    equilibrium = (range_high + range_low) / 2
    threshold = (range_high - range_low) * 0.1  # 10% threshold
    
    if current_price > equilibrium + threshold:
        return "premium"
    elif current_price < equilibrium - threshold:
        return "discount"
    else:
        return "equilibrium"

# ============================================================================
# Fibonacci and OTE Functions
# ============================================================================

def calculate_fib_levels(leg_start: float, leg_end: float, direction: Direction) -> Dict[str, float]:
    """
    Calculate ICT Fibonacci levels from a swing leg.
    
    Args:
        leg_start: Start price of the leg
        leg_end: End price of the leg
        direction: LONG for bullish leg, SHORT for bearish leg
    
    Returns:
        Dictionary of fib level names to prices
    """
    leg_size = abs(leg_end - leg_start)
    
    if direction == Direction.LONG:
        # Bullish leg: levels above leg_end
        base = leg_end
        levels = {
            '0.000': base,
            '0.382': base + leg_size * 0.382,
            '0.500': base + leg_size * 0.500,
            '0.618': base + leg_size * 0.618,
            '0.625': base + leg_size * 0.625,  # ICT 0.625
            '0.705': base + leg_size * 0.705,  # ICT 0.705
            '0.786': base + leg_size * 0.786,
            '0.79': base + leg_size * 0.79,     # ICT 0.79
            '1.000': base + leg_size * 1.000,
        }
    else:  # SHORT
        # Bearish leg: levels below leg_end
        base = leg_end
        levels = {
            '0.000': base,
            '0.382': base - leg_size * 0.382,
            '0.500': base - leg_size * 0.500,
            '0.618': base - leg_size * 0.618,
            '0.625': base - leg_size * 0.625,
            '0.705': base - leg_size * 0.705,
            '0.786': base - leg_size * 0.786,
            '0.79': base - leg_size * 0.79,
            '1.000': base - leg_size * 1.000,
        }
    
    return levels


def calculate_ote_zone(leg_start: float, leg_end: float, direction: Direction) -> Tuple[float, float]:
    """
    Calculate OTE (Optimal Trade Entry) zone.
    
    OTE is the 0.62-0.79 fib zone (ICT uses 0.62/0.705/0.79).
    Entry zone is typically 0.62-0.79 or 0.705-0.79.
    
    Args:
        leg_start: Start price of the leg
        leg_end: End price of the leg
        direction: LONG for bullish leg, SHORT for bearish leg
    
    Returns:
        Tuple of (ote_low, ote_high)
    """
    levels = calculate_fib_levels(leg_start, leg_end, direction)
    
    if direction == Direction.LONG:
        return (levels['0.625'], levels['0.79'])
    else:  # SHORT
        return (levels['0.79'], levels['0.625'])


def ote_zone(df: pd.DataFrame, swing_high: float, swing_low: float) -> pd.DataFrame:
    """
    Calculate OTE zone for each bar based on swing levels.
    
    Args:
        df: DataFrame with 'close' column
        swing_high: High of swing leg
        swing_low: Low of swing leg
    
    Returns:
        DataFrame with columns: ote_high, ote_low, ce
    """
    leg_size = swing_high - swing_low
    
    # Determine direction based on current close relative to swing
    direction = 'long' if df['close'].iloc[-1] > (swing_high + swing_low) / 2 else 'short'
    
    if direction == 'long':
        ote_low = swing_low + leg_size * 0.625
        ote_high = swing_low + leg_size * 0.79
    else:
        ote_high = swing_high - leg_size * 0.625
        ote_low = swing_high - leg_size * 0.79
    
    ce = (ote_low + ote_high) / 2
    
    return pd.DataFrame({
        'ote_high': [ote_high] * len(df),
        'ote_low': [ote_low] * len(df),
        'ce': [ce] * len(df)
    }, index=df.index)

# ============================================================================
# HTF Bias Functions
# ============================================================================

def htf_bias(htf_df: pd.DataFrame, ltf_index: pd.DatetimeIndex) -> pd.Series:
    """
    Calculate HTF bias and reindex onto LTF index via forward-fill.
    
    Args:
        htf_df: Higher timeframe DataFrame with 'close' column
        ltf_index: Lower timeframe index to reindex onto
    
    Returns:
        Series of LONG/SHORT/NEUTRAL, reindexed to LTF via forward-fill
    """
    # Simple bias: close above prev close = LONG, below = SHORT
    htf_df['prev_close'] = htf_df['close'].shift(1)
    htf_df['bias'] = 'NEUTRAL'
    htf_df.loc[htf_df['close'] > htf_df['prev_close'], 'bias'] = 'LONG'
    htf_df.loc[htf_df['close'] < htf_df['prev_close'], 'bias'] = 'SHORT'
    
    # Reindex to LTF and forward-fill
    bias_series = htf_df['bias'].reindex(ltf_index, method='ffill')
    
    return bias_series

# ============================================================================
# Displacement Detection Functions
# ============================================================================

def detect_displacement(df: pd.DataFrame, min_range_pct: float = 1.5) -> pd.Series:
    """
    Detect displacement candles.
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        min_range_pct: Minimum range as percentage of average range
    
    Returns:
        Boolean Series (True at displacement)
    """
    ranges = df['high'] - df['low']
    avg_range = ranges.rolling(20).mean()
    
    displacement = ranges > (avg_range * min_range_pct)
    
    return displacement


def displacement_strength(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate displacement strength metrics.
    
    Args:
        df: DataFrame with 'open', 'high', 'low', 'close' columns
    
    Returns:
        DataFrame with columns: body_ratio, opposing_wick_ratio
    """
    ranges = df['high'] - df['low']
    body_high = df[['open', 'close']].max(axis=1)
    body_low = df[['open', 'close']].min(axis=1)
    body_size = body_high - body_low
    
    # Body ratio: body size / total range
    body_ratio = body_size / ranges
    
    # Opposing wick ratio
    if df['close'] > df['open']:  # Bullish
        opposing_wick = df['high'] - body_high
    else:  # Bearish
        opposing_wick = body_low - df['low']
    
    opposing_wick_ratio = opposing_wick / ranges
    
    return pd.DataFrame({
        'body_ratio': body_ratio,
        'opposing_wick_ratio': opposing_wick_ratio
    }, index=df.index)

# ============================================================================
# Risk Management Functions
# ============================================================================

def calculate_position_size(equity: float, risk_pct: float, sl_distance: float, pip_value: float) -> float:
    """
    Calculate position size based on risk percentage.
    
    Args:
        equity: Total account equity
        risk_pct: Risk per trade as percentage (e.g., 0.01 for 1%)
        sl_distance: Stop loss distance in price units
        pip_value: Value of one pip in account currency
    
    Returns:
        Position size in units
    """
    risk_amount = equity * risk_pct
    position_size = risk_amount / (sl_distance / pip_value)
    return position_size


def calculate_r_multiple(entry: float, stop: float, target: float) -> float:
    """
    Calculate R-multiple (risk/reward ratio).
    
    Args:
        entry: Entry price
        stop: Stop loss price
        target: Take profit price
    
    Returns:
        R-multiple (reward/risk)
    """
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        return 0
    return reward / risk


def calculate_partial_takes(entry: float, stop: float, target: float, partial_levels: list) -> list:
    """
    Calculate partial take-profit levels.
    
    Args:
        entry: Entry price
        stop: Stop loss price
        target: Full target price
        partial_levels: List of R-levels for partials (e.g., [1.0, 2.0, 3.0])
    
    Returns:
        List of partial take prices
    """
    risk = abs(entry - stop)
    partials = []
    for r_level in partial_levels:
        if entry < target:  # Long
            partial = entry + (risk * r_level)
        else:  # Short
            partial = entry - (risk * r_level)
        partials.append(partial)
    return partials

# ============================================================================
# News and Account Filter Stubs
# ============================================================================

def apply_news_filter(df: pd.DataFrame, exclude_dates: Optional[list] = None) -> pd.Series:
    """
    Stub function for news-based no-trade filters.
    
    Args:
        df: DataFrame with datetime index
        exclude_dates: Optional list of dates to exclude (user-supplied)
    
    Returns:
        Boolean mask (True = allowed to trade)
    
    Note: This filter is inactive until exclude_dates is provided.
    Economic calendar not available in parquet data.
    """
    if exclude_dates is None:
        return pd.Series(True, index=df.index)
    
    date_mask = ~df.index.date.isin(exclude_dates)
    return date_mask


def apply_account_filters():
    """
    Stub for account-based filters.
    
    Note: These require Portfolio.from_order_func with manual state tracking.
    Not implemented in vectorized from_signals version.
    Would require mid-run equity tracking which vectorized backtest doesn't support.
    """
    pass

# ============================================================================
# Main Execution (for testing)
# ============================================================================

if __name__ == "__main__":
    print("ICT Signals - Vectorized ICT Detection Primitives")
    print("=" * 60)
    print("Available primitive categories:")
    print("- Market Structure: swing_highs, swing_lows, bos, choch, mss")
    print("- Liquidity: liquidity_pools, liquidity_sweep, draw_on_liquidity")
    print("- Price Levels: fair_value_gaps, fvg_ce_entry, order_blocks, breaker_blocks")
    print("- Fibonacci/OTE: calculate_fib_levels, calculate_ote_zone, ote_zone")
    print("- Time/Session: in_killzone, is_in_macro_window, get_90min_cycle")
    print("- HTF Bias: htf_bias")
    print("- Risk Management: calculate_position_size, calculate_r_multiple, calculate_partial_takes")
    print("- Displacement: detect_displacement, displacement_strength")
    print("\nImport this module to use primitives:")
    print("from ict_signals import *")
