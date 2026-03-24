from __future__ import annotations

import os

from dash import Dash, Input, Output, dash_table, dcc, html

from portfolio_dash.models import PortfolioBundle
from portfolio_dash.optimization import (
    DEFAULT_BUDGET,
    DEFAULT_LOOKBACK_MONTHS,
    allocation_table_rows,
    load_portfolio_bundle,
    summary_cards,
    supported_symbol_notes,
)
from portfolio_dash.plots import (
    make_allocation_figure,
    make_efficient_frontier_figure,
    make_growth_figure,
)

EXTERNAL_STYLESHEETS: list[str | dict[str, object]] = [
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap",
]

# ── Archival palette ──────────────────────────────────────────────────────────
PARCHMENT_CREAM = "#ede2c2"
MUTED_PARCHMENT = "#f5edd8"
AGED_TERRACOTTA = "#d97b4a"
CALM_SAGE = "#88a99f"
VINTAGE_MUSTARD = "#d8a62b"
ARCHIVAL_INDIGO = "#2f3b4c"
EVOLUTIONARY_GREEN = "#4e8c5d"
BORDER_TINT = "rgba(47, 59, 76, 0.22)"

# ── DataTable styles ──────────────────────────────────────────────────────────
TABLE_STYLE_HEADER = {
    "backgroundColor": MUTED_PARCHMENT,
    "color": ARCHIVAL_INDIGO,
    "fontWeight": 600,
    "fontSize": "0.72rem",
    "letterSpacing": "0.14em",
    "textTransform": "uppercase",
    "border": f"1px solid {BORDER_TINT}",
    "padding": "12px 14px",
    "fontFamily": "IBM Plex Sans, sans-serif",
}
TABLE_STYLE_CELL = {
    "backgroundColor": PARCHMENT_CREAM,
    "color": ARCHIVAL_INDIGO,
    "border": f"1px solid {BORDER_TINT}",
    "padding": "11px 14px",
    "fontSize": "0.84rem",
    "fontFamily": "IBM Plex Mono, monospace",
    "textAlign": "left",
    "lineHeight": "1.5",
}
TABLE_STYLE_DATA_CONDITIONAL = [
    {"if": {"row_index": "odd"}, "backgroundColor": "#e7dcc0"},
]

app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS, title="The archival ledger")
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


def metric_stack(cards: list[dict[str, str]]) -> html.Div:
    """Render KPI summary cards as an archival ledger stack."""
    return html.Div(
        className="metric-stack",
        children=[
            html.Div(
                className="metric-row",
                children=[
                    html.Div(
                        card["label"],
                        className="metric-label",
                    ),
                    html.Div(
                        card["value"],
                        className="metric-value",
                    ),
                ],
            )
            for card in cards
        ],
    )


def diagram_index() -> html.Div:
    sections = [
        ("Frontier register", "frontier-section"),
        ("Historical growth", "growth-section"),
        ("Allocation strata", "allocation-section"),
        ("Discrete ledger", "table-section"),
    ]
    return html.Div(
        className="sidebar-block",
        children=[
            html.Div("Diagram register", className="sidebar-label"),
            html.Div(
                className="diagram-index",
                children=[
                    html.A(label, href=f"#{target}", className="diagram-index-link")
                    for label, target in sections
                ],
            ),
        ],
    )


def diagram_panel(
    panel_id: str,
    eyebrow: str,
    title: str,
    note: str,
    child: html.Div | dcc.Graph | dash_table.DataTable,
) -> html.Section:
    return html.Section(
        id=panel_id,
        className="diagram-panel",
        children=[
            html.Div(
                className="panel-header",
                children=[
                    html.Div(eyebrow, className="panel-eyebrow"),
                    html.H2(title, className="panel-title"),
                    html.P(note, className="panel-note"),
                ],
            ),
            child,
        ],
    )


