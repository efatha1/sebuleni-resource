"""
Data Loader - Load and prepare ICT trading data

Handles loading parquet data and timezone conversion for ICT backtesting.
All data is assumed to be in UTC timezone and converted to NY timezone for
session/killzone analysis.

Timezone Assumption:
- Parquet index is assumed to be in UTC
- Conversion to America/New_York handled by ict_signals.in_killzone()
- DST handled automatically via pytz/zoneinfo

No Volume Constraint:
- Data contains only OHLC (open, high, low, close)
- No volume column in parquet schema
"""

import pandas as pd
import numpy as np
import pytz
from pathlib import Path
from typing import Dict, Any, Optional


def load_data(symbol: str, timeframe: str, data_dir: str = "data",
              start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Load parquet data with flexible filename matching, date filtering, and timezone handling.
    
    Args:
        symbol: Instrument symbol (e.g., "XAUUSD")
        timeframe: Timeframe (e.g., "5m", "1h", "1d")
        data_dir: Directory containing parquet files (default: "data")
        start_date: Optional start date for filtering (e.g., "2024-01-01")
        end_date: Optional end date for filtering (e.g., "2024-12-31")
    
    Returns:
        DataFrame with datetime index in UTC timezone
    
    Timezone Assumption:
    - Parquet index is assumed to be UTC
    - Conversion to NY timezone handled by ict_signals.in_killzone()
    - This function ensures UTC timezone is set if missing
    
    Filename Mapping:
    - Handles both "XAUUSD_5m.parquet" and "xauusd_5min.parquet" formats
    - Maps "5m" to "5min", "1h" to "1h", "1d" to "1D"
    
    Example:
        >>> df = load_data("XAUUSD", "5m", start_date="2024-01-01", end_date="2024-01-31")
        >>> df.head()
    """
    # Filename mapping
    timeframe_map = {
        '5m': '5min', '15m': '15min', '30m': '30min',
        '1h': '1h', '4h': '4h', '1d': '1D'
    }
    
    # Normalize inputs
    symbol_lower = symbol.lower()
    actual_timeframe = timeframe_map.get(timeframe, timeframe)
    
    # Try multiple filename patterns to handle different naming conventions
    possible_patterns = [
        f"{symbol_lower}_{actual_timeframe}.parquet",
        f"{symbol}_{actual_timeframe}.parquet",
        f"{symbol_lower}_{timeframe}.parquet",
        f"{symbol}_{timeframe}.parquet"
    ]
    
    # Find existing file
    file_path = None
    for pattern in possible_patterns:
        test_path = Path(data_dir) / pattern
        if test_path.exists():
            file_path = test_path
            break
    
    if file_path is None:
        raise FileNotFoundError(f"No data file found for {symbol}_{timeframe} in {data_dir}")
    
    # Load and process
    df = pd.read_parquet(file_path)
    df.index = pd.to_datetime(df.index)
    
    # Timezone handling
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    elif df.index.tz.zone != 'UTC':
        df.index = df.index.tz_convert('UTC')
    
    # Column normalization (convert to lowercase)
    df.columns = df.columns.str.lower()
    
    # Date filtering
    if start_date:
        start_dt = pd.to_datetime(start_date).tz_localize('UTC')
        df = df[df.index >= start_dt]
    if end_date:
        end_dt = pd.to_datetime(end_date).tz_localize('UTC')
        df = df[df.index <= end_dt]
    
    # Validation
    required_columns = ['open', 'high', 'low', 'close']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    if df.isnull().any().any():
        raise ValueError("Data contains null values")
    
    df = df.sort_index()
    return df


def load_multiple_timeframes(symbol: str, timeframes: list, data_dir: str = "data") -> dict:
    """
    Load multiple timeframes for a single symbol.
    
    Args:
        symbol: Instrument symbol (e.g., "XAUUSD")
        timeframes: List of timeframes (e.g., ["5m", "1h", "1d"])
        data_dir: Directory containing parquet files (default: "data")
    
    Returns:
        Dictionary mapping timeframe to DataFrame
    
    Example:
        >>> data = load_multiple_timeframes("XAUUSD", ["5m", "1h", "1d"])
        >>> data["5m"].head()
    """
    data = {}
    for tf in timeframes:
        data[tf] = load_data(symbol, tf, data_dir)
    return data


def resample_data(df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """
    Resample data to a different timeframe.
    
    Note: This function is provided for completeness but the project
    specification states that parquet files are already resampled.
    Use with caution as it may introduce look-ahead bias if not handled properly.
    
    Args:
        df: DataFrame with OHLC data
        target_timeframe: Target timeframe (e.g., "1h", "1d")
    
    Returns:
        Resampled DataFrame
    
    Example:
        >>> df_5m = load_data("XAUUSD", "5m")
        >>> df_1h = resample_data(df_5m, "1h")
    """
    # Define resampling mapping
    resample_map = {
        '1m': '1T',
        '5m': '5T',
        '15m': '15T',
        '30m': '30T',
        '1h': '1H',
        '4h': '4H',
        '1d': '1D',
        '1w': '1W',
    }
    
    if target_timeframe not in resample_map:
        raise ValueError(f"Unsupported timeframe: {target_timeframe}")
    
    resample_rule = resample_map[target_timeframe]
    
    resampled = df.resample(resample_rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    })
    
    return resampled


def validate_data(df: pd.DataFrame) -> dict:
    """
    Validate DataFrame for ICT backtesting requirements.
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Dictionary with validation results
    
    Example:
        >>> df = load_data("XAUUSD", "5m")
        >>> validation = validate_data(df)
        >>> print(validation)
    """
    results = {
        'has_ohlc': False,
        'has_timezone': False,
        'is_utc': False,
        'no_nulls': False,
        'is_sorted': False,
        'no_volume': True,  # Assume no volume by default
    }
    
    # Check OHLC columns
    required_columns = ['open', 'high', 'low', 'close']
    results['has_ohlc'] = all(col in df.columns for col in required_columns)
    
    # Check timezone
    results['has_timezone'] = df.index.tz is not None
    if results['has_timezone']:
        results['is_utc'] = df.index.tz.zone == 'UTC'
    
    # Check for nulls
    results['no_nulls'] = not df[required_columns].isnull().any().any()
    
    # Check if sorted
    results['is_sorted'] = df.index.is_monotonic_increasing
    
    # Check for volume column
    results['no_volume'] = 'volume' not in df.columns
    
    return results


def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive data quality validation for backtest agent.
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Dictionary with validation results including:
        - has_ohlc, no_nulls, is_sorted, no_duplicates
        - has_timezone, is_utc
        - index_range, data_points
    
    Example:
        >>> df = load_data("XAUUSD", "5m")
        >>> validation = validate_data_quality(df)
        >>> print(validation)
    """
    results = {
        'has_ohlc': all(col in df.columns for col in ['open', 'high', 'low', 'close']),
        'no_nulls': not df.isnull().any().any(),
        'is_sorted': df.index.is_monotonic_increasing,
        'no_duplicates': not df.index.duplicated().any(),
        'has_timezone': df.index.tz is not None,
        'is_utc': df.index.tz.zone == 'UTC' if df.index.tz else False,
        'index_range': (df.index.min(), df.index.max()),
        'data_points': len(df)
    }
    
    return results


def create_sample_data(symbol: str = "XAUUSD", timeframe: str = "5m", 
                       start_date: str = "2024-01-01", end_date: str = "2024-01-31",
                       data_dir: str = "data") -> pd.DataFrame:
    """
    Create sample data for testing when parquet files are not available.
    
    This function generates synthetic OHLC data for testing purposes.
    Not intended for production use.
    
    Args:
        symbol: Instrument symbol
        timeframe: Timeframe
        start_date: Start date
        end_date: End date
        data_dir: Directory to save sample data
    
    Returns:
        DataFrame with synthetic OHLC data
    
    Example:
        >>> df = create_sample_data("XAUUSD", "5m", "2024-01-01", "2024-01-31")
        >>> df.head()
    """
    import numpy as np
    
    # Create date range
    date_range = pd.date_range(start=start_date, end=end_date, freq='5T', tz='UTC')
    
    # Generate synthetic price data
    np.random.seed(42)
    base_price = 2000.0  # Approximate gold price
    
    returns = np.random.normal(0, 0.001, len(date_range))
    prices = base_price * (1 + returns).cumprod()
    
    # Create OHLC from prices
    high = prices * (1 + np.random.uniform(0, 0.002, len(date_range)))
    low = prices * (1 - np.random.uniform(0, 0.002, len(date_range)))
    open_prices = prices.copy()
    close_prices = prices.copy()
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close_prices
    }, index=date_range)
    
    # Sort index
    df = df.sort_index()
    
    return df


