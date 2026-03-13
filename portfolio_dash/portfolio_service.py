from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from pypfopt import expected_returns, risk_models
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt.efficient_frontier import EfficientFrontier
from portfolio_dash.tickers import RAW_TICKERS

BASE_CURRENCY = os.getenv("PORTFOLIO_BASE_CURRENCY", "EUR")
DEFAULT_BUDGET = float(os.getenv("PORTFOLIO_BUDGET", "10000"))
DEFAULT_LOOKBACK_MONTHS = int(os.getenv("PORTFOLIO_LOOKBACK_MONTHS", "12"))
DEFAULT_RANDOM_SAMPLES = int(os.getenv("PORTFOLIO_RANDOM_SAMPLES", "15000"))


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

def clean_name(name: str) -> str:
    value = name.strip()
    while "  " in value:
        value = value.replace("  ", " ")
    return value


def extract_currency(ticker: yf.Ticker, fallback: str) -> str:
    try:
        fast_info = ticker.fast_info
        if fast_info:
            currency = fast_info.get("currency")
            if currency:
                return str(currency)
    except Exception:
        pass

    try:
        metadata = ticker.get_history_metadata()
        currency = metadata.get("currency")
        if currency:
            return str(currency)
    except Exception:
        pass

    try:
        info = ticker.info
        currency = info.get("currency")
        if currency:
            return str(currency)
    except Exception:
        pass

    return fallback


def extract_name(ticker: yf.Ticker, fallback: str) -> str:
    for accessor in (
        lambda: ticker.fast_info.get("shortName"),
        lambda: ticker.info.get("shortName"),
        lambda: ticker.info.get("longName"),
    ):
        try:
            value = accessor()
            if value:
                return clean_name(str(value))
        except Exception:
            continue
    return fallback


def coerce_datetime_index(frame: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    return frame


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
    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.DateOffset(months=lookback_months)

    raw_prices = pd.DataFrame()
    fx_prices: dict[str, pd.Series] = {}
    stock_currencies: dict[str, str] = {}
    names: dict[str, str] = {}
    failed_tickers: list[str] = []

    for raw_ticker in RAW_TICKERS:
        symbol = raw_ticker
        fallback_name = raw_ticker

        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(
                start=start_date,
                end=end_date,
                auto_adjust=True,
                repair=True,
            )
            if history.empty or "Close" not in history:
                failed_tickers.append(symbol)
                continue

            close_series = history["Close"].copy()
            coerce_datetime_index(close_series)
            raw_prices[symbol] = close_series
            stock_currencies[symbol] = extract_currency(ticker, base_currency)
            display_name = extract_name(ticker, fallback_name)
            names[symbol] = f"{display_name} ({fallback_name})" if display_name != fallback_name else fallback_name
        except Exception:
            failed_tickers.append(symbol)

    if raw_prices.empty:
        raise RuntimeError("No market data could be downloaded. Check the ticker universe or network access.")

    for currency in sorted({value for value in stock_currencies.values() if value != base_currency}):
        fx_symbol = f"{currency}{base_currency}=X"
        try:
            history = yf.Ticker(fx_symbol).history(
                start=start_date,
                end=end_date,
                auto_adjust=True,
                repair=True,
            )
            if history.empty or "Close" not in history:
                raise RuntimeError(f"Missing FX history for {fx_symbol}")
            close_series = history["Close"].copy()
            coerce_datetime_index(close_series)
            fx_prices[fx_symbol] = close_series
        except Exception as exc:
            raise RuntimeError(f"Could not download FX conversion data for {fx_symbol}: {exc}") from exc

    aligned = raw_prices.ffill().dropna(how="all")
    converted = pd.DataFrame(index=aligned.index)
    retained_names: dict[str, str] = {}

    for symbol in aligned.columns:
        currency = stock_currencies.get(symbol, base_currency)
        series = aligned[symbol]

        if currency == base_currency:
            converted[symbol] = series
            retained_names[symbol] = names[symbol]
            continue

        fx_symbol = f"{currency}{base_currency}=X"
        fx_series = fx_prices.get(fx_symbol)
        if fx_series is None:
            failed_tickers.append(symbol)
            continue

        combined = pd.concat([series, fx_series.rename(fx_symbol)], axis=1).ffill().dropna()
        if combined.empty:
            failed_tickers.append(symbol)
            continue

        converted[symbol] = combined[symbol] * combined[fx_symbol]
        retained_names[symbol] = names[symbol]

    converted = converted.ffill().dropna()
    if converted.shape[1] < 2:
        raise RuntimeError("At least two assets with aligned price history are required to build the dashboard.")

    mu = expected_returns.mean_historical_return(converted)
    covariance = risk_models.sample_cov(converted)

    ef = EfficientFrontier(mu, covariance)
    ef.max_sharpe()
    cleaned_weights = {symbol: weight for symbol, weight in ef.clean_weights().items() if weight > 0}
    ret_opt, std_opt, sharpe_opt = ef.portfolio_performance(verbose=False)

    latest_prices = get_latest_prices(converted)
    discrete = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=budget)
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
    min_vol_ret, _, _ = min_vol_frontier.portfolio_performance(verbose=False)
    upper_ret = max(float(mu.max()), float(ret_opt))

    frontier_returns: list[float] = []
    frontier_vols: list[float] = []
    for target_return in np.linspace(min_vol_ret, upper_ret, 40):
        try:
            frontier = EfficientFrontier(mu, covariance)
            frontier.efficient_return(target_return=float(target_return))
            _, volatility, _ = frontier.portfolio_performance(verbose=False)
            frontier_returns.append(float(target_return))
            frontier_vols.append(float(volatility))
        except Exception:
            continue

    if not frontier_returns:
        frontier_returns = [float(ret_opt)]
        frontier_vols = [float(std_opt)]

    return PortfolioBundle(
        price_frame=converted,
        mu=mu,
        covariance=covariance,
        cleaned_weights=cleaned_weights,
        ret_opt=float(ret_opt),
        std_opt=float(std_opt),
        sharpe_opt=float(sharpe_opt),
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
        names=retained_names,
        failed_tickers=sorted(set(failed_tickers)),
        budget=float(budget),
        base_currency=base_currency,
        lookback_months=int(lookback_months),
    )


