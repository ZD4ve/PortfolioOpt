from __future__ import annotations

from importlib import import_module
from functools import lru_cache
from typing import Iterable
import os

import numpy as np
import pandas as pd
from pypfopt import expected_returns, risk_models
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt.efficient_frontier import EfficientFrontier

from .data_download import download_price_frame
from .models import PortfolioBundle

BASE_CURRENCY = os.getenv("PORTFOLIO_BASE_CURRENCY", "EUR")
DEFAULT_BUDGET = float(os.getenv("PORTFOLIO_BUDGET", "10000"))
DEFAULT_LOOKBACK_MONTHS = int(os.getenv("PORTFOLIO_LOOKBACK_MONTHS", "12"))
DEFAULT_RANDOM_SAMPLES = int(os.getenv("PORTFOLIO_RANDOM_SAMPLES", "5000"))


def _optimizer_core_module():
    return import_module("portfolio_dash.optimizer_core")


def clip_target_return(bundle: PortfolioBundle, target_return: float) -> float:
    lower = min(bundle.frontier_returns) if bundle.frontier_returns else bundle.ret_opt
    upper = max(bundle.frontier_returns) if bundle.frontier_returns else bundle.ret_opt
    return float(np.clip(target_return, lower, upper))


@lru_cache(maxsize=8)
def load_portfolio_bundle(
    budget: float = DEFAULT_BUDGET,
    base_currency: str = BASE_CURRENCY,
    lookback_months: int = DEFAULT_LOOKBACK_MONTHS,
    random_samples: int = DEFAULT_RANDOM_SAMPLES,
) -> PortfolioBundle:
    converted, names, failed_tickers = download_price_frame(
        base_currency=base_currency,
        lookback_months=lookback_months,
    )

    mu = pd.Series(expected_returns.mean_historical_return(converted), index=converted.columns, dtype=float)
    covariance = pd.DataFrame(risk_models.sample_cov(converted), index=converted.columns, columns=converted.columns, dtype=float)

    core = _optimizer_core_module()
    optimum = core.optimize_without_target(mu, covariance)
    cleaned_weights = optimum.weights
    ret_opt_value = optimum.expected_return
    std_opt_value = optimum.volatility
    sharpe_opt_value = optimum.sharpe

    latest_prices = get_latest_prices(converted)
    discrete = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=int(budget))
    allocation, leftover = discrete.greedy_portfolio()

    n_assets = converted.shape[1]
    random_weights = np.random.default_rng(42).dirichlet(np.full(n_assets, 0.25), size=random_samples)
    random_returns = random_weights @ mu.to_numpy()
    covariance_array = covariance.to_numpy()
    random_stds = np.sqrt(np.einsum("ij,jk,ik->i", random_weights, covariance_array, random_weights))
    random_sharpes = np.divide(
        random_returns,
        random_stds,
        out=np.zeros_like(random_returns),
        where=random_stds != 0,
    )
    asset_vols = pd.Series(np.sqrt(np.diag(covariance_array)), index=converted.columns)

    min_vol_frontier = EfficientFrontier(mu, covariance)
    min_vol_frontier.min_volatility()
    min_vol_perf = np.asarray(min_vol_frontier.portfolio_performance(verbose=False), dtype=float)
    min_vol_ret_value = float(min_vol_perf[0])
    upper_ret = max(float(mu.max()), ret_opt_value)

    frontier_returns: list[float] = []
    frontier_vols: list[float] = []
    for target_return in np.linspace(min_vol_ret_value, upper_ret, 40):
        try:
            frontier = EfficientFrontier(mu, covariance)
            frontier.efficient_return(target_return=float(target_return))
            frontier_perf = np.asarray(frontier.portfolio_performance(verbose=False), dtype=float)
            volatility = float(frontier_perf[1])
            frontier_returns.append(float(target_return))
            frontier_vols.append(volatility)
        except Exception:
            continue

    if not frontier_returns:
        frontier_returns = [ret_opt_value]
        frontier_vols = [std_opt_value]

    return PortfolioBundle(
        price_frame=converted,
        mu=mu,
        covariance=covariance,
        cleaned_weights=cleaned_weights,
        ret_opt=ret_opt_value,
        std_opt=std_opt_value,
        sharpe_opt=sharpe_opt_value,
        latest_prices=latest_prices,
        allocation=allocation,
        leftover=float(leftover),
        random_returns=random_returns,
        random_stds=random_stds,
        random_sharpes=random_sharpes,
        random_weights=random_weights,
        frontier_returns=frontier_returns,
        frontier_vols=frontier_vols,
        asset_vols=asset_vols,
        names=names,
        failed_tickers=failed_tickers,
        budget=float(budget),
        base_currency=base_currency,
        lookback_months=int(lookback_months),
    )


