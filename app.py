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
    page_title="Kotak Neo Terminal | AI Stock Screener",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- KOTAK NEO SIGNATURE DARK THEME CSS -----------------
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #0b0f17;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111622 !important;
        border-right: 1px solid #1e293b;
    }
    
    /* Top Index Bar */
    .index-bar {
        display: flex;
        gap: 15px;
        padding: 10px 16px;
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        margin-bottom: 18px;
    }
    .index-pill {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        color: #94a3b8;
    }
    .val-green { color: #10b981; font-weight: 700; }
    .val-red { color: #ef4444; font-weight: 700; }

    /* Neo Stock Header Card */
    .neo-header {
        background: linear-gradient(135deg, #131c2e 0%, #0d131f 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
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
    .change-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 700;
        margin-left: 10px;
    }
    .pill-up { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
    .pill-down { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }

    /* Order Pad / Trading Box */
    .order-box {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 16px;
        margin-top: 10px;
    }
    .btn-buy {
        background-color: #2563eb !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        border: none !important;
        width: 100%;
        padding: 8px;
    }
    .btn-sell {
        background-color: #dc2626 !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        border: none !important;
        width: 100%;
        padding: 8px;
    }
    
    /* Native Metric overrides */
    div[data-testid="stMetric"] {
        background-color: #131926;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px 14px;
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 0.82rem;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 1.25rem;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- LIVE MARKET INDICES STRIP (CACHED) -----------------
@st.cache_data(ttl=120)
def get_market_indices():
    indices = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"}
    data = {}
    for name, sym in indices.items():
        try:
            h = yf.Ticker(sym).history(period="2d")
            if len(h) >= 2:
                curr = h['Close'].iloc[-1]
                prev = h['Close'].iloc[-2]
                chg = curr - prev
                pct = (chg / prev) * 100
                data[name] = {"val": curr, "chg": chg, "pct": pct}
        except Exception:
            pass
    return data

# ----------------- SMART SYMBOL & GOOGLE SCRAPER -----------------
def clean_ticker_input(text):
    raw = text.strip()
    if "google.com/finance/quote/" in raw:
        match = re.search(r"quote/([A-Za-z0-9_]+):?([A-Za-z]*)", raw)
        if match:
            return match.group(1).upper()
            
    cleaned = raw.upper()
    for w in ["SHARE PRICE", "STOCK PRICE", "SHARE", "STOCK", "LIMITED", "LTD", "NSE", "BSE"]:
        cleaned = re.sub(r'\b' + w + r'\b', '', cleaned)
    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned).strip()
    
    mapping = {
        "COAL": "COALINDIA",
        "COALINDIA": "COALINDIA",
        "JPL": "JPL",
        "JIO": "JPL",
        "JIOFIN": "JIOFIN",
        "BLS": "BLS",
        "BLSE": "BLSE",
        "SWIGGY": "SWIGGY",
        "ZOMATO": "ZOMATO"
    }
    return mapping.get(cleaned, cleaned if cleaned else "COALINDIA")

@st.cache_data(ttl=60)
def scrape_google_finance_live(ticker):
    url = f"https://www.google.com/finance/quote/{ticker}:NSE"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = {"name": None, "price": None, "change_pct": None, "high": None, "low": None, "prev_close": None}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            name_el = soup.find("div", class_="zzDege")
            if name_el:
                res["name"] = name_el.text.strip()
            price_el = soup.find("div", class_="YMlKec fxKbKc")
            if price_el:
                res["price"] = float(price_el.text.replace("₹", "").replace(",", "").strip())
            pct_el = soup.find("div", class_="JwB6zf")
            if pct_el:
                res["change_pct"] = pct_el.text.strip()
            for s in soup.find_all("div", class_="gyFHrc"):
                l = s.find("div", class_="mfs7Fc")
                v = s.find("div", class_="P6K39c")
                if l and v:
                    lbl = l.text.strip().lower()
                    val = v.text.strip().replace("₹", "").replace(",", "")
                    if "prev close" in lbl:
                        res["prev_close"] = float(val) if val.replace(".", "").isdigit() else None
                    elif "day range" in lbl or "range" in lbl:
                        parts = val.split("-")
                        if len(parts) == 2:
                            res["low"] = float(parts[0].strip())
                            res["high"] = float(parts[1].strip())
    except Exception:
        pass
    return res

# ----------------- TECHNICAL STRATEGY (BUY/SELL SIGNALS) -----------------
def apply_signals(df):
    total = len(df)
    df['EMA_20'] = df['Close'].ewm(span=min(20, total), adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=min(50, total), adjust=False).mean()

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=min(14, total)).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=min(14, total)).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['RSI'] = (100 - (100 / (1 + rs))).fillna(50.0)

    df['Buy_Signal'] = np.nan
    df['Sell_Signal'] = np.nan

    in_pos = False
    for i in range(1, len(df)):
        c = df['Close'].iloc[i]
        p = df['Close'].iloc[i-1]
        e = df['EMA_20'].iloc[i]
        pe = df['EMA_20'].iloc[i-1]
        rsi = df['RSI'].iloc[i]

        if not in_pos and p <= pe and c > e and 38 <= rsi <= 68:
            df.loc[df.index[i], 'Buy_Signal'] = df['Low'].iloc[i] * 0.985
            in_pos = True
        elif in_pos and (rsi >= 70 or (p >= pe and c < e)):
            df.loc[df.index[i], 'Sell_Signal'] = df['High'].iloc[i] * 1.015
            in_pos = False
    return df

# ----------------- SIDEBAR WATCHLIST -----------------
st.sidebar.markdown("### ⚡ Kotak Neo Watchlist")
watchlist = ["COALINDIA", "JPL", "BLS", "BLSE", "RELIANCE", "SWIGGY", "TATATECH", "HDFCBANK", "INFY"]
selected_from_list = st.sidebar.selectbox("Choose Scrip:", watchlist, index=0)

search_term = st.sidebar.text_input("Search / Paste Google URL:", placeholder="e.g. COALINDIA, JPL, BLS")
active_ticker = clean_ticker_input(search_term) if search_term.strip() else selected_from_list

timeframe = st.sidebar.selectbox("Timeframe:", ["1mo", "3mo", "6mo", "1y"], index=2)

# ----------------- TOP INDICES STRIP -----------------
idx_data = get_market_indices()
if idx_data:
    cols = st.columns(4)
    c_idx = 0
    for name, d in idx_data.items():
        color_class = "val-green" if d['chg'] >= 0 else "val-red"
        symbol_icon = "▲" if d['chg'] >= 0 else "▼"
        cols[c_idx].markdown(f"""
            <div style="background:#111726; border:1px solid #1e293b; padding:8px 14px; border-radius:6px;">
                <span style="color:#94a3b8; font-size:0.8rem;">{name}</span><br>
                <b>₹{d['val']:,.2f}</b> 
                <span class="{color_class}" style="font-size:0.8rem;">{symbol_icon} {d['chg']:+,.2f} ({d['pct']:+.2f}%)</span>
            </div>
        """, unsafe_allow_html=True)
        c_idx += 1

# ----------------- DATA PIPELINE -----------------
with st.spinner(f"Loading {active_ticker} live quote from Google Finance..."):
    try:
        g_data = scrape_google_finance_live(active_ticker)
        yf_sym = f"{active_ticker}.NS"
        stock_obj = yf.Ticker(yf_sym)
        df = stock_obj.history(period=timeframe)

        if df.empty or len(df) < 5:
            df = stock_obj.history(period="max")

        if df.empty:
            st.error(f"Scrip '{active_ticker}' not found on NSE. Please verify symbol.")
            st.stop()

        if g_data["price"]:
            df.loc[df.index[-1], 'Close'] = g_data["price"]

        df = apply_signals(df)

        company_name = g_data["name"] if g_data["name"] else f"{active_ticker} Limited"
        ltp = float(df['Close'].iloc[-1])
        prev_close = g_data["prev_close"] if g_data["prev_close"] else float(df['Close'].iloc[-2])
        chg_pts = ltp - prev_close
        chg_pct = (chg_pts / prev_close) * 100

        rsi_val = float(df['RSI'].iloc[-1])
        ema20_val = float(df['EMA_20'].iloc[-1])
        support = float(df['Low'].tail(20).min())
        resistance = float(df['High'].tail(20).max())

        stop_loss = round(support * 0.985, 2)
        risk = max(3.0, ltp - stop_loss)
        target_1 = round(ltp + (risk * 1.25), 2)
        target_2 = round(ltp + (risk * 2.2), 2)

        # Signal Verdict
        if ltp > ema20_val and rsi_val <= 68:
            verdict = "BUY / ACCUMULATE"
            pill_color = "#10b981"
            verdict_badge = "🟢 BUY CONFIRMED"
        elif rsi_val > 68:
            verdict = "PROFIT BOOKING"
            pill_color = "#f59e0b"
            verdict_badge = "🟡 BOOK PARTIAL PROFIT"
        else:
            verdict = "EXIT / CAUTION"
            pill_color = "#ef4444"
            verdict_badge = "🔴 WEAK MOMENTUM"

        # ----------------- KOTAK NEO HEADER CARD -----------------
        is_up = chg_pts >= 0
        pill_class = "pill-up" if is_up else "pill-down"
        sign = "+" if is_up else ""

        st.markdown(f"""
            <div class="neo-header">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="company-title">{company_name}</span>
                        <span class="company-badge">{active_ticker} | NSE EQ</span>
                    </div>
                    <div style="background:{pill_color}22; border:1px solid {pill_color}; color:{pill_color}; padding:6px 14px; border-radius:20px; font-weight:700; font-size:0.9rem;">
                        {verdict_badge}
                    </div>
                </div>
                <div style="display:flex; align-items:baseline; margin-top:8px;">
                    <span class="ltp-price">₹{ltp:,.2f}</span>
                    <span class="change-pill {pill_class}">{sign}{chg_pts:,.2f} ({sign}{chg_pct:.2f}%)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ----------------- LAYOUT: CHART (70%) + ORDER PAD (30%) -----------------
        col_chart, col_order = st.columns([7, 3])

        with col_chart:
            # Candlestick + Volume Chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])

            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price'
            ), row=1, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#38bdf8', width=1.5), name='20 EMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='#fbbf24', width=1.5), name='50 EMA'), row=1, col=1)

            # Buy Signal Marker (Green Up Triangle)
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

            # Sell / Profit Book Marker (Red Down Triangle)
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

            # Volume Bars
            vol_colors = ['#10b981' if r['Close'] >= r['Open'] else '#ef4444' for _, r in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)

            fig.update_layout(
                height=530,
                margin=dict(l=10, r=10, t=20, b=10),
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                paper_bgcolor="#0b0f17",
                plot_bgcolor="#0b0f17",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_order:
            # ----------------- KOTAK NEO TRADE EXECUTION PAD -----------------
            st.markdown("""
                <div class="order-box">
                    <h4 style="margin:0 0 10px 0; color:#ffffff;">🛒 Kotak Neo Order Pad</h4>
                </div>
            """, unsafe_allow_html=True)

            order_tab1, order_tab2 = st.tabs(["BUY", "SELL"])

            with order_tab1:
                st.caption(f"Ready to Buy {active_ticker} at Market LTP")
                qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="buy_qty")
                prod_type = st.radio("Product Type", ["Delivery (CNC)", "Intraday (MIS)"], horizontal=True, key="buy_prod")
                total_val = qty * ltp
                st.write(f"**Required Margin:** ₹{total_val:,.2f}")

                st.markdown(f"""
                    <div style="background:#131c2e; padding:10px; border-radius:6px; margin:10px 0; border:1px solid #1e293b;">
                        <small style="color:#94a3b8;">Suggested Plan</small><br>
                        • <b>Stop-Loss:</b> ₹{stop_loss:,.2f}<br>
                        • <b>Target 1 (Book 50%):</b> ₹{target_1:,.2f}<br>
                        • <b>Target 2 (Runner):</b> ₹{target_2:,.2f}
                    </div>
                """, unsafe_allow_html=True)

                if st.button("BUY NOW", use_container_width=True):
                    st.success(f"Order simulated: Bought {qty} shares of {active_ticker} at ₹{ltp:,.2f}")

            with order_tab2:
                st.caption(f"Square off / Book Profit in {active_ticker}")
                sell_qty = st.number_input("Quantity to Sell", min_value=1, value=qty, step=1, key="sell_qty")
                st.write(f"**Est. Release Value:** ₹{sell_qty * ltp:,.2f}")
                if st.button("BOOK PROFIT / SELL", use_container_width=True):
                    st.warning(f"Profit booked on {sell_qty} shares of {active_ticker} at ₹{ltp:,.2f}")

        # ----------------- BOTTOM METRICS BAR -----------------
        st.markdown("### 📊 Market Depth & Key Levels")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("20-Day EMA", f"₹{ema20_val:,.2f}")
        m2.metric("14-Period RSI", f"{rsi_val:.1f}")
        m3.metric("Recent Support", f"₹{support:,.2f}")
        m4.metric("Recent Resistance", f"₹{resistance:,.2f}")
        m5.metric("Target 1 (50% Exit)", f"₹{target_1:,.2f}")

    except Exception as e:
        st.error(f"Error rendering Kotak Neo interface for {active_ticker}: {str(e)}")
