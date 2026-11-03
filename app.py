import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Kotak Neo Terminal | Pro Screener",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- KOTAK NEO SIGNATURE DARK THEME -----------------
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f17;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #111622 !important;
        border-right: 1px solid #1e293b;
    }
    .neo-header {
        background: linear-gradient(135deg, #131c2e 0%, #0d131f 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 16px;
    }
    .company-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
    }
    .company-badge {
        background: #1e293b;
        color: #38bdf8;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-left: 10px;
    }
    .ltp-price {
        font-size: 2.2rem;
        font-weight: 800;
        color: #f8fafc;
        margin: 6px 0 0 0;
    }
    .pill-up { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; padding: 3px 10px; border-radius: 20px; font-weight: 700; }
    .pill-down { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; padding: 3px 10px; border-radius: 20px; font-weight: 700; }
    
    div[data-testid="stMetric"] {
        background-color: #131926;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px 14px;
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 0.82rem; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #38bdf8 !important; font-size: 1.25rem; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# ----------------- SMART SYMBOL RESOLVER -----------------
COMMON_ALIASES = {
    "COAL": "COALINDIA",
    "COALINDIA": "COALINDIA",
    "JPL": "JIOFIN",            # Jio Financial Services listed ticker on NSE
    "JIO": "JIOFIN",
    "JIOPLATFORMS": "JIOFIN",
    "JIOFIN": "JIOFIN",
    "BLS": "BLS",
    "BLSE": "BLSE",
    "SWIGGY": "SWIGGY",
    "ZOMATO": "ZOMATO",
    "RELIANCE": "RELIANCE",
    "TCS": "TCS",
    "INFY": "INFY",
    "HDFCBANK": "HDFCBANK",
    "TATATECH": "TATATECH",
    "TATAMOTORS": "TATAMOTORS"
}

def resolve_ticker(user_text):
    raw = user_text.strip()
    if "google.com/finance/quote/" in raw:
        match = re.search(r"quote/([A-Za-z0-9_]+):?([A-Za-z]*)", raw)
        if match:
            raw = match.group(1).upper()
            
    cleaned = raw.upper()
    for w in ["SHARE PRICE", "STOCK PRICE", "SHARE", "STOCK", "LIMITED", "LTD", "NSE", "BSE", ".NS", ".BO"]:
        cleaned = re.sub(r'\b' + w + r'\b', '', cleaned)
    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned).strip()
    
    base_sym = COMMON_ALIASES.get(cleaned, cleaned if cleaned else "COALINDIA")
    return f"{base_sym}.NS", base_sym

# ----------------- LIVE SCRAPER (SAFE WRAPPER) -----------------
@st.cache_data(ttl=60)
def safe_google_finance_quote(pure_sym):
    url = f"https://www.google.com/finance/quote/{pure_sym}:NSE"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    data = {"name": None, "price": None, "change_pct": None}
    try:
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            n = soup.find("div", class_="zzDege")
            p = soup.find("div", class_="YMlKec fxKbKc")
            pct = soup.find("div", class_="JwB6zf")
            if n: data["name"] = n.text.strip()
            if p: data["price"] = float(p.text.replace("₹", "").replace(",", "").strip())
            if pct: data["change_pct"] = pct.text.strip()
    except Exception:
        pass
    return data

# ----------------- TECHNICAL STRATEGY ENGINE -----------------
def apply_technical_strategy(df):
    total = len(df)
    df['EMA_20'] = df['Close'].ewm(span=min(20, total), adjust=False).mean()
    if total >= 50:
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    else:
        df['EMA_50'] = np.nan

    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=min(14, total)).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=min(14, total)).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['RSI'] = (100 - (100 / (1 + rs))).fillna(50.0)

    # Buy / Sell single-crossover logic
    df['Buy_Signal'] = np.nan
    df['Sell_Signal'] = np.nan

    in_pos = False
    for i in range(1, len(df)):
        c = df['Close'].iloc[i]
        p = df['Close'].iloc[i-1]
        e = df['EMA_20'].iloc[i]
        pe = df['EMA_20'].iloc[i-1]
        rsi = df['RSI'].iloc[i]

        # BUY: Crosses above 20 EMA
        if not in_pos and p <= pe and c > e and 38 <= rsi <= 68:
            df.loc[df.index[i], 'Buy_Signal'] = df['Low'].iloc[i] * 0.985
            in_pos = True
        # PROFIT BOOK / SELL: RSI > 70 or falls below 20 EMA
        elif in_pos and (rsi >= 70 or (p >= pe and c < e)):
            df.loc[df.index[i], 'Sell_Signal'] = df['High'].iloc[i] * 1.015
            in_pos = False

    return df

