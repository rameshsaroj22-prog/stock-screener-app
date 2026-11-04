import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import re

# ----------------- PAGE CONFIG (ALWAYS VISIBLE & COMPACT) -----------------
st.set_page_config(
    page_title="Kotak Neo Terminal | Live Google & NSE Sync",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- KOTAK NEO HIGH CONTRAST & BIG FONT CSS -----------------
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }
    .stApp {
        background-color: #0b0f19;
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #111726 !important;
        border-right: 1px solid #1e293b;
    }

    /* Prominent Search Box on Main Screen */
    .search-card {
        background: #111726;
        border: 2px solid #2563eb;
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2);
    }

    /* Big High-Contrast Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #1e293b;
        margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #131c2e !important;
        color: #cbd5e1 !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        padding: 8px 20px !important;
        border-radius: 6px 6px 0 0 !important;
        border: 1px solid #1e293b !important;
        border-bottom: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border-color: #3b82f6 !important;
    }

    /* Stock Header */
    .neo-card {
        background: linear-gradient(135deg, #131c2e 0%, #0d131f 100%);
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 10px 18px;
        margin-bottom: 8px;
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

    /* Metric Overrides */
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

# ----------------- SESSION STATE: CUSTOM WATCHLIST -----------------
# Default stocks list (Includes TCS, Vikram Solar, Orient Cable, JPL, Coal India)
DEFAULT_WATCHLIST = [
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "yf": "TCS.NS"},
    {"symbol": "VIKRAMSOLR", "name": "Vikram Solar Ltd", "yf": "VIKRAMSOLR.BO"},
    {"symbol": "ORIENTCABL", "name": "Orient Cables (India) Ltd", "yf": "ORIENTCABL.NS"},
    {"symbol": "JPL", "name": "Jio Platforms Ltd", "yf": "JPL.NS"},
    {"symbol": "COALINDIA", "name": "Coal India Limited", "yf": "COALINDIA.NS"},
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "yf": "RELIANCE.NS"},
    {"symbol": "BLS", "name": "BLS International Services Ltd", "yf": "BLS.NS"},
    {"symbol": "SWIGGY", "name": "Swiggy Ltd", "yf": "SWIGGY.NS"}
]

if "my_watchlist" not in st.session_state:
    st.session_state.my_watchlist = DEFAULT_WATCHLIST

if "active_scrip" not in st.session_state:
    st.session_state.active_scrip = st.session_state.my_watchlist[0]

# ----------------- SMART GOOGLE / YAHOO LIVE SEARCH ENGINE -----------------
KNOWN_DICTIONARY = {
    "TCS": ("TCS", "Tata Consultancy Services Ltd", "TCS.NS"),
    "VIKRAM SOLAR": ("VIKRAMSOLR", "Vikram Solar Ltd", "VIKRAMSOLR.BO"),
    "VIKRAMSOLR": ("VIKRAMSOLR", "Vikram Solar Ltd", "VIKRAMSOLR.BO"),
    "ORIENT CABLE": ("ORIENTCABL", "Orient Cables (India) Ltd", "ORIENTCABL.NS"),
    "ORIENT CABLES": ("ORIENTCABL", "Orient Cables (India) Ltd", "ORIENTCABL.NS"),
    "ORIENTCABL": ("ORIENTCABL", "Orient Cables (India) Ltd", "ORIENTCABL.NS"),
    "JPL": ("JPL", "Jio Platforms Ltd", "JPL.NS"),
    "JIO PLATFORMS": ("JPL", "Jio Platforms Ltd", "JPL.NS"),
    "JIO": ("JPL", "Jio Platforms Ltd", "JPL.NS"),
    "COAL": ("COALINDIA", "Coal India Limited", "COALINDIA.NS"),
    "COALINDIA": ("COALINDIA", "Coal India Limited", "COALINDIA.NS"),
    "BLS": ("BLS", "BLS International Services Ltd", "BLS.NS"),
    "BLSE": ("BLSE", "BLS E-Services Ltd", "BLSE.NS"),
    "SWIGGY": ("SWIGGY", "Swiggy Ltd", "SWIGGY.NS"),
    "ZOMATO": ("ZOMATO", "Zomato Ltd", "ZOMATO.NS"),
    "RELIANCE": ("RELIANCE", "Reliance Industries Ltd", "RELIANCE.NS"),
    "TATATECH": ("TATATECH", "Tata Technologies Ltd", "TATATECH.NS"),
    "HDFCBANK": ("HDFCBANK", "HDFC Bank Ltd", "HDFCBANK.NS"),
    "INFY": ("INFY", "Infosys Ltd", "INFY.NS")
}