def initial_status_text(bundle: PortfolioBundle | None) -> str:
    if bundle is None:
        return f"Market data is unavailable: {STATE.error}"

    status_bits = [
        f"Prepared {bundle.price_frame.shape[1]} assets across {bundle.lookback_months} months.",
    ]
    if bundle.failed_tickers:
        status_bits.append("Omitted: " + ", ".join(bundle.failed_tickers))
    return " ".join(status_bits)


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
                className="dashboard-shell",
                children=[
                    html.Aside(
                        className="ledger-sidebar",
                        children=[
                            html.Div(
                                className="sidebar-frame",
                                children=[
                                    html.Img(src="/assets/portfolio-icon.png", className="sidebar-logo"),
                                    html.Div("Portfolio optimiser", className="sidebar-eyebrow"),
                                    html.H1("The archival ledger", className="sidebar-title"),
                                    html.P(
                                        "A dashboard for reading efficient frontier structure, relative growth, and discrete allocation.",
                                        className="sidebar-intro",
                                    ),
                                    html.Div(
                                        className="sidebar-block",
                                        children=[
                                            html.Div("Portfolio brief", className="sidebar-label"),
                                            html.Div(id="summary-cards", children=metric_stack(cards) if cards else None),
                                        ],
                                    ),
                                    diagram_index(),
                                    html.Div(
                                        className="sidebar-block",
                                        children=[
                                            html.Div("Target return", className="sidebar-label"),
                                            html.P(
                                                "Adjust the mechanical control to rebuild the discrete ledger against the efficient frontier.",
                                                className="sidebar-copy",
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
                                            html.Div(
                                                id="load-status",
                                                className="status-text" if not STATE.error else "status-text is-error",
                                                children=initial_status_text(STATE.bundle),
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="sidebar-block",
                                        children=[
                                            html.Div("Universe notes", className="sidebar-label"),
                                            html.Ul(
                                                [html.Li(note) for note in supported_symbol_notes()],
                                                className="notes-list",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Main(
                        className="diagram-column",
                        children=[
                            html.Div(
                                className="diagram-scroll",
                                children=[
                                    diagram_panel(
                                        "frontier-section",
                                        "Diagram I",
                                        "Efficient frontier register",
                                        "Read the full opportunity set, with the selected allocation pinned directly onto the frontier.",
                                        dcc.Graph(
                                            id="frontier-graph",
                                            figure=efficient_figure,
                                            config={"displaylogo": False, "responsive": True},
                                            className="diagram-graph diagram-graph-tall",
                                        ),
                                    ),
                                    diagram_panel(
                                        "growth-section",
                                        "Diagram II",
                                        "Historical growth strata",
                                        "Stepped traces turn the observation window into a quiet comparative record of compounded movement.",
                                        dcc.Graph(
                                            id="growth-graph",
                                            figure=growth_figure,
                                            config={"displaylogo": False, "responsive": True},
                                            className="diagram-graph diagram-graph-tall",
                                        ),
                                    ),
                                    dcc.Loading(
                                        id="loading-allocation",
                                        type="circle",
                                        color=AGED_TERRACOTTA,
                                        children=[
                                            html.Div(
                                                className="diagram-grid",
                                                children=[
                                                    diagram_panel(
                                                        "allocation-section",
                                                        "Diagram III",
                                                        "Allocation strata",
                                                        "Target and actual weights are layered as calibrated blocks rather than glossy bars.",
                                                        dcc.Graph(
                                                            id="allocation-graph",
                                                            figure=allocation_figure,
                                                            config={"displaylogo": False, "responsive": True},
                                                            className="diagram-graph diagram-graph-medium",
                                                        ),
                                                    ),
                                                    diagram_panel(
                                                        "table-section",
                                                        "Diagram IV",
                                                        "Discrete ledger",
                                                        "The share-exact allocation is set in a monospaced ledger for slower, deliberate reading.",
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
            ),
        ],
    )


app.layout = build_layout


@app.callback(
    Output("summary-cards", "children"),
    Output("allocation-graph", "figure"),
    Output("allocation-table", "data"),
    Output("load-status", "children"),
    Input("return-slider", "value"),
)
def update_allocation(target_return: float):
    if STATE.bundle is None:
        return None, {}, [], f"Market data is unavailable: {STATE.error}"

    cards = metric_stack(summary_cards(STATE.bundle, target_return))
    figure = make_allocation_figure(STATE.bundle, target_return)
    rows = allocation_table_rows(STATE.bundle, target_return)

    status_bits = [
        f"Prepared {STATE.bundle.price_frame.shape[1]} assets across {STATE.bundle.lookback_months} months.",
    ]
    if STATE.bundle.failed_tickers:
        status_bits.append("Omitted: " + ", ".join(STATE.bundle.failed_tickers))

    return cards, figure, rows, " ".join(status_bits)
