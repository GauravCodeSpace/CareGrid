"""
CareGrid AI — Chart Factory
=============================
Reusable Plotly chart factory with healthcare-themed styling.
All chart functions return ``plotly.graph_objects.Figure``
(except ``create_kpi_metric`` which returns an HTML string).

Usage:
    from utils.charts import create_line_chart, create_kpi_metric
    fig = create_line_chart(df, x='date', y='value', title='Trend')
    html = create_kpi_metric('Active Alerts', 12, delta=3, delta_positive=False)
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go

from config.constants import Colors

# ── Color palette for multi-series charts ────────────────────
CHART_COLORS: list[str] = [
    Colors.PRIMARY,
    Colors.SUCCESS,
    Colors.WARNING,
    Colors.DANGER,
    "#8B5CF6",   # Violet
    "#EC4899",   # Pink
    "#14B8A6",   # Teal
    "#F97316",   # Orange
    "#6366F1",   # Indigo
    "#06B6D4",   # Cyan
]


# ============================================================
# HEALTHCARE THEME
# ============================================================

def apply_healthcare_theme(fig: go.Figure) -> go.Figure:
    """
    Apply a consistent healthcare-themed layout to any Plotly figure.

    Args:
        fig: Plotly figure to style.

    Returns:
        The same figure with updated layout.
    """
    fig.update_layout(
        font=dict(family="Inter, sans-serif", color="#000000", size=13),
        paper_bgcolor=Colors.SURFACE,
        plot_bgcolor=Colors.SURFACE,
        margin=dict(l=50, r=30, t=60, b=50),
        title_font=dict(size=16, color="#000000", family="Inter, sans-serif"),
        title_x=0.0,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0)",
            borderwidth=0,
            font=dict(size=11, color="#000000"),
        ),
        hoverlabel=dict(
            bgcolor=Colors.SURFACE,
            font_size=12,
            font_family="Inter, sans-serif",
            bordercolor=Colors.BORDER,
        ),
        # Remove Plotly watermark / mode-bar clutter
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=Colors.TEXT_SECONDARY),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#cbd5e1",
        gridwidth=1,
        zeroline=False,
        linecolor="#cbd5e1",
        title_font=dict(color="#000000", size=12),
        tickfont=dict(size=11, color="#000000"),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#cbd5e1",
        gridwidth=1,
        zeroline=False,
        linecolor="#cbd5e1",
        title_font=dict(color="#000000", size=12),
        tickfont=dict(size=11, color="#000000"),
    )
    return fig


# ============================================================
# KPI METRIC CARD (HTML)
# ============================================================

def create_kpi_metric(
    label: str,
    value: str | int | float,
    delta: str | int | float | None = None,
    delta_positive: bool = True,
) -> str:
    """
    Return an HTML string for a styled KPI card.

    Args:
        label: KPI label text.
        value: Primary metric value.
        delta: Change indicator (e.g. +5 or -2.3%).
        delta_positive: Whether the delta is a positive signal.

    Returns:
        HTML string suitable for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    delta_color = Colors.SUCCESS if delta_positive else Colors.DANGER
    arrow = "▲" if delta_positive else "▼"

    delta_html = ""
    if delta is not None:
        delta_html = (
            f'<div style="font-size:13px; color:{delta_color}; '
            f'margin-top:4px; font-weight:600;">'
            f'{arrow} {delta}</div>'
        )

    return f"""
    <div style="
        background: linear-gradient(135deg, {Colors.SURFACE} 0%, {Colors.PRIMARY_LIGHT} 100%);
        border: 1px solid {Colors.BORDER};
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: transform 0.2s ease;
    ">
        <div style="font-size:12px; color:{Colors.TEXT_SECONDARY};
             text-transform:uppercase; letter-spacing:0.5px;
             font-weight:600; margin-bottom:8px;">
            {label}
        </div>
        <div style="font-size:28px; font-weight:700; color:{Colors.TEXT_PRIMARY};
             line-height:1.2;">
            {value}
        </div>
        {delta_html}
    </div>
    """


# ============================================================
# LINE CHART
# ============================================================

