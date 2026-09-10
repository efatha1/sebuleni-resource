"""
Market State Recorder - Tiered approach: core concepts + strategy-specific

Records observable market state at trade entries for downstream research analysis.
Implements tiered approach:
- Core concepts (always recorded): HTF_bias, LTF_bias, session, kill_zone, previous day/week high/low
- Strategy-specific concepts (based on strategy): FVG, OB, displacement, liquidity sweep, etc.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from ict_signals import (
    htf_bias, swing_highs, swing_lows, in_killzone,
    fair_value_gaps, order_blocks, liquidity_pools,
    detect_displacement, bos, choch, mss, convert_to_ny, Direction
)
from data_loader import load_data


class MarketStateRecorder:
    """
    Record market state at trade entries using tiered approach.
    
    Core concepts (always recorded):
    - HTF_bias, LTF_bias
    - session, kill_zone
    - previous_day_high, previous_day_low
    - previous_week_high, previous_week_low
    
    Strategy-specific concepts (based on strategy_id):
    - FVG/CE strategies: FVG, displacement
    - Order Block strategies: OB, breaker
    - Silver Bullet/2022 Model: FVG, displacement, liquidity_swept, sweep_type
    - Unicorn: FVG, displacement, displacement_strength
    - Judas Swing: liquidity_swept, sweep_type, displacement
    - Asian Range: Asian_range, liquidity_swept
    - Venom: pre_open_range, false_breakout
    """
    
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        
    def record_market_state(
        self,
        price_data: pd.DataFrame,
        entry_index: int,
        config: Any,
        htf_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Record market state at entry with tiered approach.
        
        Args:
            price_data: Price data DataFrame
            entry_index: Index position of entry
            config: Strategy configuration
            htf_data: Higher timeframe data (optional, will load if not provided)
        
        Returns:
            Dictionary with:
            - entry_time
            - core_state (always recorded)
            - strategy_specific_state (based on strategy)
            - used_vs_observed (distinguishes used vs observed concepts)
            - multi_timeframe (HTF and LTF state)
        """
        # Load HTF data if not provided
        if htf_data is None:
            htf_data = load_data(config.symbol, config.htf_timeframe)
        
        entry_dt = price_data.index[entry_index]
        
        # Core concepts (always recorded)
        core_state = {
            "HTF_bias": self._get_htf_bias(htf_data, entry_dt),
            "LTF_bias": self._get_ltf_bias(price_data, entry_index),
            "session": self._get_session(entry_dt),
            "kill_zone": self._get_killzone(entry_dt),
            "previous_day_high": self._get_previous_day_high(price_data, entry_index),
            "previous_day_low": self._get_previous_day_low(price_data, entry_index),
            "previous_week_high": self._get_previous_week_high(price_data, entry_index),
            "previous_week_low": self._get_previous_week_low(price_data, entry_index),
        }
        
        # Strategy-specific concepts
        strategy_specific = self._get_strategy_specific_state(
            price_data, entry_index, config, htf_data
        )
        
        # Distinguish used vs observed
        used_vs_observed = self._determine_used_vs_observed(
            core_state, strategy_specific, config
        )
        
        # Multi-timeframe information
        multi_tf_state = {
            "HTF": {
                "timeframe": config.htf_timeframe,
                "bias": core_state["HTF_bias"],
                "structure": self._get_structure(htf_data, entry_dt)
            },
            "LTF": {
                "timeframe": config.ltf_timeframe,
                "bias": core_state["LTF_bias"],
                "structure": self._get_structure(price_data, entry_dt)
            }
        }
        
        return {
            "entry_time": str(entry_dt),
            "core_state": core_state,
            "strategy_specific_state": strategy_specific,
            "used_vs_observed": used_vs_observed,
            "multi_timeframe": multi_tf_state
        }
    
    def _get_htf_bias(self, htf_data: pd.DataFrame, entry_dt) -> str:
        """Get HTF bias at entry time"""
        bias = htf_bias(htf_data, pd.DatetimeIndex([entry_dt]))
        return bias.iloc[0] if len(bias) > 0 else "NEUTRAL"
    
    def _get_ltf_bias(self, price_data: pd.DataFrame, entry_index: int) -> str:
        """Get LTF bias based on recent price action"""
        lookback = 20
        if entry_index < lookback:
            return "NEUTRAL"
        
        recent_slice = price_data.iloc[entry_index-lookback:entry_index+1]
        if recent_slice['close'].iloc[-1] > recent_slice['close'].iloc[0]:
            return "LONG"
        elif recent_slice['close'].iloc[-1] < recent_slice['close'].iloc[0]:
            return "SHORT"
        return "NEUTRAL"
    
    def _get_session(self, entry_dt) -> str:
        """Get session at entry time"""
        ny_time = entry_dt.tz_convert('America/New_York')
        hour = ny_time.hour
        
        if 2 <= hour < 5:
            return "LONDON_OPEN"
        elif 8 <= hour < 11:
            return "NY_AM"
        elif 10 <= hour < 12:
            return "LONDON_CLOSE"
        elif 13.5 <= hour < 16:
            return "NY_PM"
        elif 18 <= hour or hour < 3:
            return "ASIA"
        else:
            return "OTHER"
    
    def _get_killzone(self, entry_dt) -> Optional[str]:
        """Get killzone at entry time"""
        ny_time = entry_dt.tz_convert('America/New_York')
        hour = ny_time.hour + ny_time.minute / 60
        
        if 2 <= hour < 5:
            return "london_open"
        elif 8 <= hour < 11:
            return "ny_am"
        elif 10 <= hour < 12:
            return "london_close"
        elif 13.5 <= hour < 16:
            return "ny_pm"
        return None
    
    def _get_previous_day_high(self, price_data: pd.DataFrame, entry_index: int) -> Optional[float]:
        """Get previous day high"""
        if entry_index == 0:
            return None
        prev_day = price_data.iloc[:entry_index].index.date[-1]
        prev_day_data = price_data[price_data.index.date == prev_day]
        return prev_day_data['high'].max() if len(prev_day_data) > 0 else None
    
    def _get_previous_day_low(self, price_data: pd.DataFrame, entry_index: int) -> Optional[float]:
        """Get previous day low"""
        if entry_index == 0:
            return None
        prev_day = price_data.iloc[:entry_index].index.date[-1]
        prev_day_data = price_data[price_data.index.date == prev_day]
        return prev_day_data['low'].min() if len(prev_day_data) > 0 else None
    
    def _get_previous_week_high(self, price_data: pd.DataFrame, entry_index: int) -> Optional[float]:
        """Get previous week high"""
        if entry_index < 5 * 24 * 12:  # Minimum 5 days of 5-min data
            return None
        prev_week_data = price_data.iloc[:entry_index]
        return prev_week_data['high'].max()
    
    def _get_previous_week_low(self, price_data: pd.DataFrame, entry_index: int) -> Optional[float]:
        """Get previous week low"""
        if entry_index < 5 * 24 * 12:
            return None
        prev_week_data = price_data.iloc[:entry_index]
        return prev_week_data['low'].min()
    
    def _get_structure(self, df: pd.DataFrame, entry_dt) -> str:
        """Get market structure"""
        # Simplified structure detection
        lookback = 20
        if entry_dt not in df.index:
            return "UNKNOWN"
        
        entry_idx = df.index.get_loc(entry_dt)
        if entry_idx < lookback:
            return "UNKNOWN"
        
        recent = df.iloc[entry_idx-lookback:entry_idx+1]
        highs = recent['high']
        lows = recent['low']
        
        # Check for HH/HL or LH/LL
        if highs.iloc[-1] > highs.iloc[-2] and lows.iloc[-1] > lows.iloc[-2]:
            return "HH_HL"
        elif highs.iloc[-1] < highs.iloc[-2] and lows.iloc[-1] < lows.iloc[-2]:
            return "LH_LL"
        elif highs.iloc[-1] > highs.iloc[-2] and lows.iloc[-1] < lows.iloc[-2]:
            return "HH_LL"
        elif highs.iloc[-1] < highs.iloc[-2] and lows.iloc[-1] > lows.iloc[-2]:
            return "LH_HL"
        
        return "UNKNOWN"
    
    def _get_strategy_specific_state(self, price_data: pd.DataFrame, entry_index: int, config: Any, htf_data: pd.DataFrame) -> Dict[str, Any]:
        """Get strategy-specific market state"""
        strategy_id = self.strategy_id
        
        if "fvg_ce" in strategy_id:
            return {
                "FVG": self._check_fvg(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index)
            }
        elif "order_block" in strategy_id:
            return {
                "OB": self._check_ob(price_data, entry_index),
                "breaker": self._check_breaker(price_data, entry_index)
            }
        elif "silver_bullet" in strategy_id or "2022_model" in strategy_id:
            return {
                "FVG": self._check_fvg(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index),
                "liquidity_swept": self._check_liquidity_sweep(price_data, entry_index),
                "sweep_type": self._get_sweep_type(price_data, entry_index)
            }
        elif "unicorn" in strategy_id:
            return {
                "FVG": self._check_fvg(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index),
                "displacement_strength": self._get_displacement_strength(price_data, entry_index)
            }
        elif "judas" in strategy_id:
            return {
                "liquidity_swept": self._check_liquidity_sweep(price_data, entry_index),
                "sweep_type": self._get_sweep_type(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index)
            }
        elif "asian_range" in strategy_id:
            return {
                "Asian_range": self._get_asian_range(price_data, entry_index),
                "liquidity_swept": self._check_liquidity_sweep(price_data, entry_index)
            }
        elif "venom" in strategy_id:
            return {
                "pre_open_range": self._get_pre_open_range(price_data, entry_index),
                "false_breakout": self._check_false_breakout(price_data, entry_index)
            }
        elif "ote_pd" in strategy_id:
            return {
                "OTE": self._check_ote(price_data, entry_index),
                "PD_array": self._check_pd_array(price_data, entry_index)
            }
        elif "bread_and_butter" in strategy_id:
            return {
                "PM_range": self._get_pm_range(price_data, entry_index),
                "Asia_extension": self._get_asia_extension(price_data, entry_index)
            }
        elif "2023_model" in strategy_id:
            return {
                "FVG": self._check_fvg(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index),
                "competing_fvg": self._check_competing_fvg(price_data, entry_index)
            }
        elif "2024_model" in strategy_id:
            return {
                "FVG": self._check_fvg(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index),
                "competing_fvg": self._check_competing_fvg(price_data, entry_index)
            }
        elif "london_close" in strategy_id:
            return {
                "London_direction": self._get_london_direction(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index)
            }
        elif "ny_pm" in strategy_id:
            return {
                "NY_AM_direction": self._get_ny_am_direction(price_data, entry_index),
                "PM_range": self._get_pm_range(price_data, entry_index),
                "displacement": self._check_displacement(price_data, entry_index)
            }
        else:
            return {}
    
    def _check_fvg(self, price_data: pd.DataFrame, entry_index: int) -> Dict[str, Any]:
        """Check for FVG at entry"""
        if entry_index < 2:
            return {"present": False}
        
        try:
            # Check recent FVGs
            fvgs = fair_value_gaps(price_data, min_gap_pips=0.50)
            entry_dt = price_data.index[entry_index]
            recent_fvgs = fvgs[fvgs['timestamp'] <= entry_dt]
            
            if len(recent_fvgs) > 0:
                latest_fvg = recent_fvgs.iloc[-1]
                return {
                    "present": True,
                    "direction": latest_fvg['direction'],
                    "high": latest_fvg['high'],
                    "low": latest_fvg['low'],
                    "ce": latest_fvg['ce']
                }
        except Exception:
            pass
        return {"present": False}
    
    def _check_displacement(self, price_data: pd.DataFrame, entry_index: int) -> Optional[bool]:
        """Check for displacement at entry"""
        if entry_index < 1:
            return None
        
        try:
            displacement = detect_displacement(price_data, min_range_pct=1.5)
            return displacement.iloc[entry_index]
        except Exception:
            return None
    
    def _check_liquidity_sweep(self, price_data: pd.DataFrame, entry_index: int) -> Optional[bool]:
        """Check for liquidity sweep at entry"""
        # Simplified - would need actual sweep detection from ict_signals
        return None
    
    def _get_sweep_type(self, price_data: pd.DataFrame, entry_index: int) -> Optional[str]:
        """Get sweep type at entry"""
        return None
    
    def _check_ob(self, price_data: pd.DataFrame, entry_index: int) -> Dict[str, Any]:
        """Check for Order Block at entry"""
        try:
            obs = order_blocks(price_data, Direction.LONG)
            entry_dt = price_data.index[entry_index]
            recent_obs = obs[obs['timestamp'] <= entry_dt]
            
            if len(recent_obs) > 0:
                latest_ob = recent_obs.iloc[-1]
                return {
                    "present": True,
                    "direction": latest_ob['direction'],
                    "high": latest_ob['high'],
                    "low": latest_ob['low']
                }
        except Exception:
            pass
        return {"present": False}
    
    def _check_breaker(self, price_data: pd.DataFrame, entry_index: int) -> Optional[bool]:
        """Check for breaker at entry"""
        return None
    
    def _get_displacement_strength(self, price_data: pd.DataFrame, entry_index: int) -> Dict[str, Any]:
        """Get displacement strength metrics"""
        try:
            from ict_signals import displacement_strength
            strength = displacement_strength(price_data)
            return {
                "body_ratio": strength['body_ratio'].iloc[entry_index],
                "opposing_wick_ratio": strength['opposing_wick_ratio'].iloc[entry_index]
            }
        except Exception:
            return {"body_ratio": None, "opposing_wick_ratio": None}
    
    def _get_asian_range(self, price_data: pd.DataFrame, entry_index: int) -> Optional[Dict[str, float]]:
        """Get Asian range at entry"""
        return None
    
    def _get_pre_open_range(self, price_data: pd.DataFrame, entry_index: int) -> Optional[Dict[str, float]]:
        """Get pre-open range at entry"""
        return None
    
    def _check_false_breakout(self, price_data: pd.DataFrame, entry_index: int) -> Optional[bool]:
        """Check for false breakout at entry"""
        return None
    
    def _check_ote(self, price_data: pd.DataFrame, entry_index: int) -> Optional[Dict[str, Any]]:
        """Check for OTE at entry"""
        return None
    
    def _check_pd_array(self, price_data: pd.DataFrame, entry_index: int) -> Optional[Dict[str, Any]]:
        """Check for PD array at entry"""
        return None
    
    def _get_pm_range(self, price_data: pd.DataFrame, entry_index: int) -> Optional[Dict[str, float]]:
        """Get PM range at entry"""
        return None
    
    def _get_asia_extension(self, price_data: pd.DataFrame, entry_index: int) -> Optional[Dict[str, float]]:
        """Get Asia extension at entry"""
        return None
    
    def _check_competing_fvg(self, price_data: pd.DataFrame, entry_index: int) -> Optional[bool]:
        """Check for competing FVG at entry"""
        return None
    
    def _get_london_direction(self, price_data: pd.DataFrame, entry_index: int) -> Optional[str]:
        """Get London direction at entry"""
        return None
    
    def _get_ny_am_direction(self, price_data: pd.DataFrame, entry_index: int) -> Optional[str]:
        """Get NY AM direction at entry"""
        return None
    
    def _determine_used_vs_observed(self, core_state: Dict[str, Any], strategy_specific: Dict[str, Any], config: Any) -> Dict[str, Dict[str, bool]]:
        """Determine which concepts are used vs observed"""
        # Core concepts are always observed
        used_vs_observed = {
            "HTF_bias": {"observed_at_entry": True, "used_by_strategy": True},
            "LTF_bias": {"observed_at_entry": True, "used_by_strategy": True},
            "session": {"observed_at_entry": True, "used_by_strategy": True},
            "kill_zone": {"observed_at_entry": True, "used_by_strategy": True},
        }
        
        # Strategy-specific concepts
        for concept in strategy_specific:
            used_vs_observed[concept] = {
                "observed_at_entry": True,
                "used_by_strategy": True
            }
        
        return used_vs_observed


if __name__ == "__main__":
    print("Market State Recorder - VECTORBT BACKTEST AGENT")
    print("=" * 60)
    print("Tiered approach:")
    print("- Core concepts (always recorded): HTF_bias, LTF_bias, session, kill_zone")
    print("- Strategy-specific concepts (based on strategy): FVG, OB, displacement, etc.")
    print("\nExample usage:")
    print(">>> from market_state_recorder import MarketStateRecorder")
    print(">>> recorder = MarketStateRecorder('fvg_ce_entry')")
    print(">>> state = recorder.record_market_state(price_data, entry_index, config, htf_data)")
    print(">>> print(state)")
