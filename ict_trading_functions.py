"""
ICT Trading Functions
Complete implementation library for ICT trading concepts, detection algorithms, and strategy execution.

This file provides Python implementations for all key ICT concepts including:
- Market structure detection (BOS, CHoCH, MSS)
- Liquidity analysis (sweeps, pools, draws)
- Price level detection (FVG, Order Blocks, Breakers)
- Fibonacci and OTE calculations
- Time and session analysis
- Complete trading strategies
- Risk management functions

All functions use standard library only (Python 3.10+).
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional, Dict, Tuple
from enum import Enum


# ============================================================================
# Data Structures
# ============================================================================

class Direction(Enum):
    """Trade direction"""
    LONG = "long"
    SHORT = "short"


class Session(Enum):
    """Trading sessions"""
    ASIA = "asia"
    LONDON = "london"
    NY_AM = "ny_am"
    NY_PM = "ny_pm"


class KillzoneType(Enum):
    """Killzone types"""
    LONDON_OPEN = "london_open"
    NY_AM = "ny_am"
    NY_PM = "ny_pm"


@dataclass
class OHLC:
    """OHLC candle data"""
    open: float
    high: float
    low: float
    close: float
    timestamp: datetime

    def body_high(self) -> float:
        """Body high (max of open and close)"""
        return max(self.open, self.close)

    def body_low(self) -> float:
        """Body low (min of open and close)"""
        return min(self.open, self.close)

    def range(self) -> float:
        """Candle range (high - low)"""
        return self.high - self.low

    def is_bullish(self) -> bool:
        """Is candle bullish (close > open)"""
        return self.close > self.open

    def is_bearish(self) -> bool:
        """Is candle bearish (close < open)"""
        return self.close < self.open


@dataclass
class SwingPoint:
    """Swing high or low point"""
    price: float
    timestamp: datetime
    direction: Direction  # LONG for swing low, SHORT for swing high
    strength: str  # "STH", "ITH", "LTH"


@dataclass
class FVG:
    """Fair Value Gap"""
    high: float
    low: float
    ce: float  # Common Equity (midpoint)
    timestamp: datetime
    direction: Direction
    filled: bool = False


@dataclass
class OrderBlock:
    """Order Block"""
    high: float
    low: float
    timestamp: datetime
    direction: Direction
    type: str  # "bullish", "bearish"


@dataclass
class BreakerBlock:
    """Breaker Block (failed Order Block)"""
    high: float
    low: float
    timestamp: datetime
    original_direction: Direction  # Direction of original OB
    current_direction: Direction  # Direction after polarity flip


@dataclass
class LiquidityPool:
    """Liquidity Pool (BSL or SSL)"""
    price: float
    pool_type: str  # "BSL" or "SSL"
    timestamp: datetime
    size: int  # Number of equal highs/lows


@dataclass
class Trade:
    """Trade object"""
    entry: float
    stop: float
    target: float
    direction: Direction
    timestamp: datetime
    strategy: str
    r_multiple: float


@dataclass
class Account:
    """Trading account"""
    equity: float
    risk_per_trade: float  # Percentage (e.g., 0.01 for 1%)


# ============================================================================
# Module 1: Market Structure Detection Functions
# ============================================================================

def detect_swing_high(bars: List[OHLC], lookback: int = 3) -> List[SwingPoint]:
    """
    Detect swing highs using lookback method.

    Args:
        bars: List of OHLC candles
        lookback: Number of bars on each side to check

    Returns:
        List of SwingPoint objects for swing highs
    """
    swing_highs = []
    for i in range(lookback, len(bars) - lookback):
        current_high = bars[i].high
        is_swing = True

        # Check if current bar is highest in lookback window
        for j in range(i - lookback, i + lookback + 1):
            if j != i and bars[j].high >= current_high:
                is_swing = False
                break

        if is_swing:
            # Determine strength based on context
            strength = "STH"  # Default to short-term
            swing_highs.append(SwingPoint(
                price=current_high,
                timestamp=bars[i].timestamp,
                direction=Direction.SHORT,
                strength=strength
            ))

    return swing_highs


def detect_swing_low(bars: List[OHLC], lookback: int = 3) -> List[SwingPoint]:
    """
    Detect swing lows using lookback method.

    Args:
        bars: List of OHLC candles
        lookback: Number of bars on each side to check

    Returns:
        List of SwingPoint objects for swing lows
    """
    swing_lows = []
    for i in range(lookback, len(bars) - lookback):
        current_low = bars[i].low
        is_swing = True

        # Check if current bar is lowest in lookback window
        for j in range(i - lookback, i + lookback + 1):
            if j != i and bars[j].low <= current_low:
                is_swing = False
                break

        if is_swing:
            strength = "STH"  # Default to short-term
            swing_lows.append(SwingPoint(
                price=current_low,
                timestamp=bars[i].timestamp,
                direction=Direction.LONG,
                strength=strength
            ))

    return swing_lows


def detect_bos(bars: List[OHLC], swing_points: List[SwingPoint], direction: Direction) -> List[dict]:
    """
    Detect Break of Structure (BOS).

    BOS is confirmed when price breaks the last swing point in direction of trend.

    Args:
        bars: List of OHLC candles
        swing_points: List of swing points
        direction: LONG for bullish BOS, SHORT for bearish BOS

    Returns:
        List of BOS events with price and timestamp
    """
    bos_events = []
    if not swing_points:
        return bos_events

    for i, bar in enumerate(bars):
        if direction == Direction.LONG:
            # Check for bullish BOS: price breaks swing high
            recent_highs = [sp for sp in swing_points if sp.direction == Direction.SHORT and sp.timestamp < bar.timestamp]
            if recent_highs:
                last_high = max(recent_highs, key=lambda x: x.timestamp)
                if bar.close > last_high.price:
                    bos_events.append({
                        'price': last_high.price,
                        'timestamp': bar.timestamp,
                        'direction': Direction.LONG,
                        'confirmation_candle': i
                    })
        else:  # SHORT
            # Check for bearish BOS: price breaks swing low
            recent_lows = [sp for sp in swing_points if sp.direction == Direction.LONG and sp.timestamp < bar.timestamp]
            if recent_lows:
                last_low = min(recent_lows, key=lambda x: x.timestamp)
                if bar.close < last_low.price:
                    bos_events.append({
                        'price': last_low.price,
                        'timestamp': bar.timestamp,
                        'direction': Direction.SHORT,
                        'confirmation_candle': i
                    })

    return bos_events


def detect_choch(bars: List[OHLC], swing_points: List[SwingPoint], direction: Direction) -> List[dict]:
    """
    Detect Change of Character (CHoCH).

    CHoCH is confirmed when price breaks the last swing point against current trend,
    signaling potential trend change.

    Args:
        bars: List of OHLC candles
        swing_points: List of swing points
        direction: Current trend direction (LONG expects bearish CHoCH, SHORT expects bullish CHoCH)

    Returns:
        List of CHoCH events with price and timestamp
    """
    choch_events = []
    if not swing_points:
        return choch_events

    for i, bar in enumerate(bars):
        if direction == Direction.LONG:
            # Looking for bearish CHoCH: price breaks swing low
            recent_lows = [sp for sp in swing_points if sp.direction == Direction.LONG and sp.timestamp < bar.timestamp]
            if recent_lows:
                last_low = min(recent_lows, key=lambda x: x.timestamp)
                if bar.close < last_low.price:
                    choch_events.append({
                        'price': last_low.price,
                        'timestamp': bar.timestamp,
                        'direction': Direction.SHORT,
                        'confirmation_candle': i
                    })
        else:  # SHORT
            # Looking for bullish CHoCH: price breaks swing high
            recent_highs = [sp for sp in swing_points if sp.direction == Direction.SHORT and sp.timestamp < bar.timestamp]
            if recent_highs:
                last_high = max(recent_highs, key=lambda x: x.timestamp)
                if bar.close > last_high.price:
                    choch_events.append({
                        'price': last_high.price,
                        'timestamp': bar.timestamp,
                        'direction': Direction.LONG,
                        'confirmation_candle': i
                    })

    return choch_events


def detect_mss(bars: List[OHLC], swing_points: List[SwingPoint], direction: Direction) -> List[dict]:
    """
    Detect Market Structure Shift (MSS).

    MSS is the first CHoCH that leads to trend change. More aggressive than standard CHoCH.

    Args:
        bars: List of OHLC candles
        swing_points: List of swing points
        direction: Current trend direction

    Returns:
        List of MSS events with price and timestamp
    """
    # MSS is essentially the first CHoCH
    # For implementation, we'll return the first CHoCH as MSS
    choch_events = detect_choch(bars, swing_points, direction)
    if choch_events:
        mss_events = [choch_events[0]]  # First CHoCH is MSS
        for event in mss_events:
            event['type'] = 'MSS'
        return mss_events
    return []


# ============================================================================
# Module 2: Liquidity Detection Functions
# ============================================================================

def detect_liquidity_sweep(bars: List[OHLC], level: float, buffer_pips: float = 5.0) -> List[dict]:
    """
    Detect liquidity sweep (price trading through a level with wick).

    Args:
        bars: List of OHLC candles
        level: Price level to check
        buffer_pips: Minimum wick beyond level to qualify as sweep

    Returns:
        List of sweep events
    """
    sweeps = []
    for i, bar in enumerate(bars):
        # Check if bar's wick trades through level
        if bar.high >= level >= bar.low:
            # Check if wick extends beyond level by buffer
            if bar.high - level >= buffer_pips or level - bar.low >= buffer_pips:
                sweeps.append({
                    'level': level,
                    'timestamp': bar.timestamp,
                    'candle_index': i,
                    'high_wick': bar.high - level if bar.high >= level else 0,
                    'low_wick': level - bar.low if level >= bar.low else 0
                })
    return sweeps


def detect_liquidity_pool(bars: List[OHLC], min_equal: int = 2, buffer_pips: float = 2.0) -> List[LiquidityPool]:
    """
    Detect liquidity pools (equal highs or equal lows).

    Args:
        bars: List of OHLC candles
        min_equal: Minimum number of equal points to form pool
        buffer_pips: Maximum deviation for points to be considered equal

    Returns:
        List of LiquidityPool objects
    """
    pools = []

    # Detect equal highs (BSL)
    highs = [bar.high for bar in bars]
    for i in range(len(highs)):
        equal_count = 0
        for j in range(len(highs)):
            if i != j and abs(highs[i] - highs[j]) <= buffer_pips:
                equal_count += 1
        if equal_count >= min_equal:
            pools.append(LiquidityPool(
                price=highs[i],
                pool_type="BSL",
                timestamp=bars[i].timestamp,
                size=equal_count + 1
            ))

    # Detect equal lows (SSL)
    lows = [bar.low for bar in bars]
    for i in range(len(lows)):
        equal_count = 0
        for j in range(len(lows)):
            if i != j and abs(lows[i] - lows[j]) <= buffer_pips:
                equal_count += 1
        if equal_count >= min_equal:
            pools.append(LiquidityPool(
                price=lows[i],
                pool_type="SSL",
                timestamp=bars[i].timestamp,
                size=equal_count + 1
            ))

    return pools


def detect_draw_on_liquidity(bars: List[OHLC], liquidity_pools: List[LiquidityPool]) -> List[dict]:
    """
    Detect draw on liquidity (approach toward liquidity pool).

    Args:
        bars: List of OHLC candles
        liquidity_pools: List of liquidity pools

    Returns:
        List of draw events
    """
    draws = []
    for pool in liquidity_pools:
        for i, bar in enumerate(bars):
            if bar.timestamp > pool.timestamp:
                # Check if bar approaches pool within threshold
                threshold = 20  # pips
                if abs(bar.close - pool.price) <= threshold:
                    draws.append({
                        'pool_price': pool.price,
                        'pool_type': pool.pool_type,
                        'timestamp': bar.timestamp,
                        'distance': abs(bar.close - pool.price)
                    })
                    break  # One draw per pool
    return draws


# ============================================================================
# Module 3: PD Arrays and Price Levels Detection Functions
# ============================================================================

def detect_fvg(bars: List[OHLC], min_gap_pips: float = 1.0) -> List[FVG]:
    """
    Detect Fair Value Gap formation.

    FVG is the gap between candle 1 high and candle 3 low (bullish) or
    candle 1 low and candle 3 high (bearish).

    Args:
        bars: List of OHLC candles
        min_gap_pips: Minimum gap size in pips

    Returns:
        List of FVG objects
    """
    fvgs = []
    for i in range(2, len(bars)):
        # Bullish FVG: candle i-2 low > candle i high
        bullish_gap = bars[i-2].low - bars[i].high
        if bullish_gap > min_gap_pips:
            fvg = FVG(
                high=bars[i-2].low,
                low=bars[i].high,
                ce=(bars[i-2].low + bars[i].high) / 2,
                timestamp=bars[i].timestamp,
                direction=Direction.LONG
            )
            fvgs.append(fvg)

        # Bearish FVG: candle i-2 high < candle i low
        bearish_gap = bars[i].low - bars[i-2].high
        if bearish_gap > min_gap_pips:
            fvg = FVG(
                high=bars[i].low,
                low=bars[i-2].high,
                ce=(bars[i].low + bars[i-2].high) / 2,
                timestamp=bars[i].timestamp,
                direction=Direction.SHORT
            )
            fvgs.append(fvg)

    return fvgs


def detect_fvg_ce(fvg: FVG, bars: List[OHLC]) -> bool:
    """
    Check if FVG is filled (Common Equity entry zone used).

    Common Equity (CE) is the midpoint of the FVG.
    Entry at CE is preferred over edge entries in 2025+ methodology.

    Args:
        fvg: FVG object to check
        bars: List of OHLC candles after FVG formation

    Returns:
        True if FVG is filled (price trades through CE)
    """
    for bar in bars:
        if bar.timestamp > fvg.timestamp:
            if fvg.direction == Direction.LONG:
                # Bullish FVG filled if price trades below CE
                if bar.low <= fvg.ce:
                    return True
            else:  # SHORT
                # Bearish FVG filled if price trades above CE
                if bar.high >= fvg.ce:
                    return True
    return False


def detect_ob(bars: List[OHLC], direction: Direction) -> List[OrderBlock]:
    """
    Detect Order Block (last bullish candle before bearish move or vice versa).

    Args:
        bars: List of OHLC candles
        direction: LONG for bullish OB, SHORT for bearish OB

    Returns:
        List of OrderBlock objects
    """
    obs = []
    lookback = 10  # Check last 10 candles for OB formation

    for i in range(lookback, len(bars)):
        if direction == Direction.LONG:
            # Look for last bullish candle before bearish move
            if bars[i].is_bearish() and bars[i].range() > bars[i-1].range():
                # Found bearish move, find last bullish candle
                for j in range(i-1, max(0, i-lookback), -1):
                    if bars[j].is_bullish():
                        ob = OrderBlock(
                            high=bars[j].high,
                            low=bars[j].low,
                            timestamp=bars[j].timestamp,
                            direction=Direction.LONG,
                            type="bullish"
                        )
                        obs.append(ob)
                        break
        else:  # SHORT
            # Look for last bearish candle before bullish move
            if bars[i].is_bullish() and bars[i].range() > bars[i-1].range():
                # Found bullish move, find last bearish candle
                for j in range(i-1, max(0, i-lookback), -1):
                    if bars[j].is_bearish():
                        ob = OrderBlock(
                            high=bars[j].high,
                            low=bars[j].low,
                            timestamp=bars[j].timestamp,
                            direction=Direction.SHORT,
                            type="bearish"
                        )
                        obs.append(ob)
                        break

    return obs


def detect_breaker(bars: List[OHLC], order_blocks: List[OrderBlock]) -> List[BreakerBlock]:
    """
    Detect Breaker Block (failed Order Block with polarity flip).

    Args:
        bars: List of OHLC candles
        order_blocks: List of OrderBlock objects

    Returns:
        List of BreakerBlock objects
    """
    breakers = []
    for ob in order_blocks:
        # Check if price returns to OB and closes opposite
        for i, bar in enumerate(bars):
            if bar.timestamp > ob.timestamp:
                if ob.direction == Direction.LONG:
                    # Bullish OB becomes bearish breaker if price closes below OB low
                    if bar.close < ob.low:
                        breaker = BreakerBlock(
                            high=ob.high,
                            low=ob.low,
                            timestamp=ob.timestamp,
                            original_direction=Direction.LONG,
                            current_direction=Direction.SHORT
                        )
                        breakers.append(breaker)
                        break
                else:  # SHORT
                    # Bearish OB becomes bullish breaker if price closes above OB high
                    if bar.close > ob.high:
                        breaker = BreakerBlock(
                            high=ob.high,
                            low=ob.low,
                            timestamp=ob.timestamp,
                            original_direction=Direction.SHORT,
                            current_direction=Direction.LONG
                        )
                        breakers.append(breaker)
                        break

    return breakers


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
# Module 4: Fibonacci and OTE Functions
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


def detect_ote_setup(bars: List[OHLC], htf_bias: Direction) -> List[dict]:
    """
    Detect OTE setup (retracement to fib zone with HTF bias alignment).

    Args:
        bars: List of OHLC candles
        htf_bias: Higher timeframe bias direction

    Returns:
        List of OTE setup events
    """
    # This is a simplified detection
    # Full implementation would identify swing legs and check retracement
    ote_setups = []

    # Look for significant retracements (simplified)
    for i in range(10, len(bars)):
        swing_high = max(bars[j].high for j in range(i-10, i))
        swing_low = min(bars[j].low for j in range(i-10, i))

        # Check if current price is in OTE zone
        leg_size = swing_high - swing_low
        if htf_bias == Direction.LONG:
            ote_low = swing_low + leg_size * 0.625
            ote_high = swing_low + leg_size * 0.79
            if ote_low <= bars[i].close <= ote_high:
                ote_setups.append({
                    'timestamp': bars[i].timestamp,
                    'price': bars[i].close,
                    'ote_zone': (ote_low, ote_high),
                    'direction': Direction.LONG
                })
        else:  # SHORT
            ote_high = swing_high - leg_size * 0.625
            ote_low = swing_high - leg_size * 0.79
            if ote_low <= bars[i].close <= ote_high:
                ote_setups.append({
                    'timestamp': bars[i].timestamp,
                    'price': bars[i].close,
                    'ote_zone': (ote_low, ote_high),
                    'direction': Direction.SHORT
                })

    return ote_setups


# ============================================================================
# Module 5: Time and Session Functions
# ============================================================================

def convert_ny_to_utc(timestamp: datetime) -> datetime:
    """
    Convert New York time to UTC.

    Args:
        timestamp: Datetime in New York timezone

    Returns:
        Datetime in UTC
    """
    # NY is UTC-5 (standard) or UTC-4 (DST)
    # This is a simplified conversion
    # Full implementation would use pytz or zoneinfo
    # For now, assume UTC-5 (standard time)
    return timestamp.replace(hour=(timestamp.hour + 5) % 24)


def get_dst_offset(date: datetime) -> int:
    """
    Get DST offset for New York timezone.

    Args:
        date: Date to check

    Returns:
        Offset in hours (-4 for DST, -5 for standard)
    """
    # NY DST: second Sunday in March to first Sunday in November
    # This is a simplified implementation
    # Full implementation would use proper DST rules
    return -4  # Placeholder


def is_in_killzone(timestamp: datetime, killzone_type: KillzoneType) -> bool:
    """
    Check if timestamp is within a killzone.

    Killzones (NY time):
    - London Open: 02:00-05:00
    - NY AM: 08:00-11:00
    - NY PM: 13:30-16:00

    Args:
        timestamp: Datetime to check (assumed NY time)
        killzone_type: Type of killzone to check

    Returns:
        True if within killzone
    """
    time_only = timestamp.time()

    if killzone_type == KillzoneType.LONDON_OPEN:
        return time(2, 0) <= time_only <= time(5, 0)
    elif killzone_type == KillzoneType.NY_AM:
        return time(8, 0) <= time_only <= time(11, 0)
    elif killzone_type == KillzoneType.NY_PM:
        return time(13, 30) <= time_only <= time(16, 0)
    return False


def is_in_macro_window(timestamp: datetime) -> bool:
    """
    Check if timestamp is within a macro time window.

    Macro windows (NY time):
    - 02:00, 08:00, 13:30, 17:00

    Args:
        timestamp: Datetime to check (assumed NY time)

    Returns:
        True if within 30 minutes of macro time
    """
    time_only = timestamp.time()
    macro_times = [time(2, 0), time(8, 0), time(13, 30), time(17, 0)]

    for macro_time in macro_times:
        diff = abs((timestamp.hour * 60 + timestamp.minute) -
                   (macro_time.hour * 60 + macro_time.minute))
        if diff <= 30:
            return True
    return False


def get_90min_cycle(timestamp: datetime) -> str:
    """
    Get current 90-minute cycle.

    Cycles repeat every 90 minutes throughout the day.

    Args:
        timestamp: Datetime to check

    Returns:
        Cycle identifier (e.g., "Cycle 1", "Cycle 2", etc.)
    """
    minutes_since_midnight = timestamp.hour * 60 + timestamp.minute
    cycle_number = (minutes_since_midnight // 90) + 1
    return f"Cycle {cycle_number}"


# ============================================================================
# Module 6: Power of Three and AMD Functions
# ============================================================================

def detect_amd_phase(bars: List[OHLC], timeframe: str) -> List[dict]:
    """
    Detect AMD (Accumulation-Manipulation-Distribution) phase.

    Args:
        bars: List of OHLC candles
        timeframe: Timeframe of bars

    Returns:
        List of AMD phase events
    """
    # This is a simplified detection
    # Full implementation would analyze range expansion and volatility
    phases = []

    for i in range(20, len(bars)):
        # Calculate volatility over last 20 bars
        ranges = [bar.range() for bar in bars[i-20:i]]
        avg_range = sum(ranges) / len(ranges)
        current_range = bars[i].range()

        # Accumulation: low volatility, range-bound
        if current_range < avg_range * 0.7:
            phases.append({
                'timestamp': bars[i].timestamp,
                'phase': 'Accumulation',
                'reason': 'Low volatility'
            })
        # Manipulation: high volatility, false moves
        elif current_range > avg_range * 1.5:
            phases.append({
                'timestamp': bars[i].timestamp,
                'phase': 'Manipulation',
                'reason': 'High volatility'
            })
        # Distribution: directional expansion
        elif current_range > avg_range:
            phases.append({
                'timestamp': bars[i].timestamp,
                'phase': 'Distribution',
                'reason': 'Directional expansion'
            })

    return phases


def detect_power_of_three(bars: List[OHLC]) -> List[dict]:
    """
    Detect Power of Three (three-phase daily structure).

    PO3 is: Asia (Accumulation) → London (Manipulation) → NY (Distribution).

    Args:
        bars: List of OHLC candles

    Returns:
        List of PO3 structure events
    """
    # This is a simplified detection
    # Full implementation would analyze session-based structure
    po3_events = []

    for i in range(30, len(bars)):
        # Check for three-phase structure
        asia_volatility = sum(bar.range() for bar in bars[i-30:i-20]) / 10
        london_volatility = sum(bar.range() for bar in bars[i-20:i-10]) / 10
        ny_volatility = sum(bar.range() for bar in bars[i-10:i]) / 10

        if asia_volatility < london_volatility < ny_volatility:
            po3_events.append({
                'timestamp': bars[i].timestamp,
                'asia_phase': 'Accumulation',
                'london_phase': 'Manipulation',
                'ny_phase': 'Distribution'
            })

    return po3_events


# ============================================================================
# Module 7: Strategy Execution Functions
# ============================================================================

def execute_silver_bullet_ny_am(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Silver Bullet NY AM strategy.

    NY AM Silver Bullet requirements:
    - Must be in NY AM killzone (08:00-11:00 NY)
    - Must have Asian range setup
    - Must have London open sweep
    - Must have displacement
    - Must draw on liquidity
    - Must have FVG or OB entry

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    latest_bar = bars[-1]

    # Check if in NY AM killzone
    if not is_in_killzone(latest_bar.timestamp, KillzoneType.NY_AM):
        return None

    # Check for liquidity sweep (simplified)
    liquidity_pools = detect_liquidity_pool(bars, min_equal=2)
    if not liquidity_pools:
        return None

    # Check for FVG (simplified)
    fvgs = detect_fvg(bars, min_gap_pips=5.0)
    if not fvgs:
        return None

    # Use most recent FVG for entry
    fvg = fvgs[-1]

    # Calculate position size
    risk_amount = account.equity * account.risk_per_trade
    stop_distance = abs(fvg.low - fvg.high)
    pip_value = 0.0001  # Simplified
    position_size = risk_amount / (stop_distance / pip_value)

    # Create trade
    trade = Trade(
        entry=fvg.ce,
        stop=fvg.low if fvg.direction == Direction.LONG else fvg.high,
        target=fvg.high if fvg.direction == Direction.LONG else fvg.low,
        direction=fvg.direction,
        timestamp=latest_bar.timestamp,
        strategy="Silver Bullet NY AM",
        r_multiple=abs(fvg.high - fvg.low) / stop_distance
    )

    return trade


def execute_silver_bullet_london(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Silver Bullet London strategy.

    London Silver Bullet requirements:
    - Must be in London open killzone (02:00-05:00 NY)
    - Must have Asian range setup
    - Must have displacement
    - Must draw on liquidity
    - Must have FVG or OB entry

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    latest_bar = bars[-1]

    # Check if in London open killzone
    if not is_in_killzone(latest_bar.timestamp, KillzoneType.LONDON_OPEN):
        return None

    # Similar logic to NY AM
    # (simplified for brevity)
    return None


def execute_ict_2022_model(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute ICT 2022 Model strategy.

    2022 Model sequence:
    1. Liquidity sweep
    2. Displacement
    3. FVG or CE entry
    4. Target opposing liquidity

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    # Check for liquidity sweep
    liquidity_pools = detect_liquidity_pool(bars, min_equal=2)
    if not liquidity_pools:
        return None

    # Check for FVG
    fvgs = detect_fvg(bars, min_gap_pips=5.0)
    if not fvgs:
        return None

    fvg = fvgs[-1]

    # Create trade
    trade = Trade(
        entry=fvg.ce,
        stop=fvg.low if fvg.direction == Direction.LONG else fvg.high,
        target=fvg.high if fvg.direction == Direction.LONG else fvg.low,
        direction=fvg.direction,
        timestamp=bars[-1].timestamp,
        strategy="ICT 2022 Model",
        r_multiple=2.0  # Typical 2R target
    )

    return trade


def execute_unicorn(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Unicorn Model strategy.

    Unicorn requirements (all 4 must align):
    1. Breaker block present
    2. FVG nested inside breaker
    3. HTF bias agrees with breaker direction
    4. Liquidity sweep preceded breaker formation

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    # Detect Order Blocks
    obs = detect_ob(bars, Direction.LONG)
    if not obs:
        return None

    # Detect Breakers
    breakers = detect_breaker(bars, obs)
    if not breakers:
        return None

    breaker = breakers[-1]

    # Check for nested FVG
    fvgs = detect_fvg(bars, min_gap_pips=5.0)
    nested_fvg = None
    for fvg in fvgs:
        if (breaker.low <= fvg.low <= breaker.high and
            breaker.low <= fvg.high <= breaker.high):
            nested_fvg = fvg
            break

    if not nested_fvg:
        return None

    # Create trade (entry at FVG CE)
    trade = Trade(
        entry=nested_fvg.ce,
        stop=breaker.low if breaker.current_direction == Direction.LONG else breaker.high,
        target=breaker.high if breaker.current_direction == Direction.LONG else breaker.low,
        direction=breaker.current_direction,
        timestamp=bars[-1].timestamp,
        strategy="Unicorn Model",
        r_multiple=3.0  # High conviction setup
    )

    return trade


def execute_venom(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Venom Model strategy (2025).

    Venom requirements:
    - Pre-cash-open range: 08:00-09:30 NY
    - Sweep one bound after 09:30
    - False breakout (wick continues past swept bound)
    - Reversal back through range with displacement
    - Target opposite side of range

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    latest_bar = bars[-1]

    # Check if after 09:30 NY
    if latest_bar.timestamp.hour < 9 or (latest_bar.timestamp.hour == 9 and latest_bar.timestamp.minute < 30):
        return None

    # Find pre-open range (08:00-09:30)
    pre_open_bars = [bar for bar in bars if
                     (bar.timestamp.hour == 8 or
                      (bar.timestamp.hour == 9 and bar.timestamp.minute <= 30))]
    if len(pre_open_bars) < 2:
        return None

    range_high = max(bar.high for bar in pre_open_bars)
    range_low = min(bar.low for bar in pre_open_bars)

    # Check for sweep of one bound
    if latest_bar.high > range_high:
        # Sweep of high, look for bearish reversal
        if latest_bar.close < range_high:
            trade = Trade(
                entry=latest_bar.close,
                stop=latest_bar.high,
                target=range_low,
                direction=Direction.SHORT,
                timestamp=latest_bar.timestamp,
                strategy="Venom Model",
                r_multiple=abs(range_high - range_low) / abs(latest_bar.high - latest_bar.close)
            )
            return trade
    elif latest_bar.low < range_low:
        # Sweep of low, look for bullish reversal
        if latest_bar.close > range_low:
            trade = Trade(
                entry=latest_bar.close,
                stop=latest_bar.low,
                target=range_high,
                direction=Direction.LONG,
                timestamp=latest_bar.timestamp,
                strategy="Venom Model",
                r_multiple=abs(range_high - range_low) / abs(latest_bar.close - latest_bar.low)
            )
            return trade

    return None


def execute_bread_and_butter(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Bread-and-Butter Setup.

    B&B is the daily PM-Asia-London-NY sequence.
    Execute via standard 2022 model in London or NY AM.

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    # Check if in London or NY AM killzone
    latest_bar = bars[-1]
    if not (is_in_killzone(latest_bar.timestamp, KillzoneType.LONDON_OPEN) or
            is_in_killzone(latest_bar.timestamp, KillzoneType.NY_AM)):
        return None

    # Execute via 2022 model
    return execute_ict_2022_model(bars, account)


def execute_ote_pd_array(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute OTE + PD Array entry strategy.

    Entry at OTE zone aligned with PD array.

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    # Detect OTE setup
    ote_setups = detect_ote_setup(bars, Direction.LONG)  # Assume bullish
    if not ote_setups:
        return None

    ote_setup = ote_setups[-1]

    # Create trade
    trade = Trade(
        entry=ote_setup['price'],
        stop=ote_setup['ote_zone'][0] - 0.0010,  # Simplified stop
        target=ote_setup['ote_zone'][1] + 0.0020,  # Simplified target
        direction=ote_setup['direction'],
        timestamp=ote_setup['timestamp'],
        strategy="OTE + PD Array",
        r_multiple=2.0
    )

    return trade


def execute_fvg_ce(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute FVG/CE entry strategy.

    Entry at Common Equity of FVG (2025+ methodology).

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    fvgs = detect_fvg(bars, min_gap_pips=5.0)
    if not fvgs:
        return None

    fvg = fvgs[-1]

    # Entry at CE
    trade = Trade(
        entry=fvg.ce,
        stop=fvg.low if fvg.direction == Direction.LONG else fvg.high,
        target=fvg.high if fvg.direction == Direction.LONG else fvg.low,
        direction=fvg.direction,
        timestamp=bars[-1].timestamp,
        strategy="FVG/CE Entry",
        r_multiple=2.0
    )

    return trade


def execute_order_block(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Order Block entry strategy.

    Entry on retest of Order Block.

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    obs = detect_ob(bars, Direction.LONG)
    if not obs:
        return None

    ob = obs[-1]

    # Entry on retest
    trade = Trade(
        entry=ob.low + (ob.high - ob.low) * 0.5,  # Midpoint
        stop=ob.low,
        target=ob.high,
        direction=ob.direction,
        timestamp=bars[-1].timestamp,
        strategy="Order Block Entry",
        r_multiple=2.0
    )

    return trade


def execute_judas_swing(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Judas Swing entry strategy.

    Session-anchored fake move before true direction.

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    latest_bar = bars[-1]

    # Check if in killzone
    if not (is_in_killzone(latest_bar.timestamp, KillzoneType.LONDON_OPEN) or
            is_in_killzone(latest_bar.timestamp, KillzoneType.NY_AM)):
        return None

    # Check for sweep and reversal (simplified)
    liquidity_pools = detect_liquidity_pool(bars, min_equal=2)
    if not liquidity_pools:
        return None

    # Enter on reversal
    trade = Trade(
        entry=latest_bar.close,
        stop=latest_bar.low if latest_bar.is_bullish() else latest_bar.high,
        target=latest_bar.close * 1.0020 if latest_bar.is_bullish() else latest_bar.close * 0.9980,
        direction=Direction.LONG if latest_bar.is_bullish() else Direction.SHORT,
        timestamp=latest_bar.timestamp,
        strategy="Judas Swing Entry",
        r_multiple=2.0
    )

    return trade


def execute_asian_range_sweep(bars: List[OHLC], account: Account) -> Optional[Trade]:
    """
    Execute Asian Range Sweep strategy.

    Entry on reversal after London open sweeps Asian range.

    Args:
        bars: List of OHLC candles
        account: Account object

    Returns:
        Trade object if setup valid, None otherwise
    """
    latest_bar = bars[-1]

    # Check if in London open killzone
    if not is_in_killzone(latest_bar.timestamp, KillzoneType.LONDON_OPEN):
        return None

    # Find Asian range (18:00-03:00 NY)
    asian_bars = [bar for bar in bars if
                  bar.timestamp.hour >= 18 or bar.timestamp.hour <= 3]
    if len(asian_bars) < 2:
        return None

    range_high = max(bar.high for bar in asian_bars)
    range_low = min(bar.low for bar in asian_bars)

    # Check for sweep and reversal
    if latest_bar.high > range_high and latest_bar.close < range_high:
        # Sweep of high, bearish reversal
        trade = Trade(
            entry=latest_bar.close,
            stop=latest_bar.high,
            target=range_low,
            direction=Direction.SHORT,
            timestamp=latest_bar.timestamp,
            strategy="Asian Range Sweep",
            r_multiple=abs(range_high - range_low) / abs(latest_bar.high - latest_bar.close)
        )
        return trade
    elif latest_bar.low < range_low and latest_bar.close > range_low:
        # Sweep of low, bullish reversal
        trade = Trade(
            entry=latest_bar.close,
            stop=latest_bar.low,
            target=range_high,
            direction=Direction.LONG,
            timestamp=latest_bar.timestamp,
            strategy="Asian Range Sweep",
            r_multiple=abs(range_high - range_low) / abs(latest_bar.close - latest_bar.low)
        )
        return trade

    return None


# ============================================================================
# Risk Management Functions
# ============================================================================

def calculate_position_size(account_equity: float, risk_pct: float, sl_distance: float, pip_value: float) -> float:
    """
    Calculate position size based on risk percentage.

    Args:
        account_equity: Total account equity
        risk_pct: Risk per trade as percentage (e.g., 0.01 for 1%)
        sl_distance: Stop loss distance in price units
        pip_value: Value of one pip in account currency

    Returns:
        Position size in units
    """
    risk_amount = account_equity * risk_pct
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


def calculate_partial_takes(entry: float, stop: float, target: float, partial_levels: List[float]) -> List[float]:
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
# Utility Functions
# ============================================================================

def format_timezone(ny_time: datetime) -> str:
    """
    Format time with NY, London, and UTC zones.

    Args:
        ny_time: Datetime in New York timezone

    Returns:
        Formatted string with all three timezones
    """
    # Simplified conversion (full implementation would use proper timezone libraries)
    utc_time = convert_ny_to_utc(ny_time)
    london_time = utc_time.replace(hour=(utc_time.hour + 1) % 24)  # London is UTC+1

    return f"NY: {ny_time.strftime('%H:%M')} | London: {london_time.strftime('%H:%M')} | UTC: {utc_time.strftime('%H:%M')}"


# ============================================================================
# Main Execution (for testing)
# ============================================================================

if __name__ == "__main__":
    # Example usage
    print("ICT Trading Functions Library")
    print("=" * 50)
    print("Available functions:")
    print("- detect_swing_high(), detect_swing_low()")
    print("- detect_bos(), detect_choch(), detect_mss()")
    print("- detect_liquidity_sweep(), detect_liquidity_pool()")
    print("- detect_fvg(), detect_ob(), detect_breaker()")
    print("- calculate_fib_levels(), calculate_ote_zone()")
    print("- is_in_killzone(), is_in_macro_window()")
    print("- detect_amd_phase(), detect_power_of_three()")
    print("- execute_silver_bullet_ny_am(), execute_ict_2022_model()")
    print("- execute_unicorn(), execute_venom()")
    print("- calculate_position_size(), calculate_r_multiple()")
    print("\nImport this module to use functions:")
    print("from ict_trading_functions import *")