def calculate_target_portfolio(bundle: PortfolioBundle, target_return_percent: float) -> dict:
    target_return = clip_target_return(bundle, target_return_percent / 100)
    core = _optimizer_core_module()
    try:
        optimized = core.optimize_with_target_return(
            bundle.mu,
            bundle.covariance,
            target_return=target_return,
        )
    except Exception:
        optimized = None

    if optimized is None:
        raw_weights = bundle.cleaned_weights
        portfolio_return_value = bundle.ret_opt
        volatility_value = bundle.std_opt
        sharpe_value = bundle.sharpe_opt
    else:
        raw_weights = optimized.weights
        portfolio_return_value = optimized.expected_return
        volatility_value = optimized.volatility
        sharpe_value = optimized.sharpe

    discrete = DiscreteAllocation(raw_weights, bundle.latest_prices, total_portfolio_value=int(bundle.budget))
    allocation, leftover = discrete.greedy_portfolio()

    rows = []
    actual_total = bundle.budget - float(leftover)
    for symbol, weight in sorted(raw_weights.items(), key=lambda item: item[1], reverse=True):
        shares = int(allocation.get(symbol, 0))
        actual_value = float(shares * bundle.latest_prices[symbol])
        actual_weight = actual_value / bundle.budget if bundle.budget else 0
        rows.append(
            {
                "symbol": symbol,
                "label": bundle.names.get(symbol, symbol),
                "ideal_weight": float(weight),
                "shares": shares,
                "actual_value": actual_value,
                "actual_weight": actual_weight,
            }
        )

    return {
        "target_return_percent": portfolio_return_value * 100,
        "volatility_percent": volatility_value * 100,
        "sharpe": sharpe_value,
        "leftover": float(leftover),
        "invested_amount": float(actual_total),
        "rows": rows,
    }


def summary_cards(bundle: PortfolioBundle, target_return_percent: float) -> list[dict[str, str]]:
    portfolio = calculate_target_portfolio(bundle, target_return_percent)
    return [
        {"label": "Budget", "value": f"{bundle.budget:,.0f} {bundle.base_currency}"},
        {"label": "Lookback", "value": f"{bundle.lookback_months} months"},
        {"label": "Assets used", "value": str(bundle.price_frame.shape[1])},
        {"label": "Expected return", "value": f"{portfolio['target_return_percent']:.2f}%"},
        {"label": "Risk", "value": f"{portfolio['volatility_percent']:.2f}%"},
        {"label": "Cash left", "value": f"{portfolio['leftover']:.2f} {bundle.base_currency}"},
    ]


def allocation_table_rows(bundle: PortfolioBundle, target_return_percent: float) -> list[dict[str, str]]:
    portfolio = calculate_target_portfolio(bundle, target_return_percent)
    rows: list[dict[str, str]] = []
    for row in portfolio["rows"]:
        rows.append(
            {
                "Asset": row["label"],
                "Shares": str(row["shares"]),
                "Target Weight": f"{row['ideal_weight']:.2%}",
                "Actual Weight": f"{row['actual_weight']:.2%}",
                "Cost": f"{row['actual_value']:.2f} {bundle.base_currency}",
            }
        )
    return rows


def supported_symbol_notes() -> Iterable[str]:
    yield "This is a hobby project and not a financial advice tool. Always do your own research before investing."
    yield "Data is sourced from Yahoo Finance via the yfinance library. It may contain errors or omissions. Verify critical data points independently."
