<div align="center">
  <h1>📈 Stock Finder & Mini Terminal</h1>
  <p><i>Search tickers by name, view price performance, fundamentals, and recent news — built with Streamlit</i></p>
</div>

<br>

<div align="center">
  <a href="https://github.com/YOUR-USERNAME/stock-mini-terminal-streamlit">
    <img alt="Last Commit" src="https://img.shields.io/github/last-commit/YOUR-USERNAME/stock-mini-terminal-streamlit">
  </a>
  <img alt="Language" src="https://img.shields.io/badge/Language-Python-blue">
  <img alt="Framework" src="https://img.shields.io/badge/Framework-Streamlit-ff4b4b">
  <img alt="Data" src="https://img.shields.io/badge/Data-yfinance%20%7C%20Alpha%20Vantage%20%7C%20Finnhub%20%7C%20FMP-8A2BE2">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-black">
</div>

<div align="center">
  <br>
  <b>Built with the tools and technologies:</b>
  <br><br>
  <code>Python</code> | <code>Streamlit</code> | <code>Altair</code> | <code>Pandas</code> | <code>yfinance</code> | <code>Alpha Vantage</code> | <code>Finnhub</code> | <code>Financial Modeling Prep (FMP)</code>
</div>

---

## **Screenshot**

<!-- Replace with your own screenshots or remove this section -->
<img width="1919" height="928" alt="image" src="https://github.com/brej-29/stock-mini-terminal-streamlit/blob/main/assets/image.png" />

<img width="1919" height="922" alt="image" src="https://github.com/brej-29/stock-mini-terminal-streamlit/blob/main/assets/image-1.png" />

---

