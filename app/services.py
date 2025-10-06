import time
import requests
from typing import List, Dict, Optional
import pandas as pd
import yfinance as yf
from dateutil import tz
from app.utils import get_logger, get_secrets

logger = get_logger()
secrets = get_secrets()

ALPHA_URL = "https://www.alphavantage.co/query"
FINNHUB_URL = "https://finnhub.io/api/v1"

# ADD this helper near the top (after imports/constants)
def resolve_yf_symbol(symbol: str) -> Optional[str]:
    """Try common Yahoo suffixes and return the first that has data."""
    candidates = [symbol, f"{symbol}.NS", f"{symbol}.BO", f"{symbol}.BSE", f"{symbol}.NSE"]
    seen = set()
    for cand in candidates:
        if cand in seen: 
            continue
        seen.add(cand)
        try:
            t = yf.Ticker(cand)
            df = t.history(period="5d", interval="1d")
            if not df.empty:
                return cand
        except Exception:
            continue
    return None

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

# UPDATE get_history_yf to use the resolver
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


# REPLACE get_fast_info with a safer version (avoids KeyError: 'currency')
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