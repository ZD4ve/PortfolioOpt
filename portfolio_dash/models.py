from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioBundle:
    price_frame: pd.DataFrame
    mu: pd.Series
    covariance: pd.DataFrame
    cleaned_weights: dict[str, float]
    ret_opt: float
    std_opt: float
    sharpe_opt: float
    latest_prices: pd.Series
    allocation: dict[str, int]
    leftover: float
    random_returns: np.ndarray
    random_stds: np.ndarray
    random_sharpes: np.ndarray
    random_weights: np.ndarray
    frontier_returns: list[float]
    frontier_vols: list[float]
    asset_vols: pd.Series
    names: dict[str, str]
    failed_tickers: list[str]
    budget: float
    base_currency: str
    lookback_months: int
