import time
import requests
from typing import List, Dict, Optional
import pandas as pd
import yfinance as yf
from dateutil import tz
from app.utils import get_logger, get_secrets
from typing import Tuple
from typing import List, Dict, Optional

logger = get_logger()
secrets = get_secrets()

FMP_URL = "https://financialmodelingprep.com"
ALPHA_URL = "https://www.alphavantage.co/query"
FINNHUB_URL = "https://finnhub.io/api/v1"

def fmp_get(path: str, params: Dict | None = None) -> dict | list:
    if params is None:
        params = {}
    key = secrets.get("FMP_KEY", "")
    if key:
        params = {**params, "apikey": key}
    else:
        logger.warning("FMP_KEY missing: skipping FMP request to %s", path)
    r = requests.get(f"{FMP_URL}{path}", params=params, timeout=20)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        logger.error("FMP HTTP %s for %s | url=%s", r.status_code, path, r.url)
        raise
    return r.json()

# -------- FMP: search / profile / quote / news --------
def search_symbol_fmp(query: str) -> List[Dict]:
    try:
        data = fmp_get("/stable/search-symbol", {"query": query})
        # Normalize to Alpha-like fields so the rest of the app can reuse UI
        out = []
        for it in data or []:
            out.append({
                "1. symbol": (it.get("symbol") or "").upper(),
                "2. name": it.get("name") or "",
                "4. region": it.get("exchangeShortName") or it.get("exchange") or "",
            })
        return out
    except Exception:
        logger.exception("FMP search failed")
        return []

def company_profile_fmp(symbol: str) -> Dict:
    """Returns a dict profile or {}. Tries common NSE/BSE suffixes too."""
    variants = [symbol, f"{symbol}.NS", f"{symbol}.BO", f"{symbol}.NSE", f"{symbol}.BSE"]
    tried = set()
    for s in variants:
        if not s or s in tried: 
            continue
        tried.add(s)
        try:
            data = fmp_get("/stable/profile", {"symbol": s})
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict) and data:
                return data
        except Exception:
            logger.exception("FMP profile failed for %s", s)
            continue
    return {}

def quote_short_fmp(symbol: str) -> Dict:
    try:
        data = fmp_get("/stable/quote-short", {"symbol": symbol})
        if isinstance(data, list) and data:
            return data[0]
        return {}
    except Exception:
        logger.exception("FMP quote-short failed")
        return {}

def stock_news_fmp(symbol: str, page: int = 0) -> List[Dict]:
    try:
        data = fmp_get("/stable/news/stock", {"symbols": symbol, "page": page})
        return data if isinstance(data, list) else []
    except Exception:
        logger.exception("FMP news failed")
        return []

# -------- Yahoo keyless search fallback (already suggested earlier) --------
def search_symbol_yahoo(query: str) -> list[dict]:
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": query, "quotesCount": 10, "newsCount": 0},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("quotes", [])
    except Exception:
        logger.exception("Yahoo search failed")
    return []

def resolve_symbol_variants(raw: str) -> list[str]:
    s = raw.upper()
    return [s, f"{s}.NS", f"{s}.BO", f"{s}.NSE", f"{s}.BSE"]

def resolve_yf_symbol(symbol: str) -> Optional[str]:
    for cand in resolve_symbol_variants(symbol):
        try:
            if not cand:
                continue
            t = yf.Ticker(cand)
            df = t.history(period="5d", interval="1d")
            if not df.empty:
                return cand
        except Exception:
            continue
    return None

# OPTIONAL helper: gate Finnhub to tickers it’s likely to support (US-style, no dot suffix)
def supports_finnhub(symbol: str) -> bool:
    return symbol.isalpha() and "." not in symbol

# ---------- Simple retry wrapper ----------

def _get_with_retry(url: str, params: Dict, max_tries: int = 3, backoff: float = 1.5):
    last_exc = None
    for i in range(max_tries):
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            else:
                logger.warning(f"HTTP {r.status_code} for {url} | params={params}")
        except Exception as e:
            last_exc = e
            logger.exception("Request failed, retrying...")
        time.sleep(backoff * (i + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError("Unknown error in _get_with_retry")

# ---------- Alpha Vantage SYMBOL_SEARCH & OVERVIEW ----------

def search_symbol_alpha(query: str) -> List[Dict]:
    key = secrets.get("ALPHA_VANTAGE_KEY", "")
    if not key:
        return []
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": query,
        "apikey": key,
    }
    data = _get_with_retry(ALPHA_URL, params)
    return data.get("bestMatches", [])


def company_overview_alpha(symbol: str) -> Dict:
    key = secrets.get("ALPHA_VANTAGE_KEY", "")
    if not key:
        return {}
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": key,
    }
    data = _get_with_retry(ALPHA_URL, params)
    return data if isinstance(data, dict) else {}

# ---------- Yahoo Finance for price history (no key) ----------

# UPDATE get_history_yf to use resolver
def get_history_yf(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        sym = resolve_yf_symbol(symbol) or symbol
        t = yf.Ticker(sym)
        df = t.history(period=period, interval=interval, auto_adjust=False)
        if not df.empty:
            df = df.reset_index()
        return df
    except Exception as e:
        logger.exception(f"yfinance history failed for {symbol}: {e}")
        return pd.DataFrame()


# REPLACE get_fast_info with safer version (avoids KeyError)
def get_fast_info(symbol: str) -> Dict:
    try:
        sym = resolve_yf_symbol(symbol) or symbol
        t = yf.Ticker(sym)
        fi = getattr(t, "fast_info", None)
        out = {}
        for k in ("last_price", "previous_close", "market_cap"):
            try:
                out[k] = getattr(fi, k) if fi is not None else None
            except Exception:
                out[k] = None
        return out
    except Exception:
        logger.exception("yfinance fast_info failed")
        return {}

# ---------- Finnhub company profile & news (free tier) ----------

def finnhub_company_profile(symbol: str) -> Dict:
    key = secrets.get("FINNHUB_KEY", "")
    if not key:
        return {}
    params = {"symbol": symbol, "token": key}
    try:
        return _get_with_retry(f"{FINNHUB_URL}/stock/profile2", params)
    except Exception:
        logger.exception("Finnhub profile failed")
        return {}


def finnhub_company_news(symbol: str, _from: str, _to: str) -> List[Dict]:
    key = secrets.get("FINNHUB_KEY", "")
    if not key:
        return []
    params = {"symbol": symbol, "from": _from, "to": _to, "token": key}
    try:
        data = _get_with_retry(f"{FINNHUB_URL}/company-news", params)
        if isinstance(data, list):
            return data[:20]
        return []
    except Exception:
        logger.exception("Finnhub news failed")
        return []