def calculate_target_portfolio(bundle: PortfolioBundle, target_return_percent: float) -> dict:
    target_return = clip_target_return(bundle, target_return_percent / 100)

    try:
        ef = EfficientFrontier(bundle.mu, bundle.covariance)
        ef.efficient_return(target_return=target_return)
        raw_weights = {symbol: weight for symbol, weight in ef.clean_weights().items() if weight > 0}
        portfolio_return, volatility, sharpe = ef.portfolio_performance(verbose=False)
    except Exception:
        raw_weights = bundle.cleaned_weights
        portfolio_return = bundle.ret_opt
        volatility = bundle.std_opt
        sharpe = bundle.sharpe_opt

    discrete = DiscreteAllocation(raw_weights, bundle.latest_prices, total_portfolio_value=bundle.budget)
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
        "target_return_percent": float(portfolio_return * 100),
        "volatility_percent": float(volatility * 100),
        "sharpe": float(sharpe),
        "leftover": float(leftover),
        "invested_amount": float(actual_total),
        "rows": rows,
    }


def make_efficient_frontier_figure(bundle: PortfolioBundle, target_return_percent: float | None = None) -> go.Figure:
    figure = go.Figure()

    weight_text = [
        "<br>".join(
            [
                f"Return: {portfolio_return * 100:.2f}%",
                f"Risk: {portfolio_risk * 100:.2f}%",
                f"Sharpe: {portfolio_sharpe:.2f}",
                "Top weights:",
                *[
                    f"{bundle.names.get(symbol, symbol)}: {weight * 100:.1f}%"
                    for symbol, weight in sorted(
                        zip(bundle.price_frame.columns, weights),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:4]
                ],
            ]
        )
        for portfolio_return, portfolio_risk, portfolio_sharpe, weights in zip(
            bundle.random_returns,
            bundle.random_stds,
            bundle.random_sharpes,
            bundle.random_weights,
        )
    ]

    figure.add_trace(
        go.Scatter(
            x=bundle.random_stds,
            y=bundle.random_returns,
            mode="markers",
            name="Random portfolios",
            marker={
                "color": bundle.random_sharpes,
                "colorscale": "Viridis",
                "showscale": True,
                "colorbar": {"title": "Sharpe"},
                "size": 5,
                "opacity": 0.55,
            },
            hovertemplate="%{text}<extra></extra>",
            text=weight_text,
        )
    )

    labels = [bundle.names.get(symbol, symbol) for symbol in bundle.price_frame.columns]
    figure.add_trace(
        go.Scatter(
            x=bundle.asset_vols.reindex(bundle.price_frame.columns),
            y=bundle.mu.reindex(bundle.price_frame.columns),
            mode="markers+text",
            name="Individual assets",
            text=labels,
            textposition="middle right",
            marker={"size": 9, "symbol": "x", "color": "#ef4444", "line": {"width": 1}},
            hovertemplate="<b>%{text}</b><br>Return: %{y:.2%}<br>Risk: %{x:.2%}<extra></extra>",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=[bundle.std_opt],
            y=[bundle.ret_opt],
            mode="markers",
            name="Max Sharpe",
            marker={"size": 17, "symbol": "star", "color": "#facc15", "line": {"color": "black", "width": 1}},
            hovertemplate="<b>Optimal portfolio</b><br>Return: %{y:.2%}<br>Risk: %{x:.2%}<extra></extra>",
        )
    )

    if target_return_percent is not None:
        selected = calculate_target_portfolio(bundle, target_return_percent)
        figure.add_trace(
            go.Scatter(
                x=[selected["volatility_percent"] / 100],
                y=[selected["target_return_percent"] / 100],
                mode="markers",
                name="Selected portfolio",
                marker={"size": 13, "symbol": "diamond", "color": "#22d3ee", "line": {"color": "black", "width": 1}},
                hovertemplate="<b>Selected portfolio</b><br>Return: %{y:.2%}<br>Risk: %{x:.2%}<extra></extra>",
            )
        )

    figure.add_trace(
        go.Scatter(
            x=bundle.frontier_vols,
            y=bundle.frontier_returns,
            mode="lines",
            name="Efficient frontier",
            line={"color": "#f97316", "width": 3, "dash": "dot"},
            hoverinfo="skip",
        )
    )

    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title="Efficient frontier",
        xaxis_title="Risk (annual volatility)",
        yaxis_title="Expected return",
        xaxis={"tickformat": ".0%", "gridcolor": "rgba(148,163,184,0.12)"},
        yaxis={"tickformat": ".0%", "gridcolor": "rgba(148,163,184,0.12)"},
        height=620,
        margin={"l": 40, "r": 40, "t": 70, "b": 40},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    )
    return figure