def create_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: Optional[str] = None,
    height: int = 400,
) -> go.Figure:
    """
    Create a styled line chart.

    Args:
        df: Source DataFrame.
        x: Column name for x-axis.
        y: Column name for y-axis.
        title: Chart title.
        color: Line color (defaults to PRIMARY).
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    line_color = color or Colors.PRIMARY

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            line=dict(color=line_color, width=2.5, shape="spline"),
            marker=dict(size=5, color=line_color),
            name=y,
            hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{y:,.0f}}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=height, xaxis_title=x, yaxis_title=y)
    return apply_healthcare_theme(fig)


# ============================================================
# MULTI-LINE CHART
# ============================================================

def create_multi_line_chart(
    df: pd.DataFrame,
    x: str,
    y_columns: list[str],
    title: str,
    height: int = 400,
) -> go.Figure:
    """
    Create a multi-line chart with distinct colors per series.

    Args:
        df: Source DataFrame.
        x: Column name for x-axis.
        y_columns: List of column names for y-axis series.
        title: Chart title.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()
    for i, col in enumerate(y_columns):
        color = CHART_COLORS[i % len(CHART_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[col],
                mode="lines+markers",
                line=dict(color=color, width=2, shape="spline"),
                marker=dict(size=4, color=color),
                name=col,
                hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,.0f}}<extra></extra>",
            )
        )
    fig.update_layout(title=title, height=height, xaxis_title=x)
    return apply_healthcare_theme(fig)


# ============================================================
# BAR CHART
# ============================================================

def create_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: Optional[str] = None,
    horizontal: bool = False,
    height: int = 400,
) -> go.Figure:
    """
    Create a styled bar chart (vertical or horizontal).

    Args:
        df: Source DataFrame.
        x: Column for categories.
        y: Column for values.
        title: Chart title.
        color: Bar color (defaults to PRIMARY).
        horizontal: If True, renders horizontal bars.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    bar_color = color or Colors.PRIMARY

    if horizontal:
        fig = go.Figure(
            go.Bar(
                x=df[y],
                y=df[x],
                orientation="h",
                marker=dict(color=bar_color, cornerradius=4),
                hovertemplate="<b>%{y}</b><br>Value: %{x:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(xaxis_title=y, yaxis_title=x)
    else:
        fig = go.Figure(
            go.Bar(
                x=df[x],
                y=df[y],
                marker=dict(color=bar_color, cornerradius=4),
                hovertemplate="<b>%{x}</b><br>Value: %{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(xaxis_title=x, yaxis_title=y)

    fig.update_layout(title=title, height=height)
    return apply_healthcare_theme(fig)


# ============================================================
# GROUPED BAR CHART
# ============================================================

def create_grouped_bar_chart(
    df: pd.DataFrame,
    x: str,
    y_columns: list[str],
    title: str,
    height: int = 400,
) -> go.Figure:
    """
    Create a grouped bar chart with distinct colors per group.

    Args:
        df: Source DataFrame.
        x: Column for categories.
        y_columns: List of value columns (one bar per group).
        title: Chart title.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()
    for i, col in enumerate(y_columns):
        color = CHART_COLORS[i % len(CHART_COLORS)]
        fig.add_trace(
            go.Bar(
                x=df[x],
                y=df[col],
                name=col,
                marker=dict(color=color, cornerradius=4),
                hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,.0f}}<extra></extra>",
            )
        )
    fig.update_layout(title=title, height=height, barmode="group")
    return apply_healthcare_theme(fig)


# ============================================================
# PIE CHART
# ============================================================

