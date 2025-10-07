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
    # ADD:
    search_symbol_yahoo,
    resolve_yf_symbol,
    supports_finnhub,
    search_symbol_fmp,
    company_profile_fmp, quote_short_fmp, stock_news_fmp
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
        if not results:  # Fallback to FMP
            results = search_symbol_fmp(q)
        if not results:  # Fallback to Yahoo
            yahoo = search_symbol_yahoo(q)
            results = [{
                "1. symbol": (it.get("symbol") or "").upper(),
                "2. name": it.get("shortname") or it.get("longname") or "",
                "4. region": it.get("exchDisp") or "",
            } for it in yahoo if it.get("symbol")]


col_left, col_right = st.columns([2, 1])

with col_left:
    if results:
        # Filter to symbols that actually have Yahoo price data
        options, sym_map = [], {}
        for m in results or []:
            raw_sym = (m.get("1. symbol") or "").upper()
            if resolve_yf_symbol(raw_sym):
                label = f"{raw_sym} — {m.get('2. name','')} ({m.get('4. region','')})"
                options.append(label); sym_map[label] = raw_sym  # keep the raw symbol for Alpha/Finnhub; we'll resolve for yfinance later

        if options:
            choice = st.selectbox("Select a match", options)
            symbol = sym_map.get(choice)
        else:
            symbol = None
            st.warning("No symbols with valid price data were found. Try another query.")
    else:
        symbol = None
        if q:
            st.warning("No results from Alpha Vantage/Yahoo. Check your key/rate limit or try a different query.")

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
        with st.spinner("Loading overview..."):
            df = get_history_yf(symbol, period=period, interval=interval)
            fast = get_fast_info(symbol)

            last_price = fast.get("last_price") if fast else (df["Close"].iloc[-1] if not df.empty else None)
            prev_close = fast.get("previous_close") if fast else (df["Close"].iloc[-2] if len(df) > 1 else None)
            change = None
            if last_price is not None and prev_close not in (None, 0):
                change = ((last_price - prev_close) / prev_close) * 100

            mcap = fast.get("market_cap", None)
            kpi_row(last_price, change, mcap)
            price_chart(df, symbol)

            # Show which Yahoo ticker was used
            try:
                resolved = resolve_yf_symbol(symbol)
                if resolved and resolved != symbol:
                    st.caption(f"Resolved Yahoo symbol: **{resolved}**")
            except Exception:
                pass

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
        with st.spinner("Loading fundamentals..."):
            ov  = company_overview_alpha(symbol)         # Alpha Vantage (may be empty/rate-limited)
            fmp = company_profile_fmp(symbol)            # FMP fallback/primary

            if not ov and not fmp:
                st.info("No fundamentals available for this symbol (provider limits/exchange coverage).")
            else:
                colA, colB = st.columns(2)

                with colA:
                    st.subheader("Funder: Alpha Vantage — Company Overview")
                    if ov:
                        for k in ("Name","Sector","Industry","MarketCapitalization","DividendYield","PERatio","EPS","ProfitMargin","ReturnOnEquityTTM"):
                            st.write(f"**{k}:** {ov.get(k) or '-'}")
                    else:
                        st.caption("(Alpha Vantage unavailable)")

                with colB:
                    st.subheader("Funder: FMP — Company Profile")
                    if fmp:
                        fields = {
                            "companyName": fmp.get("companyName"),
                            "exchange": fmp.get("exchangeFullName") or fmp.get("exchange"),
                            "industry": fmp.get("industry"),
                            "sector": fmp.get("sector"),
                            "mktCap": fmp.get("marketCap") or fmp.get("mktCap"),
                            "currency": fmp.get("currency"),
                            "website": fmp.get("website"),
                            "description": fmp.get("description"),
                        }
                        for k, v in fields.items():
                            st.write(f"**{k}:** {v or '-'}")
                    else:
                        st.caption("(FMP profile unavailable)")

    # -------- News Tab --------
    with tabs[2]:
        with st.spinner("Fetching recent news..."):
            today = dt.date.today()
            start = today - dt.timedelta(days=14)

            news = finnhub_company_news(symbol, start.isoformat(), today.isoformat())
            if not news:
                sym = resolve_yf_symbol(symbol) or symbol
                news = stock_news_fmp(sym)  # FMP fallback

            if not news:
                st.info("No recent news (provider limits/exchange coverage).")
            else:
                for item in news:
                    title = item.get("headline") or item.get("title") or "(no headline)"
                    with st.expander(title):
                        summary = item.get("summary") or item.get("text") or "(no summary)"
                        url = item.get("url") or item.get("link")
                        st.write(summary)
                        if url:
                            st.link_button("Read source", url)