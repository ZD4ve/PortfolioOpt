from __future__ import annotations

import plotly.graph_objects as go

PARCHMENT_CREAM = "#ede2c2"
MUTED_PARCHMENT = "#f5edd8"
AGED_TERRACOTTA = "#d97b4a"
CALM_SAGE = "#88a99f"
VINTAGE_MUSTARD = "#d8a62b"
ARCHIVAL_INDIGO = "#2f3b4c"
EVOLUTIONARY_GREEN = "#4e8c5d"
GRID_COLOR = "rgba(47, 59, 76, 0.16)"
FRAME_COLOR = "rgba(47, 59, 76, 0.38)"
PLOT_SEQUENCE = [
    AGED_TERRACOTTA,
    CALM_SAGE,
    EVOLUTIONARY_GREEN,
    VINTAGE_MUSTARD,
    ARCHIVAL_INDIGO,
    "#b38b73",
    "#6e7b86",
]


def apply_archival_theme(
    figure: go.Figure,
    *,
    title: str,
    height: int,
    margin: dict[str, int],
    legend: dict | None = None,
    hovermode: str | None = None,
) -> go.Figure:
    figure.update_layout(
        template="none",
        paper_bgcolor=PARCHMENT_CREAM,
        plot_bgcolor=MUTED_PARCHMENT,
        colorway=PLOT_SEQUENCE,
        font={"family": "IBM Plex Sans, Inter, Arial, sans-serif", "color": ARCHIVAL_INDIGO, "size": 13},
        title={
            "text": title,
            "x": 0.01,
            "xanchor": "left",
            "font": {"family": "IBM Plex Sans, Inter, Arial, sans-serif", "size": 20, "color": ARCHIVAL_INDIGO},
        },
        height=height,
        margin=margin,
        hovermode=hovermode,
        legend=legend
        or {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 0,
            "font": {"size": 11, "color": ARCHIVAL_INDIGO},
        },
        hoverlabel={
            "bgcolor": MUTED_PARCHMENT,
            "bordercolor": ARCHIVAL_INDIGO,
            "font": {"family": "IBM Plex Mono, monospace", "color": ARCHIVAL_INDIGO, "size": 12},
        },
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        showline=True,
        linecolor=FRAME_COLOR,
        mirror=False,
        tickcolor=ARCHIVAL_INDIGO,
        ticks="outside",
        title_font={"size": 12, "color": ARCHIVAL_INDIGO},
        tickfont={"size": 11, "color": ARCHIVAL_INDIGO},
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        showline=True,
        linecolor=FRAME_COLOR,
        mirror=False,
        tickcolor=ARCHIVAL_INDIGO,
        ticks="outside",
        title_font={"size": 12, "color": ARCHIVAL_INDIGO},
        tickfont={"size": 11, "color": ARCHIVAL_INDIGO},
    )
    return figure