def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive data quality validation for backtest agent.
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Dictionary with validation results including:
        - has_ohlc, no_nulls, is_sorted, no_duplicates
        - has_timezone, is_utc
        - index_range, data_points
    
    Example:
        >>> df = load_data("XAUUSD", "5m")
        >>> validation = validate_data_quality(df)
        >>> print(validation)
    """
    results = {
        'has_ohlc': all(col in df.columns for col in ['open', 'high', 'low', 'close']),
        'no_nulls': not df.isnull().any().any(),
        'is_sorted': df.index.is_monotonic_increasing,
        'no_duplicates': not df.index.duplicated().any(),
        'has_timezone': df.index.tz is not None,
        'is_utc': df.index.tz.zone == 'UTC' if df.index.tz else False,
        'index_range': (df.index.min(), df.index.max()),
        'data_points': len(df)
    }
    
    return results


if __name__ == "__main__":
    print("Data Loader - ICT Trading Data Management")
    print("=" * 60)
    print("Available functions:")
    print("- load_data(symbol, timeframe, start_date, end_date): Load parquet data with date filtering")
    print("- load_multiple_timeframes(symbol, timeframes): Load multiple TFs")
    print("- resample_data(df, target_timeframe): Resample to different TF")
    print("- validate_data(df): Validate DataFrame for backtesting")
    print("- validate_data_quality(df): Comprehensive data quality validation")
    print("- create_sample_data(...): Create synthetic data for testing")
    print("\nExample usage:")
    print(">>> from data_loader import load_data")
    print(">>> df = load_data('XAUUSD', '5m', start_date='2024-01-01', end_date='2024-01-31')")
    print(">>> df.head()")
