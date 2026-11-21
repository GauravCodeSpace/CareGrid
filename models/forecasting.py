"""
CareGrid AI — Demand Forecasting Model
========================================
Linear Regression-based demand forecaster for medicine consumption.
Uses sklearn for prediction with confidence intervals.

Usage:
    from models.forecasting import DemandForecaster
    forecaster = DemandForecaster()
    forecaster.fit(consumption_df)
    result = forecaster.predict(days_ahead=14)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)


class DemandForecaster:
    """
    Medicine demand forecaster using Linear Regression.
    
    Features engineered from date:
        - day_of_week (0-6)
        - day_of_month (1-31)
        - month (1-12)
        - trend (sequential day index)
    """

    def __init__(self) -> None:
        """Initialize the forecaster."""
        self.model: Optional[LinearRegression] = None
        self.is_fitted: bool = False
        self._residual_std: float = 0.0
        self._last_date: Optional[datetime] = None
        self._mean_consumption: float = 0.0

    @staticmethod
    def _extract_features(dates: pd.Series) -> np.ndarray:
        """
        Extract time-based features from a date series.

        Args:
            dates: Series of datetime objects.

        Returns:
            Feature matrix with shape (n_samples, 4).
        """
        dates = pd.to_datetime(dates)
        features = np.column_stack([
            dates.dt.dayofweek.values,       # 0=Monday, 6=Sunday
            dates.dt.day.values,             # 1-31
            dates.dt.month.values,           # 1-12
            np.arange(len(dates)),           # trend index
        ])
        return features

    def fit(self, consumption_data: pd.DataFrame) -> "DemandForecaster":
        """
        Fit the Linear Regression model on historical consumption data.

        Args:
            consumption_data: DataFrame with columns 'date' and 'quantity'.
                              'date' should be datetime-like.
                              'quantity' should be the daily consumption amount.

        Returns:
            Self for method chaining.
        """
        if consumption_data.empty or len(consumption_data) < 3:
            logger.warning("Insufficient data for forecasting (need >= 3 records).")
            self.is_fitted = False
            return self

        # Sort by date
        df = consumption_data.sort_values("date").reset_index(drop=True)

        # Extract features and target
        X = self._extract_features(df["date"])
        y = df["quantity"].values.astype(float)

        # Fit model
        self.model = LinearRegression()
        self.model.fit(X, y)
        self.is_fitted = True

        # Calculate residual std for confidence intervals
        predictions = self.model.predict(X)
        residuals = y - predictions
        self._residual_std = float(np.std(residuals)) if len(residuals) > 1 else 0.0

        # Store metadata
        self._last_date = pd.to_datetime(df["date"].iloc[-1])
        self._mean_consumption = float(np.mean(y))
        self._trend_start = len(df)

        logger.info(
            "Forecaster fitted on %d data points. R²=%.3f, Residual STD=%.2f",
            len(df),
            self.model.score(X, y),
            self._residual_std,
        )
        return self

    def predict(self, days_ahead: int = 14) -> dict:
        """
        Predict future demand with confidence intervals.

        Args:
            days_ahead: Number of days to forecast.

        Returns:
            Dictionary with keys:
                - dates: List of date strings (YYYY-MM-DD)
                - values: List of predicted consumption values
                - confidence_lower: List of lower bound values
                - confidence_upper: List of upper bound values
        """
        if not self.is_fitted or self.model is None:
            logger.warning("Model not fitted. Returning empty prediction.")
            return {
                "dates": [],
                "values": [],
                "confidence_lower": [],
                "confidence_upper": [],
            }

        # Generate future dates
        future_dates = pd.date_range(
            start=self._last_date + timedelta(days=1),
            periods=days_ahead,
            freq="D",
        )

        # Create feature matrix for future dates
        future_features = np.column_stack([
            future_dates.dayofweek,
            future_dates.day,
            future_dates.month,
            np.arange(self._trend_start, self._trend_start + days_ahead),
        ])

        # Predict
        predicted = self.model.predict(future_features)

        # Ensure non-negative predictions
        predicted = np.maximum(predicted, 0)

        # Confidence intervals (±1 std)
        confidence_lower = np.maximum(predicted - self._residual_std, 0)
        confidence_upper = predicted + self._residual_std

        return {
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "values": [round(float(v), 1) for v in predicted],
            "confidence_lower": [round(float(v), 1) for v in confidence_lower],
            "confidence_upper": [round(float(v), 1) for v in confidence_upper],
        }

    def get_model_info(self) -> dict:
        """
        Get model metadata and coefficients.

        Returns:
            Dictionary with model information.
        """
        if not self.is_fitted or self.model is None:
            return {"fitted": False}

        feature_names = ["day_of_week", "day_of_month", "month", "trend"]
        return {
            "fitted": True,
            "coefficients": dict(zip(feature_names, self.model.coef_.tolist())),
            "intercept": float(self.model.intercept_),
            "residual_std": self._residual_std,
            "mean_consumption": self._mean_consumption,
        }
