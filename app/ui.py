import streamlit as st
import pandas as pd
import altair as alt
from app.utils import kformat, currency_prefix

def kpi_row(price: float | None, change: float | None, mcap: float | None, currency_code: str | None = None):
    sym = currency_prefix(currency_code)
    c1, c2, c3 = st.columns(3)
    with c1:
        val = f"{sym}{price:,.2f}" if price is not None else "-"
        delta = f"{change:+.2f}%" if change is not None else None
        st.metric("Price", val, delta=delta)
    with c2:
        st.metric("Market Cap", f"{sym}{kformat(mcap)}" if mcap is not None else "-")
    with c3:
        st.metric("52W Range", "see Fundamentals tab →")


def themed_altair(chart: alt.Chart) -> alt.Chart:
    # Read current theme settings provided by Streamlit
    base = (st.get_option("theme.base") or "dark").lower()                 # "dark" | "light"
    bg   = st.get_option("theme.backgroundColor") or ("#22272E" if base == "dark" else "#FFFFFF")
    txt  = st.get_option("theme.textColor")        or ("#768390" if base == "dark" else "#111827")

    # Choose a reasonable grid/border color (not exposed directly by Streamlit)
    grid = "#3a3a3a" if base == "dark" else "#e5e7eb"

    return (
        chart
        .configure(background=bg)
        .configure_axis(labelColor=txt, titleColor=txt, gridColor=grid)
        .configure_legend(labelColor=txt, titleColor=txt)
        .configure_title(color=txt)
    )

# usage in app/ui.py
def price_chart(df: pd.DataFrame, symbol: str):
    if df.empty:
        st.info("No price data available.")
        return

    base_chart = (
        alt.Chart(df, title=f"{symbol} — Adjusted Close")
        .mark_line()
        .encode(
            x="Date:T",
            y=alt.Y("Close:Q", title="Close")
        )
        .properties(height=280)
    )

    themed = themed_altair(base_chart)
    st.altair_chart(themed, use_container_width=True)