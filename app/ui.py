import streamlit as st
import pandas as pd
import altair as alt
from app.utils import kformat, currency_prefix

def price_chart(df: pd.DataFrame, symbol: str):
    if df.empty:
        st.info("No price data available.")
        return
    chart = (
        alt.Chart(df, title=f"{symbol} — Adjusted Close")
        .mark_line()
        .encode(x="Date:T", y=alt.Y("Close:Q", title="Close"))
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)


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