from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .models import PortfolioBundle
from .optimization import calculate_target_portfolio
from .theme import (
    AGED_TERRACOTTA,
    ARCHIVAL_INDIGO,
    CALM_SAGE,
    EVOLUTIONARY_GREEN,
    FRAME_COLOR,
    MUTED_PARCHMENT,
    PARCHMENT_CREAM,
    PLOT_SEQUENCE,
    VINTAGE_MUSTARD,
    apply_archival_theme,
)


def make_efficient_frontier_figure(bundle: PortfolioBundle, target_return_percent: float | None = None) -> go.Figure:
    figure = go.Figure()

    figure.add_trace(
        go.Scattergl(
            x=bundle.random_stds,
            y=bundle.random_returns,
            mode="markers",
            name="Random portfolios",
            marker={
                "color": bundle.random_sharpes,
                "colorscale": [
                    [0.0, PARCHMENT_CREAM],
                    [0.35, CALM_SAGE],
                    [0.68, AGED_TERRACOTTA],
                    [1.0, ARCHIVAL_INDIGO],
                ],
                "showscale": True,
                "colorbar": {
                    "title": {"text": "Sharpe", "font": {"color": ARCHIVAL_INDIGO}},
                    "outlinecolor": FRAME_COLOR,
                    "tickfont": {"color": ARCHIVAL_INDIGO},
                    "bgcolor": PARCHMENT_CREAM,
                },
                "size": 5,
                "opacity": 0.75,
                "line": {"width": 0.4, "color": FRAME_COLOR},
            },
            hovertemplate="Return: %{y:.2%}<br>Risk: %{x:.2%}<br>Sharpe: %{marker.color:.2f}<extra></extra>",
        )
    )

    labels = [bundle.names.get(symbol, symbol) for symbol in bundle.price_frame.columns]
    figure.add_trace(
        go.Scattergl(
            x=bundle.asset_vols.reindex(bundle.price_frame.columns),
            y=bundle.mu.reindex(bundle.price_frame.columns),
            mode="markers+text",
            name="Individual assets",
            text=labels,
            textposition="middle right",
            marker={"size": 10, "symbol": "diamond-open", "color": AGED_TERRACOTTA, "line": {"width": 1.2, "color": ARCHIVAL_INDIGO}},
            textfont={"color": ARCHIVAL_INDIGO, "size": 10},
            hovertemplate="<b>%{text}</b><br>Return: %{y:.2%}<br>Risk: %{x:.2%}<extra></extra>",
        )
    )

    figure.add_trace(
        go.Scattergl(
            x=[bundle.std_opt],
            y=[bundle.ret_opt],
            mode="markers",
            name="Max Sharpe",
            marker={"size": 17, "symbol": "star", "color": VINTAGE_MUSTARD, "line": {"color": ARCHIVAL_INDIGO, "width": 1.2}},
            hovertemplate="<b>Optimal portfolio</b><br>Return: %{y:.2%}<br>Risk: %{x:.2%}<extra></extra>",
        )
    )

    if target_return_percent is not None:
        selected = calculate_target_portfolio(bundle, target_return_percent)
        figure.add_trace(
            go.Scattergl(
                x=[selected["volatility_percent"] / 100],
                y=[selected["target_return_percent"] / 100],
                mode="markers",
                name="Selected portfolio",
                marker={"size": 14, "symbol": "diamond", "color": EVOLUTIONARY_GREEN, "line": {"color": ARCHIVAL_INDIGO, "width": 1.2}},
                hovertemplate="<b>Selected portfolio</b><br>Return: %{y:.2%}<br>Risk: %{x:.2%}<extra></extra>",
            )
        )

    figure.add_trace(
        go.Scattergl(
            x=bundle.frontier_vols,
            y=bundle.frontier_returns,
            mode="lines",
            name="Efficient frontier",
            line={"color": ARCHIVAL_INDIGO, "width": 3, "dash": "dash"},
            hoverinfo="skip",
        )
    )

    apply_archival_theme(
        figure,
        title="Efficient frontier",
        height=700,
        margin={"l": 48, "r": 32, "t": 76, "b": 44},
    )
    figure.update_xaxes(title_text="Risk (annual volatility)", tickformat=".0%")
    figure.update_yaxes(title_text="Expected return", tickformat=".0%")
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
            marker={"color": CALM_SAGE, "opacity": 0.42, "line": {"color": ARCHIVAL_INDIGO, "width": 1}},
            hoverinfo="skip",
            width=0.8,
        )
    )
    figure.add_trace(
        go.Bar(
            x=frame["label"],
            y=frame["actual_weight"],
            name="Actual weight",
            marker={"color": AGED_TERRACOTTA, "line": {"color": ARCHIVAL_INDIGO, "width": 0.8}},
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
            width=0.6,
        )
    )

    max_weight = max(frame["ideal_weight"].max(), frame["actual_weight"].max())

    apply_archival_theme(
        figure,
        title="Target return allocation",
        height=520,
        margin={"l": 48, "r": 24, "t": 76, "b": 120},
    )
    figure.update_layout(barmode="overlay")
    figure.update_xaxes(title_text="Assets", tickangle=-28)
    figure.update_yaxes(title_text="Weight", tickformat=".0%", range=[0, max_weight * 1.18])
    return figure


def make_growth_figure(bundle: PortfolioBundle) -> go.Figure:
    normalized = bundle.price_frame / bundle.price_frame.iloc[0]

    # Resample to weekly to reduce DOM elements while preserving the "stepped" look.
    normalized = normalized.resample("W").last().ffill()

    order = normalized.iloc[-1].sort_values(ascending=False).index
    normalized = normalized[order]

    figure = go.Figure()
    for index, symbol in enumerate(normalized.columns):
        figure.add_trace(
            go.Scattergl(
                x=normalized.index,
                y=normalized[symbol],
                mode="lines",
                name=bundle.names.get(symbol, symbol),
                line={"width": 1.8, "shape": "hv", "color": PLOT_SEQUENCE[index % len(PLOT_SEQUENCE)]},
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
        line_color=ARCHIVAL_INDIGO,
        line_width=2,
        opacity=0.65,
    )
    apply_archival_theme(
        figure,
        title="Relative growth over time",
        height=700,
        margin={"l": 48, "r": 250, "t": 76, "b": 40},
        legend={
            "orientation": "v",
            "y": 1,
            "x": 1.02,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 10, "color": ARCHIVAL_INDIGO},
        },
        hovermode="x unified",
    )
    figure.update_xaxes(title_text="Date")
    figure.update_yaxes(title_text="Growth multiplier")
    return figure
