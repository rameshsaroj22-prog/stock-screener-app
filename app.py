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
    page_title="Kotak Neo Terminal | Live Google Sync",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- KOTAK NEO PROFESSIONAL DARK THEME -----------------
st.markdown("""
    <style>
    /* Global Base */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #111726 !important;
        border-right: 1px solid #1e293b;
    }
    
    /* Top Market Bar */
    .market-strip {
        display: flex;
        gap: 15px;
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 8px 16px;
        margin-bottom: 15px;
    }
    .index-item {
        font-size: 0.85rem;
        color: #94a3b8;
    }
    
    /* Neo Stock Header Card */
    .neo-card {
        background: linear-gradient(135deg, #131c2e 0%, #0d131f 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 16px 22px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .stock-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
    }
    .badge-nse {
        background: #1e293b;
        color: #38bdf8;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 8px;
        vertical-align: middle;
    }
    .price-large {
        font-size: 2.2rem;
        font-weight: 800;
        color: #ffffff;
        margin: 4px 0 0 0;
    }
    .change-green {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 2px 10px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.9rem;
        margin-left: 10px;
    }
    .change-red {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid #ef4444;
        padding: 2px 10px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.9rem;
        margin-left: 10px;
    }
    
    /* Order Pad Container */
    .order-box {
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px;
    }
    
    /* Streamlit Metric Overrides */
    div[data-testid="stMetric"] {
        background-color: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 8px 12px;
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 0.8rem;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 1.15rem;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- SMART SYMBOL & GOOGLE URL PARSER -----------------
def parse_user_stock_query(user_input):
    """
    Intelligently resolves Google Finance URLs, full company names,
    or short abbreviations into official NSE tickers.
    """
    raw = user_input.strip()
    
    # 1. Direct Google Finance URL match
    if "google.com/finance/quote/" in raw:
        match = re.search(r"quote/([A-Za-z0-9_]+):?([A-Za-z]*)", raw)
        if match:
            return match.group(1).upper()
            
    # 2. Clean normal search keywords
    cleaned = raw.upper()
    for drop in ["SHARE PRICE", "STOCK PRICE", "SHARE", "STOCK", "LIMITED", "LTD", "NSE", "BSE", ".NS", ".BO"]:
        cleaned = re.sub(r'\b' + drop + r'\b', '', cleaned)
    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned).strip()
    
    # Common Indian market aliases
    alias_dict = {
        "COAL": "COALINDIA",
        "COALINDIA": "COALINDIA",
        "JPL": "JIOFIN",            # Jio Financial Services Ltd (NSE Listed)
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
        "TATAMOTORS": "TATAMOTORS",
        "TATATECH": "TATATECH"
    }
    return alias_dict.get(cleaned, cleaned if cleaned else "COALINDIA")

# ----------------- GOOGLE FINANCE LIVE SCRAPER -----------------
@st.cache_data(ttl=60)
def sync_google_finance_live(ticker):
    """
    Directly extracts official company title, live price, and day range from Google Finance.
    """
    url = f"https://www.google.com/finance/quote/{ticker}:NSE"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    res = {
        "name": None, "price": None, "change_pct": None,
        "high": None, "low": None, "prev_close": None
    }
    try:
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Name
            name_el = soup.find("div", class_="zzDege")
            if name_el:
                res["name"] = name_el.text.strip()
                
            # Price
            price_el = soup.find("div", class_="YMlKec fxKbKc")
            if price_el:
                res["price"] = float(price_el.text.replace("₹", "").replace(",", "").strip())
                
            # Change %
            pct_el = soup.find("div", class_="JwB6zf")
            if pct_el:
                res["change_pct"] = pct_el.text.strip()
                
            # Stats Table (Range & Prev Close)
            for row in soup.find_all("div", class_="gyFHrc"):
                lbl = row.find("div", class_="mfs7Fc")
                val = row.find("div", class_="P6K39c")
                if lbl and val:
                    l_text = lbl.text.strip().lower()
                    v_text = val.text.strip().replace("₹", "").replace(",", "")
                    if "prev close" in l_text:
                        res["prev_close"] = float(v_text) if v_text.replace(".", "").isdigit() else None
                    elif "day range" in l_text or "range" in l_text:
                        parts = v_text.split("-")
                        if len(parts) == 2:
                            res["low"] = float(parts[0].strip())
                            res["high"] = float(parts[1].strip())
    except Exception:
        pass
    return res

# ----------------- TECHNICAL STRATEGY (CLEAN CROSSOVER SIGNALS) -----------------
def calculate_trading_signals(df):
    total = len(df)
    
    # 20 EMA & 50 EMA
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

    # Clean non-repetitive triggers
    df['Buy_Signal'] = np.nan
    df['Sell_Signal'] = np.nan

    has_position = False
    for i in range(1, len(df)):
        c = df['Close'].iloc[i]
        p = df['Close'].iloc[i-1]
        e = df['EMA_20'].iloc[i]
        pe = df['EMA_20'].iloc[i-1]
        rsi = df['RSI'].iloc[i]

        # BUY: Crosses above 20 EMA with positive RSI
        if not has_position and p <= pe and c > e and 38 <= rsi <= 68:
            df.loc[df.index[i], 'Buy_Signal'] = df['Low'].iloc[i] * 0.985
            has_position = True

        # PROFIT BOOK: RSI > 70 or falls below 20 EMA
        elif has_position and (rsi >= 70 or (p >= pe and c < e)):
            df.loc[df.index[i], 'Sell_Signal'] = df['High'].iloc[i] * 1.015
            has_position = False

    return df

# ----------------- SIDEBAR: WATCHLIST & SEARCH -----------------
st.sidebar.markdown("### ⚡ Kotak Neo Watchlist")
quick_basket = ["COALINDIA", "JIOFIN", "BLS", "BLSE", "RELIANCE", "SWIGGY", "TATATECH", "HDFCBANK", "INFY"]
selected_scrip = st.sidebar.selectbox("Tracked Basket:", quick_basket, index=0)

search_input = st.sidebar.text_input(
    "Search Stock / Google Finance URL:",
    value="",
    placeholder="e.g. COALINDIA, BLS, SWIGGY, or paste Google URL"
)

active_ticker = parse_user_stock_query(search_input) if search_input.strip() else selected_scrip
timeframe = st.sidebar.selectbox("Chart Horizon:", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

# ----------------- TOP INDICES BAR -----------------
try:
    nifty = yf.Ticker("^NSEI").history(period="2d")
    if len(nifty) >= 2:
        n_p = nifty['Close'].iloc[-1]
        n_chg = n_p - nifty['Close'].iloc[-2]
        n_pct = (n_chg / nifty['Close'].iloc[-2]) * 100
        n_col = "#10b981" if n_chg >= 0 else "#ef4444"
        st.markdown(f"""
            <div class="market-strip">
                <span class="index-item">🇮🇳 <b>NIFTY 50:</b> ₹{n_p:,.2f} <b style="color:{n_col};">{n_chg:+,.2f} ({n_pct:+.2f}%)</b></span>
            </div>
        """, unsafe_allow_html=True)
except Exception:
    pass

# ----------------- MAIN PROCESSING -----------------
with st.spinner(f"Syncing {active_ticker} with Google Finance & NSE..."):
    try:
        # 1. Fetch Google Live Data
        g_data = sync_google_finance_live(active_ticker)
        
        # 2. Historical Chart Data
        yf_ticker = f"{active_ticker}.NS"
        stock = yf.Ticker(yf_ticker)
        df = stock.history(period=timeframe)

        if df.empty or len(df) < 3:
            df = stock.history(period="max")

        if df.empty:
            st.error(f"Scrip '{active_ticker}' not found on NSE. Please verify symbol.")
            st.stop()

        # Sync latest price from Google Finance if available
        if g_data["price"]:
            df.loc[df.index[-1], 'Close'] = g_data["price"]

        df = calculate_trading_signals(df)

        # Company Metadata
        info = stock.info if hasattr(stock, "info") else {}
        company_name = g_data["name"] or info.get("longName") or f"{active_ticker} Limited"
        ltp = float(df['Close'].iloc[-1])
        prev_close = g_data["prev_close"] if g_data["prev_close"] else float(df['Close'].iloc[-2])
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

        # Signal Status
        if ltp > ema20_val and rsi_val <= 68:
            verdict_badge = "🟢 BUY CONFIRMED"
            pill_color = "#10b981"
            action_desc = f"Trading above 20 EMA with stable momentum (RSI {rsi_val:.1f}). Favorable for entry with SL at ₹{stop_loss:,.2f}."
        elif rsi_val > 68:
            verdict_badge = "🟡 BOOK PARTIAL PROFIT"
            pill_color = "#f59e0b"
            action_desc = f"RSI is overbought ({rsi_val:.1f}). Book partial profit at Target 1 (₹{target_1:,.2f}) and trail stop-loss."
        else:
            verdict_badge = "🔴 WEAK MOMENTUM"
            pill_color = "#ef4444"
            action_desc = f"Below 20 EMA resistance. Avoid fresh buy or maintain strict stop-loss."

        # ----------------- KOTAK NEO HEADER CARD -----------------
        is_up = chg_pts >= 0
        pill_class = "change-green" if is_up else "change-red"
        sign = "+" if is_up else ""

        st.markdown(f"""
            <div class="neo-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="stock-title">{company_name}</span>
                        <span class="badge-nse">{active_ticker} | NSE EQ</span>
                    </div>
                    <div style="background:{pill_color}22; border:1px solid {pill_color}; color:{pill_color}; padding:5px 14px; border-radius:20px; font-weight:700; font-size:0.85rem;">
                        {verdict_badge}
                    </div>
                </div>
                <div style="display:flex; align-items:baseline; margin-top:6px;">
                    <span class="price-large">₹{ltp:,.2f}</span>
                    <span class="{pill_class}">{sign}{chg_pts:,.2f} ({sign}{chg_pct:.2f}%)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ----------------- MAIN LAYOUT: CHART (70%) + ORDER PAD (30%) -----------------
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

            # Clean Single BUY Marker
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

            # Clean Single PROFIT BOOK Marker
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
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                paper_bgcolor="#0b0f19",
                plot_bgcolor="#0b0f19",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_pad:
            # ----------------- KOTAK NEO ORDER PAD -----------------
            st.markdown("""
                <div class="order-box">
                    <h4 style="margin:0 0 8px 0; color:#ffffff;">🛒 Kotak Neo Order Pad</h4>
                </div>
            """, unsafe_allow_html=True)

            tab_buy, tab_sell = st.tabs(["BUY", "SELL"])

            with tab_buy:
                qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="neo_buy_qty")
                prod = st.radio("Product", ["Delivery (CNC)", "Intraday (MIS)"], horizontal=True, key="neo_prod")
                margin_req = qty * ltp
                st.write(f"**Required Margin:** ₹{margin_req:,.2f}")
                
                st.markdown(f"""
                    <div style="background:#131c2e; padding:10px; border-radius:6px; margin:10px 0; font-size:0.85rem; border:1px solid #1e293b;">
                        • <b>Stop-Loss:</b> ₹{stop_loss:,.2f}<br>
                        • <b>Target 1 (Book 50%):</b> ₹{target_1:,.2f}<br>
                        • <b>Target 2 (Runner):</b> ₹{target_2:,.2f}
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("BUY NOW", use_container_width=True):
                    st.success(f"Order Placed: {qty} shares of {active_ticker} at ₹{ltp:,.2f}")

            with tab_sell:
                s_qty = st.number_input("Quantity to Exit", min_value=1, value=qty, step=1, key="neo_sell_qty")
                st.write(f"**Estimated Proceeds:** ₹{s_qty * ltp:,.2f}")
                if st.button("BOOK PROFIT / SELL", use_container_width=True):
                    st.warning(f"Sold {s_qty} shares of {active_ticker} at ₹{ltp:,.2f}")

        # ----------------- MARKET DEPTH & BENCHMARKS -----------------
        st.markdown("### 📊 Market Depth & Key Levels")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("20-Day EMA", f"₹{ema20_val:,.2f}")
        m2.metric("14-Day RSI", f"{rsi_val:.1f}")
        m3.metric("Key Support", f"₹{support:,.2f}")
        m4.metric("Key Resistance", f"₹{resistance:,.2f}")
        m5.metric("Target 1 (Exit 50%)", f"₹{target_1:,.2f}")

    except Exception as e:
        st.error(f"Error loading {active_ticker}: {str(e)}")
