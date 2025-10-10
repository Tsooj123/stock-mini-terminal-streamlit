import datetime as dt
import os
import toml
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


if st.session_state.get("flash_msg"):
    st.toast(st.session_state.pop("flash_msg"))

# --------------- Sidebar ---------------
st.sidebar.image("assets/placeholder.png", width="stretch")
st.sidebar.markdown(
    """
    <h1 style='color: #008B8B; font-size: 36px;'>Settings</h1>
    """, 
    unsafe_allow_html=True
)
period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

# Sidebar theme toggle (persist in session)

toggle_dark = st.sidebar.toggle("Dark Mode", value=True)
if st.get_option("theme.base") == "light" and toggle_dark:
    st._config.set_option("theme.base", "dark")  # type: ignore # noqa: SLF001
    st.rerun()
elif st.get_option("theme.base") == "dark" and not toggle_dark:
    st._config.set_option("theme.base", "light")  # type: ignore # noqa: SLF001
    st.rerun()


st.sidebar.markdown("### Connect")

# --- Social icons row (centered) ---
i1, i2, i3 = st.sidebar.columns(3)
with i1:
    st.markdown(
        '<a href="https://www.linkedin.com/in/brejesh-balakrishnan-7855051b9/" target="_blank">'
        '<img src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg" width="28" alt="LinkedIn"/></a>',
        unsafe_allow_html=True,
    )
with i2:
    st.markdown(
        '<a href="https://github.com/brej-29" target="_blank">'
        '<img src="https://cdn.simpleicons.org/github/898989" width="28" alt="GitHub"/></a>',
        unsafe_allow_html=True,
    )
with i3:
    st.markdown(
        '<a href="https://share.streamlit.io/user/brej-29" target="_blank">'
        '<img src="https://cdn.simpleicons.org/streamlit/FF4B4B" width="28" alt="Streamlit"/></a>',
        unsafe_allow_html=True,
    )
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
    with st.spinner("Searching (Yahoo → FMP → Alpha)…"):
        # Yahoo first (fast/keyless). If DNS fails, function returns [] quickly.
        yahoo = search_symbol_yahoo(q)
        if yahoo:
            results = [{
                "1. symbol": (it.get("symbol") or "").upper(),
                "2. name": it.get("shortname") or it.get("longname") or "",
                "4. region": it.get("exchDisp") or "",
            } for it in yahoo if it.get("symbol")]

        if not results:
            results = search_symbol_fmp(q)     # requires FMP_KEY

        if not results:
            results = search_symbol_alpha(q)   # last resort; often rate-limited


col_left, col_right = st.columns([2, 1])

with col_left:
    if results:
        # Filter to symbols that actually have Yahoo price data
        options, sym_map = [], {}
        for m in results:
            raw = (m.get("1. symbol") or "").upper()
            name = m.get("2. name") or ""
            region = m.get("4. region") or ""
            label = f"{raw} — {name} ({region})"
            options.append(label); sym_map[label] = raw
        choice = st.selectbox("Select a match", options)
        symbol = sym_map.get(choice)
        # If the chosen symbol contains spaces or weird chars, guard quickly
        if symbol and not symbol.replace(".", "").isalnum():
            st.warning("That symbol looks invalid. Try another.")
            symbol = None
    else:
        symbol = None
        if q:
            st.warning("No results from Alpha Vantage/Yahoo. Check your key/rate limit or try a different query.")

with col_right:
    st.subheader("Watchlist")
    if st.session_state.watchlist:
        st.write(", ".join(st.session_state.watchlist))
        if st.sidebar.button("🧹 Clear watchlist"):
            st.session_state.watchlist = []
            st.toast("Watchlist cleared")
            st.rerun()
    else:
        st.write("(empty)")

