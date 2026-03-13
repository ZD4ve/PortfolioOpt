from __future__ import annotations

import os

from dash import Dash, Input, Output, dash_table, dcc, html

from portfolio_dash.portfolio_service import (
    DEFAULT_BUDGET,
    DEFAULT_LOOKBACK_MONTHS,
    PortfolioBundle,
    allocation_table_rows,
    load_portfolio_bundle,
    make_allocation_figure,
    make_efficient_frontier_figure,
    make_growth_figure,
    summary_cards,
    supported_symbol_notes,
)

EXTERNAL_STYLESHEETS: list[str | dict[str, object]] = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
]

# ── DataTable styles ──────────────────────────────────────────────────────────
TABLE_STYLE_HEADER = {
    "backgroundColor": "#0f172a",
    "color": "#94a3b8",
    "fontWeight": 600,
    "fontSize": "0.72rem",
    "letterSpacing": "0.07em",
    "textTransform": "uppercase",
    "border": "none",
    "borderBottom": "1px solid rgba(148,163,184,0.20)",
    "padding": "10px 14px",
}
TABLE_STYLE_CELL = {
    "backgroundColor": "rgba(15,23,42,0.0)",
    "color": "#cbd5e1",
    "border": "none",
    "borderBottom": "1px solid rgba(148,163,184,0.08)",
    "padding": "11px 14px",
    "fontSize": "0.875rem",
    "fontFamily": "Inter, sans-serif",
    "textAlign": "left",
}
TABLE_STYLE_DATA_CONDITIONAL = [
    {"if": {"row_index": "odd"}, "backgroundColor": "rgba(30,41,59,0.25)"},
]

app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS, title="Portfolio Dash")
server = app.server


class DataState:
    bundle: PortfolioBundle | None = None
    error: str | None = None


STATE = DataState()


def refresh_data() -> None:
    try:
        STATE.bundle = load_portfolio_bundle(
            budget=DEFAULT_BUDGET,
            lookback_months=DEFAULT_LOOKBACK_MONTHS,
        )
        STATE.error = None
    except Exception as exc:
        STATE.bundle = None
        STATE.error = str(exc)


refresh_data()


def slider_bounds(bundle: PortfolioBundle | None) -> tuple[float, float, float]:
    if bundle is None:
        return 4.0, 18.0, 8.0

    slider_min = round(min(bundle.frontier_returns) * 100, 1)
    slider_max = round(max(bundle.frontier_returns) * 100, 1)
    slider_value = round(bundle.ret_opt * 100, 1)
    return slider_min, slider_max, slider_value


def card_grid(cards: list[dict[str, str]]) -> html.Div:
    """Render KPI summary cards in a 6-column responsive grid."""
    return html.Div(
        className="kpi-grid",
        children=[
            html.Div(
                className=f"card-hover card small-card",
                style={"display": "flex", "flexDirection": "column", "gap": "4px"},
                children=[
                    html.Div(
                        card["label"],
                        style={
                            "fontSize": "0.72rem",
                            "color": "#64748b",
                            "textTransform": "uppercase",
                            "letterSpacing": "0.06em",
                        },
                    ),
                    html.Div(
                        card["value"],
                        style={"fontSize": "1.45rem", "fontWeight": 700, "color": "#f1f5f9"},
                    ),
                ],
            )
            for card in cards
        ],
    )


