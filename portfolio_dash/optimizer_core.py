from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pypfopt.efficient_frontier import EfficientFrontier


@dataclass(frozen=True)
class OptimizationResult:
    weights: dict[str, float]
    expected_return: float
    volatility: float
    sharpe: float


def _clean_positive_weights(raw_weights: Mapping[Any, float]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for symbol, weight in raw_weights.items():
        weight_value = float(weight)
        if weight_value > 0:
            cleaned[str(symbol)] = weight_value
    return cleaned


def _to_performance_tuple(perf: tuple[object, object, object]) -> tuple[float, float, float]:
    arr = np.asarray(perf, dtype=float)
    return float(arr[0]), float(arr[1]), float(arr[2])


def optimize_without_target(
    mu: pd.Series,
    covariance: pd.DataFrame,
) -> OptimizationResult:
    frontier = EfficientFrontier(mu, covariance)
    frontier.max_sharpe()
    expected_return, volatility, sharpe = _to_performance_tuple(frontier.portfolio_performance(verbose=False))
    return OptimizationResult(
        weights=_clean_positive_weights(frontier.clean_weights()),
        expected_return=expected_return,
        volatility=volatility,
        sharpe=sharpe,
    )


def optimize_with_target_return(
    mu: pd.Series,
    covariance: pd.DataFrame,
    *,
    target_return: float,
    fallback: OptimizationResult | None = None,
) -> OptimizationResult:
    try:
        frontier = EfficientFrontier(mu, covariance)
        frontier.efficient_return(target_return=target_return)
        expected_return, volatility, sharpe = _to_performance_tuple(frontier.portfolio_performance(verbose=False))
        return OptimizationResult(
            weights=_clean_positive_weights(frontier.clean_weights()),
            expected_return=expected_return,
            volatility=volatility,
            sharpe=sharpe,
        )
    except Exception:
        if fallback is None:
            raise
        return fallback