# --------------- Main Tabs ---------------
if symbol:
    tabs = st.tabs(["Overview", "Fundamentals", "News"])

    # -------- Overview Tab --------
    with tabs[0]:
        with st.spinner("Loading overview..."):
            resolved = resolve_yf_symbol(symbol) or symbol
            df = get_history_yf(resolved, period=period, interval=interval)
            fast = get_fast_info(resolved)

            # currency (from yfinance fast_info if available; fallback later)
            currency = (fast.get("currency") if isinstance(fast, dict) else None) or "USD"

            last_price = fast.get("last_price") if fast else (df["Close"].iloc[-1] if not df.empty else None)
            prev_close = fast.get("previous_close") if fast else (df["Close"].iloc[-2] if len(df) > 1 else None)
            change = ((last_price - prev_close) / prev_close) * 100 if (last_price is not None and prev_close) else None
            mcap = fast.get("market_cap")

            kpi_row(last_price, change, mcap, currency)  # <-- pass currency now
            price_chart(df, symbol)

            if resolved != symbol:
                st.caption(f"Resolved Yahoo symbol: **{resolved}**")

            c1, c2 = st.columns(2)
            with c1:
                clicked = st.button("➕ Add to watchlist", key=f"add_{symbol}")
                if clicked:
                    wl = st.session_state.get("watchlist", [])
                    if symbol and symbol not in wl:
                        st.session_state.watchlist = wl + [symbol]  # avoid in-place mutation edge cases
                        st.session_state["flash_msg"] = f"Added {symbol} to watchlist"
                    st.rerun()  # works here (not inside a callback)
            with c2:
                if not df.empty:
                    st.download_button(
                        "⬇️ Download price CSV",
                        df.to_csv(index=False).encode("utf-8"),
                        file_name=f"{resolved}_{period}_{interval}.csv",
                        mime="text/csv",
                    )

    # -------- Fundamentals Tab --------
    with tabs[1]:
        with st.spinner("Loading fundamentals..."):
            ov = company_overview_alpha(symbol)  # may be {} or rate-limited
            fmp = company_profile_fmp(symbol)    # if you added FMP; else keep Finnhub

            # consider AV meaningful only if any of these keys are non-empty
            av_keys = ("Name","Sector","Industry","MarketCapitalization","PERatio","EPS","DividendYield","ProfitMargin","ReturnOnEquityTTM")
            av_has_data = any(ov.get(k) not in (None, "", "None") for k in av_keys) if ov else False

            if not av_has_data and not fmp:
                st.info("No fundamentals available for this symbol (provider limits/exchange coverage).")
            else:
                cols = st.columns(2)

                # Alpha Vantage (only if has data)
                if av_has_data:
                    with cols[0]:
                        st.subheader("Source: Alpha Vantage — Company Overview")
                        for k in av_keys:
                            v = ov.get(k)
                            if v not in (None, "", "None"):
                                st.write(f"**{k}:** {v}")
                else:
                    with cols[0]:
                        st.subheader("Source: Alpha Vantage")
                        st.caption("(No usable data for this ticker)")

                # FMP profile (only if present)
                if fmp:
                    with cols[1]:
                        st.subheader("Source: FMP — Company Profile")
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
                            if v not in (None, "", "None"):
                                st.write(f"**{k}:** {v}")
                else:
                    with cols[1]:
                        st.subheader("Source: FMP")
                        st.caption("(Profile unavailable)")

    # -------- News Tab --------
    with tabs[2]:
        with st.spinner("Fetching recent news..."):
            resolved = resolve_yf_symbol(symbol) or symbol
            today = dt.date.today()
            start = today - dt.timedelta(days=14)

            news = finnhub_company_news(symbol, start.isoformat(), today.isoformat())  # if you gate by supports_finnhub, keep it
            # if empty and you added FMP fallback, call that here with `resolved`
            if not news:
                st.info("No recent company news (provider limits/exchange coverage).")
            else:
                for item in news:
                    with st.expander(item.get("headline", "(no headline)")):
                        st.write(item.get("summary") or "(no summary)")
                        if item.get("url"):
                            st.link_button("Read source", item["url"])


if st.session_state.get("flash_msg"):
    st.toast(st.session_state.pop("flash_msg"))