def build_layout() -> html.Div:
    slider_min, slider_max, slider_value = slider_bounds(STATE.bundle)
    cards = summary_cards(STATE.bundle, slider_value) if STATE.bundle else []
    efficient_figure = make_efficient_frontier_figure(STATE.bundle, slider_value) if STATE.bundle else {}
    allocation_figure = make_allocation_figure(STATE.bundle, slider_value) if STATE.bundle else {}
    growth_figure = make_growth_figure(STATE.bundle) if STATE.bundle else {}
    table_rows = allocation_table_rows(STATE.bundle, slider_value) if STATE.bundle else []

    return html.Div(
        className="page",
        children=[
            html.Div(
                className="inner",
                children=[

                    # ── ROW 0: Hero ───────────────────────────────────────────
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "24px",
                            "alignItems": "flex-start",
                            "flexWrap": "wrap",
                            "marginBottom": "28px",
                        },
                        children=[
                            html.Div(
                                style={"flex": "1", "minWidth": "360px"},
                                children=[
                                    html.Div(
                                        "Portfolio Optimiser",
                                        style={
                                            "fontSize": "0.72rem",
                                            "fontWeight": 600,
                                            "letterSpacing": "0.10em",
                                            "textTransform": "uppercase",
                                            "color": "#38bdf8",
                                            "marginBottom": "10px",
                                        },
                                    ),
                                    html.H1(
                                        "Efficient frontier dashboard",
                                        style={
                                            "fontSize": "2.25rem",
                                            "fontWeight": 700,
                                            "lineHeight": 1.2,
                                            "color": "#f1f5f9",
                                            "margin": "0 0 12px",
                                        },
                                    ),
                                    html.P(
                                        "Explore the efficient frontier, pick a target return, and get a share-exact discrete allocation for your budget.",
                                        style={
                                            "margin": 0,
                                            "fontSize": "0.95rem",
                                            "color": "#94a3b8",
                                            "lineHeight": 1.65,
                                        },
                                    ),
                                ],
                            ),
                            html.Div(
                                className=f"card-hover card",
                                style={"minWidth": "320px", "maxWidth": "420px", "flexShrink": "0"},
                                children=[
                                    html.Div(
                                        "Universe notes",
                                        style={"fontWeight": 700, "fontSize": "0.875rem", "color": "#f1f5f9", "marginBottom": "10px"},
                                    ),
                                    html.Ul(
                                        [html.Li(note, style={"marginBottom": "6px"}) for note in supported_symbol_notes()],
                                        style={
                                            "margin": 0,
                                            "paddingLeft": "18px",
                                            "color": "#cbd5e1",
                                            "fontSize": "0.825rem",
                                            "lineHeight": 1.6,
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # ── ROW 1: KPI bar ────────────────────────────────────────
                    html.Div(id="summary-cards", children=card_grid(cards) if cards else None),

                    # ── ROW 2: Charts A — Frontier + Growth side by side ──────
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "20px",
                            "alignItems": "stretch",
                            "flexWrap": "wrap",
                            "marginBottom": "20px",
                        },
                        children=[
                            # Efficient frontier panel (~55%)
                            html.Div(
                                className="card-accent-top card",
                                style={"flex": "11 1 0", "minWidth": "520px"},
                                children=[
                                    html.Div("Efficient frontier", className="section-label"),
                                    dcc.Graph(
                                        id="frontier-graph",
                                        figure=efficient_figure,
                                        config={"displaylogo": False, "responsive": True},
                                        style={"height": "700px"},
                                    ),
                                ],
                            ),
                            # Historical growth panel (~45%)
                            html.Div(
                                className="card-accent-top card",
                                style={"flex": "9 1 0", "minWidth": "460px"},
                                children=[
                                    html.Div("Historical growth", className="section-label"),
                                    dcc.Graph(
                                        id="growth-graph",
                                        figure=growth_figure,
                                        config={"displaylogo": False, "responsive": True},
                                        style={"height": "700px"},
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # ── ROW 3: Slider control strip ───────────────────────────
                    html.Div(
                        className="slider-strip",
                        children=[
                            html.Div(
                                style={"flex": "3", "minWidth": "180px"},
                                children=[
                                    html.Div(
                                        "Target return",
                                        style={"fontSize": "0.95rem", "fontWeight": 600, "color": "#f1f5f9"},
                                    ),
                                    html.Div(
                                        "Move the slider to rebuild the discrete allocation.",
                                        style={"fontSize": "0.80rem", "color": "#64748b", "marginTop": "4px"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"flex": "7", "display": "flex", "flexDirection": "column", "gap": "6px"},
                                children=[
                                    dcc.Slider(
                                        id="return-slider",
                                        min=slider_min,
                                        max=slider_max,
                                        step=0.1,
                                        value=slider_value,
                                        tooltip={"placement": "bottom", "always_visible": True},
                                        marks={
                                            slider_min: f"{slider_min:.1f}%",
                                            round((slider_min + slider_max) / 2, 1): f"{round((slider_min + slider_max) / 2, 1):.1f}%",
                                            slider_max: f"{slider_max:.1f}%",
                                        },
                                    ),
                                    html.Div(
                                        id="load-status",
                                        style={
                                            "fontSize": "0.75rem",
                                            "color": "#fca5a5" if STATE.error else "#93c5fd",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # ── ROW 4: Charts B — Allocation chart + Table side by side
                    dcc.Loading(
                        id="loading-allocation",
                        type="circle",
                        color="#38bdf8",
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "gap": "20px",
                                    "alignItems": "stretch",
                                    "flexWrap": "wrap",
                                },
                                children=[
                                    # Allocation bar chart (50%)
                                    html.Div(
                                        className="card-accent-top card",
                                        style={"flex": "1 1 0", "minWidth": "460px"},
                                        children=[
                                            html.Div("Target return allocation", className="section-label"),
                                            dcc.Graph(
                                                id="allocation-graph",
                                                figure=allocation_figure,
                                                config={"displaylogo": False, "responsive": True},
                                                style={"height": "520px"},
                                            ),
                                        ],
                                    ),
                                    # Discrete allocation table (50%)
                                    html.Div(
                                        className="card",
                                        style={
                                            "flex": "1 1 0",
                                            "minWidth": "460px",
                                            "display": "flex",
                                            "flexDirection": "column",
                                        },
                                        children=[
                                            html.Div(
                                                "Discrete allocation",
                                                className="section-label",
                                                style={"marginBottom": "14px"},
                                            ),
                                            dash_table.DataTable(
                                                id="allocation-table",
                                                data=table_rows,
                                                columns=[{"name": n, "id": n} for n in ["Asset", "Shares", "Target Weight", "Actual Weight", "Cost"]],
                                                style_as_list_view=True,
                                                style_table={"overflowX": "auto", "overflowY": "auto", "maxHeight": "520px"},
                                                style_header=TABLE_STYLE_HEADER,
                                                style_cell=TABLE_STYLE_CELL,
                                                style_data_conditional=TABLE_STYLE_DATA_CONDITIONAL,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),

                ],
            ),
        ],
    )


app.layout = build_layout


@app.callback(
    Output("summary-cards", "children"),
    Output("frontier-graph", "figure"),
    Output("allocation-graph", "figure"),
    Output("allocation-table", "data"),
    Output("load-status", "children"),
    Input("return-slider", "value"),
)
def update_allocation(target_return: float):
    if STATE.bundle is None:
        return None, {}, {}, [], f"Market data is unavailable: {STATE.error}"

    cards = card_grid(summary_cards(STATE.bundle, target_return))
    frontier_figure = make_efficient_frontier_figure(STATE.bundle, target_return)
    figure = make_allocation_figure(STATE.bundle, target_return)
    rows = allocation_table_rows(STATE.bundle, target_return)

    status_bits = [
        f"Loaded {STATE.bundle.price_frame.shape[1]} assets over {STATE.bundle.lookback_months} months.",
    ]
    if STATE.bundle.failed_tickers:
        status_bits.append("Skipped: " + ", ".join(STATE.bundle.failed_tickers))

    return cards, frontier_figure, figure, rows, " ".join(status_bits)
