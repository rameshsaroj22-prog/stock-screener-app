import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import urllib.parse
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import re

# ----------------- PAGE CONFIG (ZERO SCROLL ONE-PAGE) -----------------
st.set_page_config(
    page_title="Pro Screener | Kotak Neo Terminal & IPO Radar",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- ULTRA-PRO HIGH CONTRAST & MODEBAR LEFT CSS -----------------
st.markdown("""
    <style>
    header[data-testid="stHeader"] {
        background-color: #080c14 !important;
        border-bottom: 1px solid #1e293b !important;
    }
    header[data-testid="stHeader"] * {
        color: #ffffff !important;
    }
    header[data-testid="stHeader"] button, 
    header[data-testid="stHeader"] a {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 6px !important;
        font-weight: 800 !important;
        padding: 4px 12px !important;
    }

    /* PLOTLY TOOLBAR (ZOOM, PAN, FULLSCREEN) SHIFT TO LEFT */
    .js-plotly-plot .plotly .modebar {
        left: 12px !important;
        right: auto !important;
        top: 10px !important;
        background: rgba(17, 23, 38, 0.9) !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
        padding: 2px 6px !important;
    }

    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 0.4rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
        max-width: 100% !important;
    }
    .stApp {
        background-color: #080c14;
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* TIMEFRAME PILL BAR */
    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        gap: 6px !important;
        background: #111726 !important;
        padding: 4px 8px !important;
        border-radius: 8px !important;
        border: 1px solid #1e293b !important;
        width: fit-content !important;
        margin-bottom: 6px !important;
    }
    div[data-testid="stRadio"] label {
        background-color: transparent !important;
        border-radius: 6px !important;
        padding: 4px 14px !important;
        cursor: pointer !important;
        border: none !important;
    }
    div[data-testid="stRadio"] label p {
        color: #94a3b8 !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] label:hover p {
        color: #38bdf8 !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background-color: #2563eb !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"] p {
        color: #ffffff !important;
        font-weight: 900 !important;
    }

    /* UNIVERSAL BUTTONS */
    div[data-testid="stButton"] > button {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        padding: 6px 16px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #2563eb !important;
        border-color: #60a5fa !important;
        color: #ffffff !important;
    }
    div[data-testid="stButton"] > button p, div[data-testid="stButton"] > button span {
        color: #ffffff !important;
        font-weight: 800 !important;
    }

    /* CLICKABLE STOCK CARD BUTTON */
    .stock-click-btn button {
        background: #111726 !important;
        border: 1px solid #1e293b !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 10px 16px !important;
        font-size: 1.05rem !important;
    }
    .stock-click-btn button:hover {
        background: #162238 !important;
        border-color: #2563eb !important;
        transform: translateY(-1px) !important;
    }

    .reset-btn button {
        background: linear-gradient(90deg, #dc2626 0%, #b91c1c 100%) !important;
        border: 1px solid #ef4444 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
    }

    .share-btn button {
        background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important;
        border: 1px solid #3b82f6 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
    }

    .add-btn button {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%) !important;
        border: 1px solid #34d399 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #334155;
        margin-top: 6px;
        margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b !important;
        border: 1px solid #475569 !important;
        border-bottom: none !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 20px !important;
    }
    .stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] span {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        border-color: #60a5fa !important;
    }
    .stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] span {
        color: #ffffff !important;
        font-weight: 900 !important;
    }

    /* SEARCH BAR */
    .search-title {
        color: #38bdf8 !important;
        font-size: 1.1rem !important;
        font-weight: 900 !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stTextInput"] label {
        display: none !important;
    }

    /* STOCK CARD */
    .neo-card {
        background: linear-gradient(135deg, #131c2e 0%, #0d131f 100%);
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 10px 18px;
        margin-bottom: 6px;
    }
    .stock-title {
        font-size: 2.1rem !important;
        font-weight: 900 !important;
        color: #ffffff !important;
    }
    .badge-nse {
        background: #1e293b;
        color: #38bdf8;
        padding: 4px 10px;
        border-radius: 5px;
        font-size: 0.85rem;
        font-weight: 800;
        margin-left: 10px;
        vertical-align: middle;
    }
    .price-large {
        font-size: 2.3rem !important;
        font-weight: 900 !important;
        color: #ffffff !important;
    }
    .change-green {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 3px 12px;
        border-radius: 16px;
        font-weight: 800;
        font-size: 1rem;
        margin-left: 12px;
    }
    .change-red {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid #ef4444;
        padding: 3px 12px;
        border-radius: 16px;
        font-weight: 800;
        font-size: 1rem;
        margin-left: 12px;
    }

    .advisor-box {
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px;
    }
    .advisor-header {
        font-size: 1.15rem;
        font-weight: 800;
        color: #ffffff;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 8px;
        margin-bottom: 10px;
    }
    .level-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #161f30;
        font-size: 0.95rem;
    }

    .ipo-box {
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .badge-apply {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 4px 10px;
        border-radius: 16px;
        font-weight: 800;
        font-size: 0.85rem;
    }
    .badge-caution {
        background: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid #f59e0b;
        padding: 4px 10px;
        border-radius: 16px;
        font-weight: 800;
        font-size: 0.85rem;
    }
    .badge-avoid {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid #ef4444;
        padding: 4px 10px;
        border-radius: 16px;
        font-weight: 800;
        font-size: 0.85rem;
    }

    div[data-testid="stMetric"] {
        background-color: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 6px 12px;
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 1.35rem !important;
        font-weight: 800 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- ACCURATE LISTING DATES REGISTRY -----------------
# Strictly prevents any pre-IPO ghost candles before official listing date
STOCK_LISTING_REGISTRY = {
    "JPL": datetime.date(2026, 10, 5),          # JPL strictly listed October 2026
    "SWIGGY": datetime.date(2026, 11, 4),       # Swiggy Nov 2026
    "NTPCGREEN": datetime.date(2026, 11, 10),   # NTPC Green Nov 2026
    "VIKRAMSOLR": datetime.date(2025, 8, 26),   # Vikram Solar Aug 2025
    "HYUNDAI": datetime.date(2024, 10, 22),     # Hyundai Oct 2024
    "BLSE": datetime.date(2024, 2, 6),          # BLS E-Services Feb 2024
    "TATATECH": datetime.date(2023, 11, 30),    # Tata Tech Nov 2023
    "JIOFIN": datetime.date(2023, 8, 21),       # Jio Fin Aug 2023
    "ZOMATO": datetime.date(2021, 7, 23)        # Zomato July 2021
}

# ----------------- SESSION STATE WATCHLIST -----------------
DEFAULT_WATCHLIST = [
    {"symbol": "JPL", "name": "Jio Platforms Limited", "exchange": "NSE", "yf": "JPL.NS", "price": 1412.70},
    {"symbol": "BLS", "name": "BLS International Services Ltd", "exchange": "NSE", "yf": "BLS.NS", "price": 372.50},
    {"symbol": "BLSE", "name": "BLS E-Services Ltd", "exchange": "NSE", "yf": "BLSE.NS", "price": 242.00},
    {"symbol": "VIKRAMSOLR", "name": "Vikram Solar Ltd", "exchange": "BSE", "yf": "VIKRAMSOLR.BO", "price": 435.00},
    {"symbol": "ORIENTCABL", "name": "Orient Cables (India) Ltd", "exchange": "NSE", "yf": "ORIENTCABL.NS", "price": 185.00},
    {"symbol": "COALINDIA", "name": "Coal India Limited", "exchange": "NSE", "yf": "COALINDIA.NS", "price": 408.00},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE", "yf": "TCS.NS", "price": 4145.00},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "exchange": "NSE", "yf": "ICICIBANK.NS", "price": 1424.10}
]

if "my_watchlist" not in st.session_state:
    st.session_state.my_watchlist = DEFAULT_WATCHLIST

if "active_scrip" not in st.session_state:
    st.session_state.active_scrip = st.session_state.my_watchlist[0]

# ----------------- CLEAN HELPER TO SWITCH STOCKS (PREVENTS LINE TRUNCATION) -----------------
def open_stock_terminal(symbol, name, exchange="NSE", yf_sym=None, price=100.0):
    yf_clean = yf_sym if yf_sym else (f"{symbol}.BO" if exchange == "BSE" else f"{symbol}.NS")
    st.session_state.active_scrip = {
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
        "yf": yf_clean,
        "price": float(price)
    }
    st.rerun()

# ----------------- TRADINGVIEW & NSE REAL-TIME SEARCH -----------------
@st.cache_data(ttl=60)
def search_tradingview_and_nse(query):
    clean_q = query.strip()
    if not clean_q:
        return []

    results = []
    try:
        encoded_q = urllib.parse.quote(clean_q)
        tv_search_url = f"https://symbol-search.tradingview.com/symbol_search/v3/?text={encoded_q}&hl=1&exchange=NSE,BSE&lang=en"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(tv_search_url, headers=headers, timeout=3.5)
        if r.status_code == 200:
            symbols = r.json().get("symbols", [])
            for s in symbols:
                sym = s.get("symbol", "").upper()
                desc = s.get("description", "")
                exch = s.get("exchange", "NSE").upper()
                stype = s.get("type", "").lower()
                if exch in ["NSE", "BSE"] and (stype in ["stock", "equity", "dr", "fund"] or not stype):
                    yf_sym = f"{sym}.NS" if exch == "NSE" else f"{sym}.BO"
                    results.append({
                        "symbol": sym,
                        "name": desc if desc else f"{sym} Limited",
                        "exchange": exch,
                        "yf": yf_sym
                    })
    except Exception:
        pass

    if len(results) < 2:
        try:
            yf_search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(clean_q)}&quotesCount=8"
            r = requests.get(yf_search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
            if r.status_code == 200:
                quotes = r.json().get("quotes", [])
                for q in quotes:
                    sym = q.get("symbol", "")
                    name = q.get("shortname") or q.get("longname") or sym