def create_pie_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str,
    height: int = 400,
) -> go.Figure:
    """
    Create a styled pie chart.

    Args:
        df: Source DataFrame.
        names: Column for slice labels.
        values: Column for slice values.
        title: Chart title.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure(
        go.Pie(
            labels=df[names],
            values=df[values],
            marker=dict(colors=CHART_COLORS[: len(df)]),
            textinfo="percent+label",
            textposition="inside",
            textfont=dict(size=12),
            hovertemplate="<b>%{label}</b><br>Value: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=height, showlegend=True)
    return apply_healthcare_theme(fig)


# ============================================================
# DONUT CHART
# ============================================================

def create_donut_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str,
    height: int = 400,
) -> go.Figure:
    """
    Create a donut chart (pie with center hole).

    Args:
        df: Source DataFrame.
        names: Column for slice labels.
        values: Column for slice values.
        title: Chart title.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure(
        go.Pie(
            labels=df[names],
            values=df[values],
            hole=0.5,
            marker=dict(colors=CHART_COLORS[: len(df)]),
            textinfo="percent+label",
            textposition="outside",
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>Value: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=height, showlegend=True)
    return apply_healthcare_theme(fig)


# ============================================================
# HEATMAP
# ============================================================

def create_heatmap(
    data_matrix: list[list[float]],
    x_labels: list[str],
    y_labels: list[str],
    title: str,
    colorscale: str = "Blues",
    height: int = 400,
) -> go.Figure:
    """
    Create a heatmap chart.

    Args:
        data_matrix: 2-D list of values (rows × cols).
        x_labels: Labels for x-axis.
        y_labels: Labels for y-axis.
        title: Chart title.
        colorscale: Plotly colorscale name.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure(
        go.Heatmap(
            z=data_matrix,
            x=x_labels,
            y=y_labels,
            colorscale=colorscale,
            hovertemplate="<b>%{x}</b> / <b>%{y}</b><br>Value: %{z:.1f}<extra></extra>",
            colorbar=dict(thickness=15, len=0.8),
        )
    )
    fig.update_layout(title=title, height=height)
    return apply_healthcare_theme(fig)


# ============================================================
# GAUGE CHART
# ============================================================

def create_gauge_chart(
    value: float,
    max_val: float,
    title: str,
    ranges: Optional[List[Tuple[float, float, str]]] = None,
    height: int = 250,
) -> go.Figure:
    """
    Create a gauge (speedometer) chart.

    Args:
        value: Current value.
        max_val: Maximum scale value.
        title: Chart title.
        ranges: List of (start, end, color) tuples for gauge segments.
            Defaults to green/amber/red thirds.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    if ranges is None:
        third = max_val / 3
        ranges = [
            (0, third, Colors.SUCCESS),
            (third, 2 * third, Colors.WARNING),
            (2 * third, max_val, Colors.DANGER),
        ]

    steps = [
        dict(range=[start, end], color=color)
        for start, end, color in ranges
    ]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title=dict(text=title, font=dict(size=14, color=Colors.TEXT_PRIMARY)),
            number=dict(font=dict(size=28, color=Colors.TEXT_PRIMARY)),
            gauge=dict(
                axis=dict(
                    range=[0, max_val],
                    tickwidth=1,
                    tickcolor=Colors.TEXT_SECONDARY,
                    tickfont=dict(size=10),
                ),
                bar=dict(color=Colors.PRIMARY_DARK, thickness=0.25),
                bgcolor=Colors.BACKGROUND,
                borderwidth=1,
                bordercolor=Colors.BORDER,
                steps=steps,
                threshold=dict(
                    line=dict(color=Colors.DANGER, width=3),
                    thickness=0.8,
                    value=value,
                ),
            ),
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=30, r=30, t=60, b=20),
        paper_bgcolor=Colors.SURFACE,
        font=dict(family="Inter, sans-serif"),
    )
    return fig


# ============================================================
# AREA CHART
# ============================================================

def create_area_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    height: int = 400,
) -> go.Figure:
    """
    Create a filled area chart.

    Args:
        df: Source DataFrame.
        x: Column for x-axis.
        y: Column for y-axis.
        title: Chart title.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure(
        go.Scatter(
            x=df[x],
            y=df[y],
            fill="tozeroy",
            mode="lines",
            line=dict(color=Colors.PRIMARY, width=2, shape="spline"),
            fillcolor=f"rgba(37, 99, 235, 0.15)",
            name=y,
            hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{y:,.0f}}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=height, xaxis_title=x, yaxis_title=y)
    return apply_healthcare_theme(fig)


# ============================================================
# SCATTER CHART
# ============================================================

def create_scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: Optional[str] = None,
    size: Optional[str] = None,
    height: int = 400,
) -> go.Figure:
    """
    Create a scatter plot.

    Args:
        df: Source DataFrame.
        x: Column for x-axis.
        y: Column for y-axis.
        title: Chart title.
        color: Optional column for color encoding.
        size: Optional column for marker size encoding.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    marker_kwargs: dict = dict(
        color=df[color] if color and color in df.columns else Colors.PRIMARY,
        size=df[size] if size and size in df.columns else 8,
        opacity=0.75,
        line=dict(width=1, color=Colors.SURFACE),
    )
    if color and color in df.columns:
        marker_kwargs["colorscale"] = "Viridis"
        marker_kwargs["showscale"] = True
        marker_kwargs["colorbar"] = dict(thickness=12, len=0.6)

    fig = go.Figure(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="markers",
            marker=marker_kwargs,
            hovertemplate=f"<b>{x}</b>: %{{x}}<br><b>{y}</b>: %{{y:,.1f}}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=height, xaxis_title=x, yaxis_title=y)
    return apply_healthcare_theme(fig)
