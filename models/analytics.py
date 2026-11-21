"""
CareGrid AI — Analytics Utilities
====================================
Pure utility functions for statistical analysis and data transformations.
No database dependency — operates on raw values and DataFrames.

Usage:
    from models.analytics import calculate_trend, detect_anomalies
    trend = calculate_trend([10, 12, 15, 18, 22])
    outliers = detect_anomalies(values, threshold=2.5)
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd


def calculate_trend(values: list[float | int]) -> str:
    """
    Determine whether a series of values is increasing, decreasing, or stable.

    Uses ordinary least-squares linear regression slope.
    A slope within ±0.5 % of the mean is considered *stable*.

    Args:
        values: Ordered numeric series (oldest → newest).

    Returns:
        One of ``'increasing'``, ``'decreasing'``, or ``'stable'``.
    """
    if not values or len(values) < 2:
        return "stable"

    arr = np.array(values, dtype=float)
    n = len(arr)
    x = np.arange(n, dtype=float)

    # Least-squares slope: Σ(x - x̄)(y - ȳ) / Σ(x - x̄)²
    x_mean = x.mean()
    y_mean = arr.mean()
    numerator = np.sum((x - x_mean) * (arr - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Normalize slope relative to the mean to judge significance
    if y_mean == 0:
        threshold = 0.01
    else:
        threshold = abs(y_mean) * 0.005  # 0.5 % of mean

    if slope > threshold:
        return "increasing"
    elif slope < -threshold:
        return "decreasing"
    return "stable"


def calculate_moving_average(
    values: list[float | int],
    window: int = 7,
) -> list[Optional[float]]:
    """
    Compute a simple moving average (SMA).

    Leading positions where the window is incomplete are filled with ``None``.

    Args:
        values: Input numeric series.
        window: Window size (must be ≥ 1).

    Returns:
        List of the same length with moving-average values or ``None``.
    """
    if window < 1:
        raise ValueError("window must be >= 1")

    result: list[Optional[float]] = []
    arr = np.array(values, dtype=float)

    for i in range(len(arr)):
        if i < window - 1:
            result.append(None)
        else:
            result.append(float(np.mean(arr[i - window + 1 : i + 1])))
    return result


def detect_anomalies(
    values: list[float | int],
    threshold: float = 2.0,
) -> list[int]:
    """
    Detect anomalous values using z-score analysis.

    Args:
        values: Input numeric series.
        threshold: Number of standard deviations beyond which a value
                   is considered anomalous.

    Returns:
        List of indices where the absolute z-score exceeds *threshold*.
    """
    if not values or len(values) < 3:
        return []

    arr = np.array(values, dtype=float)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)  # sample std

    if std == 0:
        return []

    z_scores = np.abs((arr - mean) / std)
    return [int(i) for i in np.where(z_scores > threshold)[0]]


def calculate_growth_rate(old_val: float | int, new_val: float | int) -> float:
    """
    Calculate percentage growth rate between two values.

    Args:
        old_val: Previous / baseline value.
        new_val: Current / latest value.

    Returns:
        Growth rate as a percentage (e.g. 25.0 for 25 % growth).
        Returns 0.0 when *old_val* is zero.
    """
    if old_val == 0:
        return 0.0
    return ((new_val - old_val) / abs(old_val)) * 100.0


def aggregate_by_period(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    period: str = "W",
) -> pd.DataFrame:
    """
    Aggregate a DataFrame by a time period.

    Args:
        df: Source DataFrame (must contain *date_col* and *value_col*).
        date_col: Name of the datetime / date column.
        value_col: Name of the numeric column to aggregate (sum).
        period: Pandas offset alias — ``'D'`` (daily), ``'W'`` (weekly),
                ``'M'`` (monthly), ``'Q'`` (quarterly), etc.

    Returns:
        DataFrame with columns [date_col, value_col] aggregated per period.
    """
    temp = df[[date_col, value_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col])
    temp = temp.set_index(date_col)
    resampled = temp.resample(period).sum().reset_index()
    resampled.columns = [date_col, value_col]
    return resampled