# ----------------- SIDEBAR -----------------
st.sidebar.markdown("### ⚡ Kotak Neo Watchlist")
watchlist = ["COALINDIA", "JIOFIN", "BLS", "BLSE", "RELIANCE", "SWIGGY", "TATATECH", "HDFCBANK", "INFY"]
selected_dropdown = st.sidebar.selectbox("Choose Stock:", watchlist, index=0)

user_search = st.sidebar.text_input(
    "Search Any Stock / URL:",
    value="",
    placeholder="e.g. COALINDIA, BLS, SWIGGY, or Google URL"
)

active_input = user_search if user_search.strip() else selected_dropdown
yf_ticker, pure_symbol = resolve_ticker(active_input)

timeframe = st.sidebar.selectbox("Chart Period:", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

# ----------------- TOP INDICES BAR (SAFE FETCH) -----------------
try:
    nifty_h = yf.Ticker("^NSEI").history(period="2d")
    if len(nifty_h) >= 2:
        n_curr = nifty_h['Close'].iloc[-1]
        n_chg = n_curr - nifty_h['Close'].iloc[-2]
        n_pct = (n_chg / nifty_h['Close'].iloc[-2]) * 100
        n_col = "#10b981" if n_chg >= 0 else "#ef4444"
        st.markdown(f"""
            <div style="background:#111726; border:1px solid #1e293b; padding:8px 16px; border-radius:8px; margin-bottom:15px; display:inline-block;">
                <span style="color:#94a3b8; font-size:0.85rem;">🇮🇳 NIFTY 50:</span> 
                <b style="color:#ffffff;">{n_curr:,.2f}</b> 
                <span style="color:{n_col}; font-weight:700;">{n_chg:+,.2f} ({n_pct:+.2f}%)</span>
            </div>
        """, unsafe_allow_html=True)
except Exception:
    pass

# ----------------- MAIN DATA EXECUTION -----------------
with st.spinner(f"Loading {pure_symbol} live market quote..."):
    try:
        # 1. Fetch from yfinance
        t = yf.Ticker(yf_ticker)
        df = t.history(period=timeframe)

        if df.empty or len(df) < 3:
            df = t.history(period="max")

        if df.empty:
            st.error(f"Data not found for ticker '{yf_ticker}'. Please verify the company ticker.")
            st.stop()

        # 2. Try Google Finance for live price sync
        g_data = safe_google_finance_quote(pure_symbol)
        if g_data["price"]:
            df.loc[df.index[-1], 'Close'] = g_data["price"]

        df = apply_technical_strategy(df)

        # Company details
        info = t.info if hasattr(t, "info") else {}
        official_name = g_data["name"] or info.get("longName") or f"{pure_symbol} Limited"
        ltp = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2]) if len(df) >= 2 else ltp
        chg_pts = ltp - prev_close
        chg_pct = (chg_pts / prev_close) * 100 if prev_close else 0.0

        rsi_val = float(df['RSI'].iloc[-1])
        ema20_val = float(df['EMA_20'].iloc[-1])
        support = float(df['Low'].tail(20).min())
        resistance = float(df['High'].tail(20).max())

        stop_loss = round(support * 0.985, 2)
        risk = max(3.0, ltp - stop_loss)
        target_1 = round(ltp + (risk * 1.25), 2)
        target_2 = round(ltp + (risk * 2.2), 2)

        # Verdict
        if ltp > ema20_val and rsi_val <= 68:
            verdict_badge = "🟢 BUY CONFIRMED"
            pill_color = "#10b981"
            action_text = f"Price is trading above 20 EMA with healthy momentum (RSI {rsi_val:.1f}). Favorable for entry with stop-loss at ₹{stop_loss:,.2f}."
        elif rsi_val > 68:
            verdict_badge = "🟡 BOOK PARTIAL PROFIT"
            pill_color = "#f59e0b"
            action_text = f"Stock is overbought (RSI {rsi_val:.1f}). Book partial profits at Target 1 (₹{target_1:,.2f}) and trail your stop-loss."
        else:
            verdict_badge = "🔴 WEAK MOMENTUM"
            pill_color = "#ef4444"
            action_text = f"Trading below 20 EMA resistance. Avoid fresh buy or maintain strict stop-loss."

        # ----------------- KOTAK NEO HEADER -----------------
        is_up = chg_pts >= 0
        pill_class = "pill-up" if is_up else "pill-down"
        sign = "+" if is_up else ""

        st.markdown(f"""
            <div class="neo-header">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="company-title">{official_name}</span>
                        <span class="company-badge">{pure_symbol} | NSE EQ</span>
                    </div>
                    <div style="background:{pill_color}22; border:1px solid {pill_color}; color:{pill_color}; padding:6px 14px; border-radius:20px; font-weight:700;">
                        {verdict_badge}
                    </div>
                </div>
                <div style="display:flex; align-items:baseline; margin-top:8px;">
                    <span class="ltp-price">₹{ltp:,.2f}</span>
                    <span style="margin-left:12px;" class="{pill_class}">{sign}{chg_pts:,.2f} ({sign}{chg_pct:.2f}%)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ----------------- CHART & ORDER PAD LAYOUT -----------------
        col_chart, col_pad = st.columns([7, 3])

        with col_chart:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])

            # Candles
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price'
            ), row=1, col=1)

            # EMAs
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#38bdf8', width=1.5), name='20 EMA'), row=1, col=1)
            if 'EMA_50' in df and pd.notna(df['EMA_50'].iloc[-1]):
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='#fbbf24', width=1.5), name='50 EMA'), row=1, col=1)

            # BUY Marker
            buys = df[df['Buy_Signal'].notna()]
            if not buys.empty:
                fig.add_trace(go.Scatter(
                    x=buys.index, y=buys['Buy_Signal'],
                    mode='markers+text',
                    marker=dict(symbol='triangle-up', size=15, color='#10b981', line=dict(width=1, color='white')),
                    text=['BUY'] * len(buys),
                    textposition='bottom center',
                    textfont=dict(color='#10b981', size=11, family="Arial Black"),
                    name='BUY Trigger'
                ), row=1, col=1)

            # PROFIT BOOK Marker
            sells = df[df['Sell_Signal'].notna()]
            if not sells.empty:
                fig.add_trace(go.Scatter(
                    x=sells.index, y=sells['Sell_Signal'],
                    mode='markers+text',
                    marker=dict(symbol='triangle-down', size=15, color='#ef4444', line=dict(width=1, color='white')),
                    text=['PROFIT BOOK'] * len(sells),
                    textposition='top center',
                    textfont=dict(color='#ef4444', size=11, family="Arial Black"),
                    name='PROFIT BOOK'
                ), row=1, col=1)

            # Volume
            vol_colors = ['#10b981' if r['Close'] >= r['Open'] else '#ef4444' for _, r in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)

            fig.update_layout(
                height=530,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                paper_bgcolor="#0b0f17",
                plot_bgcolor="#0b0f17",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_pad:
            st.markdown("""
                <div style="background:#111827; border:1px solid #1f2937; border-radius:8px; padding:12px; margin-bottom:10px;">
                    <h4 style="margin:0; color:#ffffff;">🛒 Kotak Neo Order Pad</h4>
                </div>
            """, unsafe_allow_html=True)

            tab_buy, tab_sell = st.tabs(["BUY", "SELL"])

            with tab_buy:
                qty = st.number_input("Qty", min_value=1, value=10, step=1, key="k_qty")
                st.write(f"**Required Margin:** ₹{qty * ltp:,.2f}")
                st.markdown(f"""
                    <div style="background:#131c2e; padding:10px; border-radius:6px; margin:10px 0; font-size:0.85rem; border:1px solid #1e293b;">
                        • <b>Stop-Loss:</b> ₹{stop_loss:,.2f}<br>
                        • <b>Target 1 (50%):</b> ₹{target_1:,.2f}<br>
                        • <b>Target 2 (Final):</b> ₹{target_2:,.2f}
                    </div>
                """, unsafe_allow_html=True)
                if st.button("BUY NOW", use_container_width=True):
                    st.success(f"Bought {qty} {pure_symbol} at ₹{ltp:,.2f}")

            with tab_sell:
                s_qty = st.number_input("Qty to Exit", min_value=1, value=qty, step=1, key="s_qty")
                st.write(f"**Est. Value:** ₹{s_qty * ltp:,.2f}")
                if st.button("BOOK PROFIT", use_container_width=True):
                    st.warning(f"Sold {s_qty} {pure_symbol} at ₹{ltp:,.2f}")

        # ----------------- BOTTOM STATS -----------------
        st.markdown("### 📌 Execution Benchmarks")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Current 20 EMA", f"₹{ema20_val:,.2f}")
        m2.metric("14-Day RSI", f"{rsi_val:.1f}")
        m3.metric("Key Support", f"₹{support:,.2f}")
        m4.metric("Key Resistance", f"₹{resistance:,.2f}")
        m5.metric("Target 1 (Book 50%)", f"₹{target_1:,.2f}")

    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
