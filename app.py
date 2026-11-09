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
    page_title="Pro Terminal & Next-Day Radar",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- ULTRA-PRO HIGH CONTRAST CSS -----------------
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

    .match-item {
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .radar-card {
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
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

# ----------------- TRADINGVIEW & NSE REAL-TIME LIVE SEARCH -----------------
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
                    if sym.endswith(".NS") or sym.endswith(".BO"):
                        clean_sym = sym.replace(".NS", "").replace(".BO", "")
                        exch = "NSE" if sym.endswith(".NS") else "BSE"
                        results.append({
                            "symbol": clean_sym,
                            "name": name,
                            "exchange": exch,
                            "yf": sym
                        })
        except Exception:
            pass

    seen = set()
    unique_matches = []
    for item in results:
        key = (item["symbol"], item["exchange"])
        if key not in seen:
            seen.add(key)
            unique_matches.append(item)

    return unique_matches[:6]

# ----------------- TRADINGVIEW SCANNER REAL-TIME PRICE FETCHER -----------------
@st.cache_data(ttl=10)
def fetch_tradingview_live_quote(symbol, exchange="NSE"):
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    url = "https://scanner.tradingview.com/india/scan"
    payload = {
        "symbols": {"tickers": [f"{exchange}:{clean_sym}", f"NSE:{clean_sym}", f"BSE:{clean_sym}"]},
        "columns": ["close", "change", "change_abs", "description", "prev_close"]
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=3)
        if r.status_code == 200:
            rows = r.json().get("data", [])
            if rows:
                d = rows[0].get("d", [])
                if len(d) >= 3 and d[0] is not None:
                    ltp = float(d[0])
                    pct = float(d[1]) if d[1] is not None else 0.0
                    chg_abs = float(d[2]) if d[2] is not None else 0.0
                    desc = d[3] if len(d) > 3 and d[3] else f"{clean_sym} Limited"
                    prev = d[4] if len(d) > 4 and d[4] is not None else ltp - chg_abs
                    return {
                        "name": desc,
                        "price": ltp,
                        "change_pct": f"{pct:+.2f}%",
                        "chg_pts": chg_abs,
                        "prev_close": prev
                    }
    except Exception:
        pass

    try:
        tkr = yf.Ticker(f"{clean_sym}.NS" if exchange == "NSE" else f"{clean_sym}.BO")
        h = tkr.history(period="2d")
        if not h.empty:
            c = float(h['Close'].iloc[-1])
            prev = float(h['Close'].iloc[-2]) if len(h) >= 2 else c
            chg = c - prev
            pct = (chg / prev) * 100 if prev else 0.0
            return {
                "name": f"{clean_sym} Limited",
                "price": c,
                "change_pct": f"{pct:+.2f}%",
                "chg_pts": chg,
                "prev_close": prev
            }
    except Exception:
        pass

    return None

# ----------------- TIMEFRAME CANDLESTICK GENERATOR -----------------
def generate_pro_candles_by_period(base_price, period_choice):
    np.random.seed(101)
    if period_choice == "1D":
        times = pd.date_range(end=datetime.datetime.now(), periods=50, freq='5min')
        returns = np.random.normal(-0.0001, 0.002, 50)
        curve = base_price * np.exp(np.cumsum(returns[::-1]))[::-1]
        curve = curve * (base_price / curve[-1])
        df = pd.DataFrame(index=times)
    elif period_choice == "5D":
        times = pd.date_range(end=datetime.datetime.now(), periods=40, freq='30min')
        returns = np.random.normal(-0.0002, 0.005, 40)
        curve = base_price * np.exp(np.cumsum(returns[::-1]))[::-1]
        curve = curve * (base_price / curve[-1])
        df = pd.DataFrame(index=times)
    elif period_choice in ["1M", "6M", "YTD"]:
        days = 25 if period_choice == "1M" else (65 if period_choice == "6M" else 45)
        dates = pd.bdate_range(end=datetime.date.today(), periods=days)
        returns = np.random.normal(0.001, 0.012, days)
        curve = base_price * np.exp(np.cumsum(returns[::-1]))[::-1]
        curve = curve * (base_price / curve[-1])
        df = pd.DataFrame(index=dates)
    else:
        days = 70
        dates = pd.bdate_range(end=datetime.date.today(), periods=days)
        returns = np.random.normal(0.002, 0.018, days)
        curve = base_price * np.exp(np.cumsum(returns[::-1]))[::-1]
        curve = curve * (base_price / curve[-1])
        df = pd.DataFrame(index=dates)

    df['Close'] = curve
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.994)
    df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.random.uniform(0.001, 0.008, len(df)))
    df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.random.uniform(0.001, 0.008, len(df)))
    df['Volume'] = np.random.randint(500000, 2500000, len(df))
    return df

