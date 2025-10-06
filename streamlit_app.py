import datetime as dt
import pandas as pd
import streamlit as st

from app.services import (
    search_symbol_alpha,
    company_overview_alpha,
    get_history_yf,
    get_fast_info,
    finnhub_company_profile,
    finnhub_company_news,
)
from app.ui import price_chart, kpi_row
from app.utils import get_logger, get_secrets

logger = get_logger()
secrets = get_secrets()

st.set_page_config(page_title="Stock Mini Terminal", page_icon="📈", layout="wide")

# --------------- Sidebar ---------------
st.sidebar.image("assets/placeholder.png", width="stretch")
st.sidebar.header("Settings")
period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

# Watchlist stored in session_state
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# --------------- Header ---------------
st.title("📈 Stock Finder & Mini Terminal")
st.caption("Search a stock, view price, fundamentals, and recent news. Built with Streamlit.")

# --------------- Search ---------------
q = st.text_input("🔎 Search by company name or symbol", value="", placeholder="e.g., TCS or AAPL")

results = []
if q:
    with st.spinner("Searching symbols..."):
        results = search_symbol_alpha(q)

col_left, col_right = st.columns([2, 1])

with col_left:
    if results:
        # Render search results as a selectbox of "SYM — Name (Region)"
        options = []
        sym_map = {}
        for m in results:
            sym = m.get("1. symbol", "").upper()
            name = m.get("2. name", "")
            region = m.get("4. region", "")
            label = f"{sym} — {name} ({region})"
            options.append(label)
            sym_map[label] = sym
        choice = st.selectbox("Select a match", options)
        symbol = sym_map.get(choice)
    else:
        symbol = None
        if q:
            st.warning("No results from Alpha Vantage. Check your key/rate limit or try a different query.")


with col_right:
    st.subheader("Watchlist")
    if st.session_state.watchlist:
        st.write(", ".join(st.session_state.watchlist))
        if st.button("Clear watchlist"):
            st.session_state.watchlist = []
    else:
        st.write("(empty)")

# --------------- Main Tabs ---------------
if symbol:
    tabs = st.tabs(["Overview", "Fundamentals", "News"])

    # -------- Overview Tab --------
    with tabs[0]:
        df = get_history_yf(symbol, period=period, interval=interval)
        fast = get_fast_info(symbol)

        # after df/fast are fetched
        try:
            from app.services import resolve_yf_symbol
            resolved = resolve_yf_symbol(symbol)
            if resolved and resolved != symbol:
                st.caption(f"Resolved Yahoo symbol: **{resolved}**")
        except Exception:
            pass

        last_price = fast.get("last_price") if fast else (df["Close"].iloc[-1] if not df.empty else None)
        prev_close = fast.get("previous_close") if fast else (df["Close"].iloc[-2] if len(df) > 1 else None)
        change = None
        if last_price is not None and prev_close not in (None, 0):
            change = ((last_price - prev_close) / prev_close) * 100

        mcap = fast.get("market_cap", None)
        kpi_row(last_price, change, mcap)
        price_chart(df, symbol)

        add_col1, add_col2 = st.columns(2)
        with add_col1:
            if st.button("➕ Add to watchlist"):
                if symbol not in st.session_state.watchlist:
                    st.session_state.watchlist.append(symbol)
                    st.success(f"Added {symbol} to watchlist")
                    st.balloons()
        with add_col2:
            if not df.empty:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download price CSV", csv, file_name=f"{symbol}_{period}_{interval}.csv", mime="text/csv")

    # -------- Fundamentals Tab --------
    with tabs[1]:
        ov = company_overview_alpha(symbol)
        prof = finnhub_company_profile(symbol)
        if not ov and not prof:
            st.info("No fundamentals available (check API keys or rate limits).")
        else:
            colA, colB = st.columns(2)
            with colA:
                st.subheader("Alpha Vantage — Company Overview")
                if ov:
                    fields = [
                        ("Name", ov.get("Name")),
                        ("Sector", ov.get("Sector")),
                        ("Industry", ov.get("Industry")),
                        ("MarketCapitalization", ov.get("MarketCapitalization")),
                        ("DividendYield", ov.get("DividendYield")),
                        ("PERatio", ov.get("PERatio")),
                        ("EPS", ov.get("EPS")),
                        ("ProfitMargin", ov.get("ProfitMargin")),
                        ("ReturnOnEquityTTM", ov.get("ReturnOnEquityTTM")),
                    ]
                    for k, v in fields:
                        st.write(f"**{k}:** {v if v not in (None, '', 'None') else '-'}")
                else:
                    st.caption("(No Alpha Vantage overview or rate-limited)")
            with colB:
                st.subheader("Finnhub — Company Profile")
                if prof:
                    f_fields = [
                        ("Name", prof.get("name")),
                        ("Exchange", prof.get("exchange")),
                        ("IPO", prof.get("ipo")),
                        ("Market Cap", prof.get("marketCapitalization")),
                        ("Web", prof.get("weburl")),
                        ("Country", prof.get("country")),
                        ("Currency", prof.get("currency")),
                    ]
                    for k, v in f_fields:
                        st.write(f"**{k}:** {v if v not in (None, '', 'None') else '-'}")
                else:
                    st.caption("(No Finnhub profile or key missing)")

    # -------- News Tab --------
    with tabs[2]:
        today = dt.date.today()
        start = today - dt.timedelta(days=14)
        news = finnhub_company_news(symbol, start.isoformat(), today.isoformat())
        if not news:
            st.info("No recent company news (or API rate-limited).")
        else:
            for item in news:
                with st.expander(item.get("headline", "(no headline)")):
                    ts = item.get("datetime")
                    summary = item.get("summary") or "(no summary)"
                    url = item.get("url")
                    st.write(summary)
                    if url:
                        st.link_button("Read source", url)