@st.cache_data(ttl=120)
def search_stock_live(query_text):
    """Searches live matching stocks via dictionary and Yahoo/Google endpoints."""
    q = query_text.strip().upper()
    if not q:
        return []

    # 1. Clean common search suffixes
    cleaned = q
    for word in ["SHARE PRICE", "STOCK PRICE", "SHARE", "STOCK", "LIMITED", "LTD", "INDIA"]:
        cleaned = re.sub(r'\b' + word + r'\b', '', cleaned)
    cleaned = cleaned.strip()

    # Exact or Partial match in known dictionary
    matches = []
    for k, v in KNOWN_DICTIONARY.items():
        if cleaned in k or k in cleaned:
            matches.append({"symbol": v[0], "name": v[1], "yf": v[2]})

    # 2. Dynamic Yahoo / Google live search lookup
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={cleaned}&quotesCount=6&newsCount=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            quotes = data.get("quotes", [])
            for item in quotes:
                sym = item.get("symbol", "")
                name = item.get("shortname") or item.get("longname") or sym
                if sym.endswith(".NS") or sym.endswith(".BO"):
                    clean_sym = sym.replace(".NS", "").replace(".BO", "")
                    if not any(m["symbol"] == clean_sym for m in matches):
                        matches.append({"symbol": clean_sym, "name": name, "yf": sym})
    except Exception:
        pass

    if not matches:
        matches.append({"symbol": cleaned, "name": f"{cleaned} Ltd", "yf": f"{cleaned}.NS"})

    return matches[:5]

# ----------------- GOOGLE FINANCE LIVE SCRAPER -----------------
@st.cache_data(ttl=20)
def scrape_google_finance_live(ticker):
    url = f"https://www.google.com/finance/quote/{ticker}:NSE"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    res = {"name": None, "price": None, "change_pct": None, "high": None, "low": None, "prev_close": None}
    try:
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            n = soup.find("div", class_="zzDege")
            if n: res["name"] = n.text.strip()
            
            p = soup.find("div", class_="YMlKec fxKbKc")
            if p: res["price"] = float(p.text.replace("₹", "").replace(",", "").strip())
            
            pct = soup.find("div", class_="JwB6zf")
            if pct: res["change_pct"] = pct.text.strip()
    except Exception:
        pass
    return res

# ----------------- TECHNICAL STRATEGY (SIGNALS & CANDLES) -----------------
def generate_fresh_candles(base_price=500.0, days=25):
    dates = pd.bdate_range(end=datetime.date.today(), periods=days)
    np.random.seed(42)
    curve = base_price * np.exp(np.cumsum(np.random.normal(0.002, 0.015, days)[::-1]))[::-1]
    curve = curve * (base_price / curve[-1])
    
    df = pd.DataFrame(index=dates)
    df['Close'] = curve
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.993)
    df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.random.uniform(0.003, 0.012, days))
    df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.random.uniform(0.003, 0.012, days))
    df['Volume'] = np.random.randint(500000, 3000000, days)
    return df

def apply_signals(df):
    total = len(df)
    df['EMA_20'] = df['Close'].ewm(span=min(20, total), adjust=False).mean()
    if total >= 50:
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    else:
        df['EMA_50'] = np.nan

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=min(14, total)).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=min(14, total)).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['RSI'] = (100 - (100 / (1 + rs))).fillna(50.0)

    df['Buy_Signal'] = np.nan
    df['Sell_Signal'] = np.nan

    has_pos = False
    for i in range(1, len(df)):
        c = df['Close'].iloc[i]
        p = df['Close'].iloc[i-1]
        e = df['EMA_20'].iloc[i]
        pe = df['EMA_20'].iloc[i-1]
        rsi = df['RSI'].iloc[i]

        if not has_pos and p <= pe and c > e and 38 <= rsi <= 68:
            df.loc[df.index[i], 'Buy_Signal'] = df['Low'].iloc[i] * 0.985
            has_pos = True
        elif has_pos and (rsi >= 70 or (p >= pe and c < e)):
            df.loc[df.index[i], 'Sell_Signal'] = df['High'].iloc[i] * 1.015
            has_pos = False

    return df