## **Table of Contents**
* [Overview](#overview)
* [Features](#features)
* [Getting Started](#getting-started)
    * [Project Structure](#project-structure)
    * [Prerequisites](#prerequisites)
    * [Installation](#installation)
    * [Configuration](#configuration)
    * [Usage](#usage)
* [Design Notes](#design-notes)
* [Limitations](#limitations)
* [License](#license)
* [Contact](#contact)
* [References](#references)

---

## **Overview**

**Stock Finder & Mini Terminal** is a Streamlit app that lets you:
- search for a stock by **name or symbol**,
- view **historical price charts** and KPIs,
- read **company fundamentals/profile**,
- and skim **recent news**.

It uses a pragmatic mix of free data sources:
- **yfinance** (price history; no API key), :contentReference[oaicite:0]{index=0}
- **Alpha Vantage** (symbol search + overview; free key), :contentReference[oaicite:1]{index=1}
- **Finnhub** (company profile + news; free key), :contentReference[oaicite:2]{index=2}
- **Financial Modeling Prep** (optional fallback for fundamentals/news; free key). :contentReference[oaicite:3]{index=3}

Secrets are stored via **Streamlit `secrets.toml`** locally and in **Community Cloud** settings on deploy. :contentReference[oaicite:4]{index=4}

<br>

### **Project Highlights**
- **Global-friendly search** with multiple providers (Yahoo-style/yfinance for prices; Alpha/FMP for fundamentals).
- **Rate-limit resilient**: retries, timeouts, and graceful fallbacks to avoid hard crashes.
- **Delightful UX**: tabs, KPIs, CSV export, and a light sprinkling of Streamlit animations (🎈).

---

## **Features**

- 🔎 **Search** by company name or symbol (provider chain & fallbacks).
- 📉 **Price & KPIs** using `yfinance` (last price, daily change, market cap). :contentReference[oaicite:5]{index=5}
- 🧾 **Fundamentals** via Alpha Vantage (Overview) and/or FMP (Profile). :contentReference[oaicite:6]{index=6}
- 📰 **Recent News** via Finnhub (with optional FMP fallback). :contentReference[oaicite:7]{index=7}
- ⭐ **Watchlist** stored in `st.session_state` (add/clear in-app).
- ⬇️ **Export** the visible price history as CSV.
- 🧠 **Caching + retries** around network calls for a smoother experience.

---

## **Getting Started**

### **Project Structure**

    stock-mini-terminal-streamlit/
    ├─ .streamlit/
    │  └─ secrets.toml               # local secrets (not committed)
    ├─ app/
    │  ├─ __init__.py
    │  ├─ services.py                # API clients & helpers (Alpha Vantage, yfinance, Finnhub, FMP)
    │  ├─ ui.py                      # charts, KPI tiles
    │  └─ utils.py                   # logging, secrets loader, format helpers
    ├─ assets/
    │  └─ placeholder.png            # optional logo
    ├─ requirements.txt
    ├─ streamlit_app.py
    └─ README.md

### **Prerequisites**
- Python **3.9+**
- Accounts/API keys (free tiers are fine):
  - **Alpha Vantage** (search + overview) :contentReference[oaicite:8]{index=8}
  - **Finnhub** (profile + news; note coverage limits by exchange) :contentReference[oaicite:9]{index=9}
  - **Financial Modeling Prep** *(optional fallback)* (profile/news) :contentReference[oaicite:10]{index=10}
- No key needed for **yfinance** (Yahoo Finance access). :contentReference[oaicite:11]{index=11}

### **Installation**
1) Create & activate a virtual environment (recommended):

        python -m venv .venv
        # Windows:
        .venv\Scripts\activate
        # macOS/Linux:
        source .venv/bin/activate

2) Install dependencies:

        pip install -r requirements.txt

### **Configuration**

Create `.streamlit/secrets.toml` (local) and paste your keys:

        ALPHA_VANTAGE_KEY = "your_alpha_vantage_api_key"
        FINNHUB_KEY = "your_finnhub_api_key"
        # Optional fallback provider:
        FMP_KEY = "your_fmp_api_key"
        OFFLINE_MODE = "false"

- **Never commit** `secrets.toml`. In Streamlit Community Cloud, paste these keys in **App → Settings → Advanced → Secrets**. :contentReference[oaicite:12]{index=12}
- Access in code with `st.secrets["KEY_NAME"]`. :contentReference[oaicite:13]{index=13}

### **Usage**

Run locally:

        streamlit run streamlit_app.py

Workflow:
1. Use the search bar to find a company by **name** or **symbol**.
2. Pick a result to load **Overview / Fundamentals / News** tabs.
3. Tune the **Period** and **Interval** in the sidebar for the price chart.
4. Add to **Watchlist**, or download **CSV** from the Overview tab.

---

## **Design Notes**

- **Why multiple providers?**  
  No single free API has perfect global coverage + generous rate limits. This app uses `yfinance` for historical pricing, **Alpha Vantage** for search/overview, **Finnhub** for profile/news, and optional **FMP** as a fundamentals/news fallback — balancing reliability and coverage. :contentReference[oaicite:14]{index=14}

- **Secrets & deployment**  
  Streamlit’s `secrets.toml` provides a simple, secure way to use keys locally and in the cloud without leaking them in your repo. :contentReference[oaicite:15]{index=15}

- **Charts & KPIs**  
  Price charts are rendered with **Altair**, and KPI tiles show last price, delta, and market cap derived from `yfinance` (or computed from the price series). :contentReference[oaicite:16]{index=16}

---

## **Limitations**

- **Rate limits**: Free tiers (e.g., Alpha Vantage) enforce daily/minute caps. Expect temporary “no data” states if exceeded. :contentReference[oaicite:17]{index=17}
- **Coverage**: Some endpoints focus on North American tickers (e.g., parts of Finnhub news). For certain NSE/BSE tickers, use FMP fallback where possible. :contentReference[oaicite:18]{index=18}
- **Yahoo terms**: `yfinance` relies on Yahoo’s public endpoints and is intended for educational/research use; review Yahoo’s terms before production use. :contentReference[oaicite:19]{index=19}

---

## **License**
This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## **Contact**
For questions or feedback, reach out on:
- LinkedIn: https://www.linkedin.com/in/brejesh-balakrishnan-7855051b9/
- GitHub: https://github.com/brej-29

---

## **References**
- Streamlit `secrets.toml` & `st.secrets`
- Alpha Vantage API (overview/search).
- Finnhub API (profile/news).
- yfinance reference (Ticker/history/usage).
- Financial Modeling Prep (Company Profile / developer docs).