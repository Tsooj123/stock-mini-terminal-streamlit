import logging
from functools import lru_cache
from typing import Any, Dict
import streamlit as st


# ---------- Logging ----------


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    logger = logging.getLogger("stock-mini-terminal")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ---------- Secrets ----------


@lru_cache(maxsize=1)
def get_secrets() -> Dict[str, Any]:
# Streamlit exposes secrets via st.secrets
    return {
        "ALPHA_VANTAGE_KEY": st.secrets.get("ALPHA_VANTAGE_KEY", ""),
        "FINNHUB_KEY": st.secrets.get("FINNHUB_KEY", ""),
        "FMP_KEY": st.secrets.get("FMP_KEY", ""),
        "OFFLINE_MODE": str(st.secrets.get("OFFLINE_MODE", "false")).lower() == "true",
    }


# ---------- UI helpers ----------


def kformat(num: float) -> str:
    try:
        n = float(num)
    except Exception:
        return "-"
    for unit in ["", "K", "M", "B", "T"]:
        if abs(n) < 1000.0:
            return f"{n:,.2f}{unit}"
        n /= 1000.0
    return f"{n:.2f}P"