def make_allocation_figure(bundle: PortfolioBundle, target_return_percent: float) -> go.Figure:
    portfolio = calculate_target_portfolio(bundle, target_return_percent)
    frame = pd.DataFrame(portfolio["rows"])

    figure = go.Figure()

    if frame.empty:
        figure.add_annotation(
            text="No allocation available for the selected return.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return figure

    figure.add_trace(
        go.Bar(
            x=frame["label"],
            y=frame["ideal_weight"],
            name="Target weight",
            marker={"color": "rgba(255,255,255,0.10)", "line": {"color": "rgba(255,255,255,0.35)", "width": 1}},
            hoverinfo="skip",
            width=0.8
        )
    )
    figure.add_trace(
        go.Bar(
            x=frame["label"],
            y=frame["actual_weight"],
            name="Actual weight",
            marker={"color": "#14b8a6"},
            customdata=np.stack(
                [frame["shares"], frame["actual_value"], frame["ideal_weight"]],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Shares: %{customdata[0]}<br>"
                f"Cost: %{{customdata[1]:.2f}} {bundle.base_currency}<br>"
                "Actual weight: %{y:.2%}<br>"
                "Target weight: %{customdata[2]:.2%}<extra></extra>"
            ),
            width=0.6
        )
    )

    max_weight = max(frame["ideal_weight"].max(), frame["actual_weight"].max())

    figure.update_layout(
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title="Target return allocation",
        height=620,
        margin={"l": 40, "r": 40, "t": 70, "b": 90},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    )
    figure.update_xaxes(title_text="Assets", tickangle=-30, gridcolor="rgba(148,163,184,0.12)")
    figure.update_yaxes(title_text="Weight", tickformat=".0%", range=[0, max_weight * 1.18], gridcolor="rgba(148,163,184,0.12)")
    return figure


def make_growth_figure(bundle: PortfolioBundle) -> go.Figure:
    normalized = bundle.price_frame / bundle.price_frame.iloc[0]
    order = normalized.iloc[-1].sort_values(ascending=False).index
    normalized = normalized[order]

    figure = go.Figure()
    for symbol in normalized.columns:
        figure.add_trace(
            go.Scatter(
                x=normalized.index,
                y=normalized[symbol],
                mode="lines",
                name=bundle.names.get(symbol, symbol),
                hovertemplate=(
                    "<b>{name}</b><br>%{{y:.2f}}x<extra></extra>".format(
                        name=bundle.names.get(symbol, symbol)
                    )
                ),
            )
        )

    figure.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="white",
        line_width=2,
        opacity=0.65,
    )
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title="Relative growth over time",
        xaxis_title="Date",
        yaxis_title="Growth multiplier",
        xaxis={"gridcolor": "rgba(148,163,184,0.12)"},
        yaxis={"gridcolor": "rgba(148,163,184,0.12)"},
        hovermode="x unified",
        hoverlabel={
            "bgcolor": "rgba(0,0,0,0.85)",
            "font": {"color": "white", "family": "Inter, DejaVu Sans, Arial", "size": 12},
        },
        height=620,
        margin={"l": 40, "r": 40, "t": 70, "b": 40},
        legend={"orientation": "v", "y": 1, "x": 1.02, "xanchor": "left", "yanchor": "top"},
    )
    return figure


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