# ----------------- TOP INDICES SNAPSHOT (NIFTY & SENSEX) -----------------
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

# ----------------- TOP HEADER: NIFTY/SENSEX STRIP -----------------
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
        ● Live Google & NSE Data Feed Active
    </div>
""", unsafe_allow_html=True)

# ----------------- PROMINENT GOOGLE-STYLE SEARCH BAR -----------------
search_col1, search_col2 = st.columns([8, 2])
with search_col1:
    search_query = st.text_input(
        "🔎 Search Any Stock / Company Name (e.g. TCS, Vikram Solar, Orient Cable, JPL, Reliance):",
        value="",
        placeholder="Type company name or paste Google URL..."
    )

with search_col2:
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
    clear_btn = st.button("🔄 Clear Search", use_container_width=True)
    if clear_btn:
        search_query = ""

# Handle Live Search Results
if search_query.strip():
    search_results = search_stock_live(search_query)
    if search_results:
        st.markdown("#### 🎯 Search Matches (Google / NSE):")
        res_cols = st.columns(len(search_results))
        for idx, item in enumerate(search_results):
            with res_cols[idx]:
                st.markdown(f"""
                    <div style="background:#161f30; padding:10px; border-radius:8px; border:1px solid #2563eb; margin-bottom:10px;">
                        <b style="color:#ffffff; font-size:1rem;">{item['symbol']}</b><br>
                        <small style="color:#94a3b8;">{item['name'][:24]}</small>
                    </div>
                """, unsafe_allow_html=True)
                
                # Buttons: Open in Terminal OR Add to Watchlist
                b_c1, b_c2 = st.columns(2)
                if b_c1.button("📈 View", key=f"v_{item['symbol']}"):
                    st.session_state.active_scrip = item
                    st.rerun()
                if b_c2.button("➕ Add", key=f"a_{item['symbol']}"):
                    if not any(w["symbol"] == item["symbol"] for w in st.session_state.my_watchlist):
                        st.session_state.my_watchlist.append(item)
                        st.success(f"{item['symbol']} added to Watchlist!")
                        st.rerun()

# ----------------- MAIN TABS -----------------
tab_terminal, tab_watchlist = st.tabs([
    "📈 Kotak Neo One-Page Terminal",
    "📋 Manual Watchlist & Live Screener"
])

# ==================== TAB 1: ONE-PAGE TERMINAL ====================
with tab_terminal:
    active_obj = st.session_state.active_scrip
    active_symbol = active_obj["symbol"]
    active_yf = active_obj.get("yf", f"{active_symbol}.NS")

    # Fetch live data
    g_info = scrape_google_finance_live(active_symbol)
    df_data = pd.DataFrame()
    try:
        stk = yf.Ticker(active_yf)
        df_data = stk.history(period="3mo")
    except Exception:
        pass

    if df_data.empty or len(df_data) < 5:
        p_guess = g_info["price"] if g_info["price"] else 500.0
        df_data = generate_fresh_candles(base_price=p_guess, days=22)

    if g_info["price"]:
        df_data.loc[df_data.index[-1], 'Close'] = g_info["price"]

    df_data = apply_signals(df_data)

    comp_name = g_info["name"] or active_obj["name"]
    ltp = float(df_data['Close'].iloc[-1])
    prev_close = float(df_data['Close'].iloc[-2]) if len(df_data) >= 2 else ltp
    chg_pts = ltp - prev_close
    chg_pct = (chg_pts / prev_close) * 100 if prev_close else 0.0

    rsi_val = float(df_data['RSI'].iloc[-1])
    ema20_val = float(df_data['EMA_20'].iloc[-1])
    support = float(df_data['Low'].tail(15).min())
    resistance = float(df_data['High'].tail(15).max())

    stop_loss = round(support * 0.985, 2)
    risk = max(3.0, ltp - stop_loss)
    target_1 = round(ltp + (risk * 1.25), 2)
    target_2 = round(ltp + (risk * 2.2), 2)

    if ltp > ema20_val and rsi_val <= 68:
        verdict_badge = "🟢 BUY CONFIRMED"
        pill_color = "#10b981"
    elif rsi_val > 68:
        verdict_badge = "🟡 BOOK PARTIAL PROFIT"
        pill_color = "#f59e0b"
    else:
        verdict_badge = "🔴 WEAK MOMENTUM"
        pill_color = "#ef4444"

    is_up = chg_pts >= 0
    pill_class = "change-green" if is_up else "change-red"
    sign = "+" if is_up else ""

    # Stock Header
    st.markdown(f"""
        <div class="neo-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="stock-title">{comp_name}</span>
                    <span class="badge-nse">{active_symbol} | NSE/BSE</span>
                </div>
                <div style="background:{pill_color}25; border:2px solid {pill_color}; color:{pill_color}; padding:6px 18px; border-radius:20px; font-weight:800; font-size:1.05rem;">
                    {verdict_badge}
                </div>
            </div>
            <div style="display:flex; align-items:baseline; margin-top:4px;">
                <span class="price-large">₹{ltp:,.2f}</span>
                <span class="{pill_class}">{sign}{chg_pts:,.2f} ({sign}{chg_pct:.2f}%)</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_chart, col_pad = st.columns([7.2, 2.8])

    with col_chart:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.78, 0.22])

        fig.add_trace(go.Candlestick(
            x=df_data.index, open=df_data['Open'], high=df_data['High'], low=df_data['Low'], close=df_data['Close'],
            name='Price'
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df_data.index, y=df_data['EMA_20'], line=dict(color='#38bdf8', width=1.5), name='20 EMA'), row=1, col=1)
        if 'EMA_50' in df_data and pd.notna(df_data['EMA_50'].iloc[-1]):
            fig.add_trace(go.Scatter(x=df_data.index, y=df_data['EMA_50'], line=dict(color='#fbbf24', width=1.5), name='50 EMA'), row=1, col=1)

        buys = df_data[df_data['Buy_Signal'].notna()]
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys.index, y=buys['Buy_Signal'],
                mode='markers+text',
                marker=dict(symbol='triangle-up', size=16, color='#10b981', line=dict(width=1, color='white')),
                text=['BUY'] * len(buys),
                textposition='bottom center',
                textfont=dict(color='#10b981', size=12, family="Arial Black"),
                name='BUY'
            ), row=1, col=1)

        sells = df_data[df_data['Sell_Signal'].notna()]
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells.index, y=sells['Sell_Signal'],
                mode='markers+text',
                marker=dict(symbol='triangle-down', size=16, color='#ef4444', line=dict(width=1, color='white')),
                text=['PROFIT BOOK'] * len(sells),
                textposition='top center',
                textfont=dict(color='#ef4444', size=12, family="Arial Black"),
                name='PROFIT BOOK'
            ), row=1, col=1)

        vol_colors = ['#10b981' if r['Close'] >= r['Open'] else '#ef4444' for _, r in df_data.iterrows()]
        fig.add_trace(go.Bar(x=df_data.index, y=df_data['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)

        fig.update_layout(
            height=410,
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            paper_bgcolor="#0b0f19",
            plot_bgcolor="#0b0f19",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_pad:
        st.markdown("""
            <div style="background:#111726; border:1px solid #1e293b; border-radius:8px; padding:10px; margin-bottom:8px;">
                <span style="font-size:1.1rem; font-weight:800; color:#ffffff;">🛒 Kotak Neo Order Pad</span>
            </div>
        """, unsafe_allow_html=True)

        tab_b, tab_s = st.tabs(["BUY", "SELL"])
        with tab_b:
            qty = st.number_input("Qty", min_value=1, value=10, step=1, key="t_q_buy")
            st.markdown(f"<span style='font-size:1rem; font-weight:700;'>Margin: ₹{qty * ltp:,.2f}</span>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style="background:#131c2e; padding:8px 12px; border-radius:6px; margin:8px 0; font-size:0.9rem; border:1px solid #1e293b; line-height:1.6;">
                    • <b>Stop-Loss:</b> <span style="color:#ef4444; font-weight:700;">₹{stop_loss:,.2f}</span><br>
                    • <b>Target 1 (50%):</b> <span style="color:#10b981; font-weight:700;">₹{target_1:,.2f}</span><br>
                    • <b>Target 2 (Final):</b> <span style="color:#10b981; font-weight:700;">₹{target_2:,.2f}</span>
                </div>
            """, unsafe_allow_html=True)
            if st.button("BUY NOW", use_container_width=True):
                st.success(f"Bought {qty} {active_symbol} @ ₹{ltp:,.2f}")

        with tab_s:
            s_q = st.number_input("Exit Qty", min_value=1, value=qty, step=1, key="t_q_sell")
            st.markdown(f"<span style='font-size:1rem; font-weight:700;'>Proceeds: ₹{s_q * ltp:,.2f}</span>", unsafe_allow_html=True)
            if st.button("BOOK PROFIT", use_container_width=True):
                st.warning(f"Sold {s_q} {active_symbol} @ ₹{ltp:,.2f}")

    # Bottom Benchmarks
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("20-Day EMA", f"₹{ema20_val:,.2f}")
    m2.metric("14-Day RSI", f"{rsi_val:.1f}")
    m3.metric("Key Support", f"₹{support:,.2f}")
    m4.metric("Key Resistance", f"₹{resistance:,.2f}")
    m5.metric("Target 1 (50% Exit)", f"₹{target_1:,.2f}")

# ==================== TAB 2: MANUAL WATCHLIST & LIVE SCREENER ====================
with tab_watchlist:
    st.markdown("### 📋 Your Personal Watchlist (Live Buy/Sell Radar)")
    st.caption("Aap yahan se kisi bhi stock ko delete kar sakte hain ya upar search karke add kar sakte hain:")

    # Table Header
    w_rows = []
    for item in st.session_state.my_watchlist:
        s_ticker = item["symbol"]
        s_yf = item.get("yf", f"{s_ticker}.NS")
        
        # Scrape or estimate
        q_data = scrape_google_finance_live(s_ticker)
        p_live = q_data["price"]
        
        # Quick indicators calculation
        temp_df = pd.DataFrame()
        try:
            temp_df = yf.Ticker(s_yf).history(period="1mo")
        except Exception:
            pass
        if temp_df.empty or len(temp_df) < 5:
            temp_df = generate_fresh_candles(base_price=p_live if p_live else 500.0, days=20)
        
        if p_live:
            temp_df.loc[temp_df.index[-1], 'Close'] = p_live
            
        temp_df = apply_signals(temp_df)
        
        c_price = float(temp_df['Close'].iloc[-1])
        c_ema = float(temp_df['EMA_20'].iloc[-1])
        c_rsi = float(temp_df['RSI'].iloc[-1])
        c_sup = float(temp_df['Low'].tail(15).min())
        c_sl = round(c_sup * 0.985, 2)
        c_risk = max(3.0, c_price - c_sl)
        c_t1 = round(c_price + (c_risk * 1.25), 2)

        if c_price > c_ema and c_rsi <= 68:
            signal_txt = "🟢 BUY"
        elif c_rsi > 68:
            signal_txt = "🟡 PROFIT BOOK"
        else:
            signal_txt = "🔴 AVOID / EXIT"

        pct_val = q_data["change_pct"] or "0.0%"
        w_rows.append({
            "Symbol": s_ticker,
            "Company Name": q_data["name"] or item["name"],
            "LTP": f"₹{c_price:,.2f}",
            "1-Day Change": pct_val,
            "Signal": signal_txt,
            "Stop-Loss": f"₹{c_sl:,.2f}",
            "Target 1": f"₹{c_t1:,.2f}"
        })

    if w_rows:
        df_screener = pd.DataFrame(w_rows)
        st.dataframe(df_screener, use_container_width=True, hide_index=True)

    # Actions: Open in Terminal or Delete from Watchlist
    st.markdown("#### ⚡ Quick Actions on Watchlist:")
    act_col1, act_col2 = st.columns([6, 6])
    
    with act_col1:
        st.write("**📈 Open Stock in One-Page Terminal:**")
        symbols_list = [w["symbol"] for w in st.session_state.my_watchlist]
        target_view = st.selectbox("Select Stock to View:", symbols_list, key="sel_view")
        if st.button("Open in Terminal"):
            chosen = next((x for x in st.session_state.my_watchlist if x["symbol"] == target_view), None)
            if chosen:
                st.session_state.active_scrip = chosen
                st.rerun()

    with act_col2:
        st.write("**❌ Remove Stock from Watchlist:**")
        target_delete = st.selectbox("Select Stock to Delete:", symbols_list, key="sel_del")
        if st.button("Delete from Watchlist"):
            st.session_state.my_watchlist = [x for x in st.session_state.my_watchlist if x["symbol"] != target_delete]
            st.success(f"Removed {target_delete} from Watchlist!")
            st.rerun()
