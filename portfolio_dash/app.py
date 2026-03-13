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

EXTERNAL_STYLESHEETS = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
]
CARD_STYLE = {
    "background": "linear-gradient(180deg, rgba(30,41,59,0.96), rgba(15,23,42,0.96))",
    "border": "1px solid rgba(148,163,184,0.16)",
    "borderRadius": "18px",
    "boxShadow": "0 12px 40px rgba(15,23,42,0.35)",
    "padding": "18px 20px",
}
PAGE_STYLE = {
    "fontFamily": "Inter, sans-serif",
    "background": "radial-gradient(circle at top, #172554, #020617 62%)",
    "minHeight": "100vh",
    "color": "#e2e8f0",
    "padding": "32px 32px 48px",
}
INNER_STYLE = {
    "maxWidth": "1400px",
    "margin": "0 auto",
}
SECTION_LABEL_STYLE = {
    "fontSize": "0.78rem",
    "fontWeight": 600,
    "letterSpacing": "0.10em",
    "textTransform": "uppercase",
    "color": "#38bdf8",
    "marginBottom": "10px",
}

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
    return html.Div(
        [
            html.Div(
                [
                    html.Div(card["label"], style={"fontSize": "0.85rem", "color": "#94a3b8", "marginBottom": "8px"}),
                    html.Div(card["value"], style={"fontSize": "1.4rem", "fontWeight": 700}),
                ],
                style={
                    **CARD_STYLE,
                    "padding": "16px 18px",
                },
            )
            for card in cards
        ],
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
            "gap": "14px",
        },
    )


def build_layout() -> html.Div:
    slider_min, slider_max, slider_value = slider_bounds(STATE.bundle)
    cards = summary_cards(STATE.bundle, slider_value) if STATE.bundle else []
    efficient_figure = make_efficient_frontier_figure(STATE.bundle, slider_value) if STATE.bundle else {}
    allocation_figure = make_allocation_figure(STATE.bundle, slider_value) if STATE.bundle else {}
    growth_figure = make_growth_figure(STATE.bundle) if STATE.bundle else {}
    table_rows = allocation_table_rows(STATE.bundle, slider_value) if STATE.bundle else []

    return html.Div(
        [html.Div(
            [
                # Hero
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Portfolio Optimiser", style={"fontSize": "0.95rem", "color": "#38bdf8", "fontWeight": 600}),
                                html.H1("Efficient frontier dashboard", style={"margin": "8px 0 10px", "fontSize": "2.4rem"}),
                                html.P(
                                    "Explore the efficient frontier, pick a target return, and get a share-exact discrete allocation for your budget.",
                                    style={"margin": 0, "maxWidth": "880px", "color": "#cbd5e1", "lineHeight": 1.6},
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Div("Universe notes", style={"fontWeight": 700, "marginBottom": "8px"}),
                                html.Ul(
                                    [html.Li(note) for note in supported_symbol_notes()],
                                    style={"margin": 0, "paddingLeft": "18px", "color": "#cbd5e1"},
                                ),
                            ],
                            style={**CARD_STYLE, "maxWidth": "430px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "18px", "justifyContent": "space-between", "alignItems": "stretch", "flexWrap": "wrap"},
                ),

                html.Div(style={"height": "22px"}),

                # Summary KPI cards
                html.Div(id="summary-cards", children=card_grid(cards) if cards else None),

                html.Div(style={"height": "32px"}),

                # Efficient frontier
                html.Div("Efficient frontier", style=SECTION_LABEL_STYLE),
                html.Div(
                    dcc.Graph(id="frontier-graph", figure=efficient_figure, config={"displaylogo": False}),
                    style=CARD_STYLE,
                ),

                html.Div(style={"height": "32px"}),

                # Historical growth
                html.Div("Historical growth", style=SECTION_LABEL_STYLE),
                html.Div(
                    dcc.Graph(id="growth-graph", figure=growth_figure, config={"displaylogo": False}),
                    style=CARD_STYLE,
                ),

                html.Div(style={"height": "32px"}),

                # Return slider
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Target return", style={"fontWeight": 700, "fontSize": "1rem", "marginBottom": "8px"}),
                                html.Div(
                                    "Move the slider to rebuild the discrete allocation around a chosen point on the efficient frontier.",
                                    style={"color": "#cbd5e1", "marginBottom": "12px"},
                                ),
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
                                html.Div(id="load-status", style={"marginTop": "16px", "color": "#fca5a5" if STATE.error else "#93c5fd"}),
                            ],
                            style=CARD_STYLE,
                        ),
                    ]
                ),

                html.Div(style={"height": "32px"}),

                # Target-return allocation (reactive)
                html.Div("Target return allocation", style=SECTION_LABEL_STYLE),
                dcc.Loading(
                    id="loading-allocation",
                    type="circle",
                    color="#38bdf8",
                    children=[
                        html.Div(
                            dcc.Graph(id="allocation-graph", figure=allocation_figure, config={"displaylogo": False}),
                            style=CARD_STYLE,
                        ),
                        html.Div(style={"height": "22px"}),
                        html.Div(
                            [
                                html.Div("Discrete allocation", style={"fontWeight": 700, "fontSize": "1rem", "marginBottom": "12px"}),
                                dash_table.DataTable(
                                    id="allocation-table",
                                    data=table_rows,
                                    columns=[{"name": name, "id": name} for name in ["Asset", "Shares", "Target Weight", "Actual Weight", "Cost"]],
                                    style_as_list_view=True,
                                    style_table={"overflowX": "auto"},
                                    style_header={"backgroundColor": "#0f172a", "color": "#e2e8f0", "fontWeight": 700, "border": "none"},
                                    style_cell={"backgroundColor": "#020617", "color": "#cbd5e1", "border": "none", "padding": "12px", "textAlign": "left"},
                                    style_data={"borderBottom": "1px solid rgba(148,163,184,0.12)"},
                                ),
                            ],
                            style=CARD_STYLE,
                        ),
                    ],
                ),
            ],
            style=INNER_STYLE,
        )],
        style=PAGE_STYLE,
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