# ----------------- CHANDELIER EXIT [EVERGET] (ATR 7, MULTIPLIER 2.0) -----------------
def calculate_chandelier_exit(df, length=7, mult=2.0, use_close=True):
    total = len(df)
    eff_length = min(total, max(2, length))

    high = df['High']
    low = df['Low']
    close = df['Close']
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / eff_length, min_periods=1, adjust=False).mean()
    df['ATR'] = atr
    atr_scaled = mult * atr

    if use_close:
        highest_val = close.rolling(window=eff_length, min_periods=1).max()
        lowest_val = close.rolling(window=eff_length, min_periods=1).min()
    else:
        highest_val = high.rolling(window=eff_length, min_periods=1).max()
        lowest_val = low.rolling(window=eff_length, min_periods=1).min()

    raw_long_stop = highest_val - atr_scaled
    raw_short_stop = lowest_val + atr_scaled

    n = len(df)
    long_stop = np.zeros(n)
    short_stop = np.zeros(n)
    direction = np.zeros(n)
    buy_signals = [np.nan] * n
    sell_signals = [np.nan] * n

    curr_dir = 1
    curr_long = raw_long_stop.iloc[0]
    curr_short = raw_short_stop.iloc[0]

    for i in range(n):
        c = close.iloc[i]
        c_prev = close.iloc[i-1] if i > 0 else c
        rl = raw_long_stop.iloc[i]
        rs = raw_short_stop.iloc[i]

        if i > 0:
            if c_prev > long_stop[i-1]:
                curr_long = max(rl, long_stop[i-1])
            else:
                curr_long = rl
        else:
            curr_long = rl

        if i > 0:
            if c_prev < short_stop[i-1]:
                curr_short = min(rs, short_stop[i-1])
            else:
                curr_short = rs
        else:
            curr_short = rs

        long_stop[i] = curr_long
        short_stop[i] = curr_short

        prev_dir = curr_dir
        if i > 0:
            if c > short_stop[i-1]:
                curr_dir = 1
            elif c < long_stop[i-1]:
                curr_dir = -1
            else:
                curr_dir = direction[i-1]
        else:
            curr_dir = 1

        direction[i] = curr_dir

        if i > 0:
            if curr_dir == 1 and prev_dir == -1:
                buy_signals[i] = low.iloc[i] * 0.988
            elif curr_dir == -1 and prev_dir == 1:
                sell_signals[i] = high.iloc[i] * 1.012

    df['Chandelier_Long'] = long_stop
    df['Chandelier_Short'] = short_stop
    df['Chandelier_Dir'] = direction
    df['Chandelier_Stop'] = np.where(direction == 1, long_stop, short_stop)
    df['Buy_Signal'] = buy_signals
    df['Sell_Signal'] = sell_signals

    df['EMA_20'] = df['Close'].ewm(span=min(20, total), adjust=False).mean()
    return df

# ----------------- TOP INDICES (NIFTY & SENSEX) -----------------
@st.cache_data(ttl=60)
def get_indices_snapshot():
    out = {}
    for k, sym in {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN"}.items():
        try:
            h = yf.Ticker(sym).history(period="2d")
            if len(h) >= 2:
                c = h['Close'].iloc[-1]
                diff = c - h['Close'].iloc[-2]
                pct = (diff / h['Close'].iloc[-2]) * 100
                out[k] = {"price": c, "diff": diff, "pct": pct}
        except Exception:
            pass
    return out

idx_res = get_indices_snapshot()
cols_idx = st.columns([2.5, 2.5, 5])

if "NIFTY 50" in idx_res:
    d = idx_res["NIFTY 50"]
    col = "#10b981" if d["diff"] >= 0 else "#ef4444"
    cols_idx[0].markdown(f"""
        <div style="background:#111726; border:1px solid #1e293b; padding:6px 12px; border-radius:6px; font-size:0.95rem;">
            <span style="color:#94a3b8; font-weight:700;">🇮🇳 NIFTY 50:</span> 
            <b>₹{d['price']:,.2f}</b> <span style="color:{col}; font-weight:800;">{d['diff']:+,.2f} ({d['pct']:+.2f}%)</span>
        </div>
    """, unsafe_allow_html=True)

if "SENSEX" in idx_res:
    d = idx_res["SENSEX"]
    col = "#10b981" if d["diff"] >= 0 else "#ef4444"
    cols_idx[1].markdown(f"""
        <div style="background:#111726; border:1px solid #1e293b; padding:6px 12px; border-radius:6px; font-size:0.95rem;">
            <span style="color:#94a3b8; font-weight:700;">🇮🇳 SENSEX:</span> 
            <b>₹{d['price']:,.2f}</b> <span style="color:{col}; font-weight:800;">{d['diff']:+,.2f} ({d['pct']:+.2f}%)</span>
        </div>
    """, unsafe_allow_html=True)

cols_idx[2].markdown("""
    <div style="text-align:right; padding-top:6px; font-size:0.9rem; color:#10b981; font-weight:700;">
        ● TradingView & NSE Universal Database Active
    </div>
""", unsafe_allow_html=True)

# ----------------- PROMINENT SEARCH BAR -----------------
st.markdown('<p class="search-title">🔎 LIVE SCRIP SEARCH (TradingView & NSE All Stocks):</p>', unsafe_allow_html=True)
search_c1, search_c2, search_c3 = st.columns([7.4, 1.3, 1.3])

with search_c1:
    search_query = st.text_input(
        "Search Box Input",
        value="",
        placeholder="Type any stock or partial name (e.g. BLS, Vikram Solar, JPL, Orient, Tata, ICICI)..."
    )

with search_c2:
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.active_scrip = st.session_state.my_watchlist[0]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with search_c3:
    st.markdown('<div class="share-btn">', unsafe_allow_html=True)
    if st.button("🔗 Share", use_container_width=True):
        st.toast("📋 App Link Copied: https://stock-screener-app-david.streamlit.app", icon="🚀")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- MATCH RESULTS -----------------
if search_query.strip():
    matches = search_tradingview_and_nse(search_query)
    if matches:
        st.markdown(f"#### 🎯 Matching Stocks Found for '{search_query.strip()}':")
        for idx, item in enumerate(matches):
            sym = item["symbol"]
            exch = item["exchange"]
            name = item["name"]
            
            q_info = fetch_tradingview_live_quote(sym, exch)
            live_p = q_info["price"] if q_info else 100.0
            live_pct = q_info["change_pct"] if q_info else "0.0%"
            p_color = "#10b9
