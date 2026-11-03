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
st.set_page_config(page_title="AI Stock Screener (Google Finance)", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(180deg, #0b0e14 0%, #101520 100%);
        color: #e6edf3;
    }
    section[data-testid="stSidebar"] {
        background-color: #121722 !important;
        border-right: 1px solid #1f2937;
    }
    div[data-testid="stMetric"] {
        background-color: #161c28;
        border: 1px solid #232d3f;
        border-radius: 10px;
        padding: 12px 16px;
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
    }
    .header-box {
        background: linear-gradient(90deg, #161f30 0%, #101520 100%);
        border-left: 6px solid #2962ff;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- SMART SYMBOL & URL RESOLVER -----------------
def extract_clean_ticker(input_str):
    """
    Extracts pure NSE ticker from user input, even if they paste full Google Finance URL
    or search terms like 'COAL', 'jpl share price'.
    """
    raw = input_str.strip()
    
    # Check if user pasted a Google Finance URL like:
    # https://www.google.com/finance/quote/COALINDIA:NSE
    if "google.com/finance/quote/" in raw:
        match = re.search(r"quote/([A-Za-z0-9_]+):?([A-Za-z]*)", raw)
        if match:
            return match.group(1).upper()
            
    # Clean unwanted words
    cleaned = raw.upper()
    for word in ["SHARE PRICE", "STOCK PRICE", "SHARE", "STOCK", "LIMITED", "LTD", "NSE", "BSE"]:
        cleaned = re.sub(r'\b' + word + r'\b', '', cleaned)
    
    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned).strip()
    
    # Specific common Indian company mappings
    alias_map = {
        "COAL": "COALINDIA",
        "COALINDIA": "COALINDIA",
        "JIO": "JPL",
        "JIOPLATFORMS": "JPL",
        "JPL": "JPL",
        "JIOFIN": "JIOFIN",
        "BLS": "BLS",
        "BLSE": "BLSE",
        "SWIGGY": "SWIGGY",
        "ZOMATO": "ZOMATO",
        "TATASTEEL": "TATASTEEL",
        "RELIANCE": "RELIANCE"
    }
    return alias_map.get(cleaned, cleaned if cleaned else "COALINDIA")

# ----------------- GOOGLE FINANCE LIVE SCRAPER -----------------
@st.cache_data(ttl=60)
def scrape_google_finance(ticker):
    """Fetches real-time price, official company name, and daily stats directly from Google Finance."""
    url = f"https://www.google.com/finance/quote/{ticker}:NSE"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = {
        "name": None, "price": None, "change_pct": None,
        "high": None, "low": None, "prev_close": None
    }
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Extract Company Full Name
            name_el = soup.find("div", class_="zzDege")
            if name_el:
                res["name"] = name_el.text.strip()
                
            # Extract Live Price
            price_el = soup.find("div", class_="YMlKec fxKbKc")
            if price_el:
                res["price"] = float(price_el.text.replace("₹", "").replace(",", "").strip())
                
            # Extract % Change
            pct_el = soup.find("div", class_="JwB6zf")
            if pct_el:
                res["change_pct"] = pct_el.text.strip()
                
            # Extract Stats Table
            for s in soup.find_all("div", class_="gyFHrc"):
                label_el = s.find("div", class_="mfs7Fc")
                val_el = s.find("div", class_="P6K39c")
                if label_el and val_el:
                    l = label_el.text.strip().lower()
                    v = val_el.text.strip().replace("₹", "").replace(",", "")
                    if "prev close" in l:
                        res["prev_close"] = float(v) if v.replace(".", "").isdigit() else None
                    elif "day range" in l or "range" in l:
                        parts = v.split("-")
                        if len(parts) == 2:
                            res["low"] = float(parts[0].strip())
                            res["high"] = float(parts[1].strip())
    except Exception:
        pass
    return res

# ----------------- INDICATOR & CLEAN BUY/SELL SIGNALS -----------------
def apply_technical_strategy(df):
    total = len(df)
    
    # 20 EMA & 50 EMA
    df['EMA_20'] = df['Close'].ewm(span=min(20, total), adjust=False).mean()
    if total >= 50:
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    else:
        df['EMA_50'] = np.nan

    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=min(14, total)).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=min(14, total)).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['RSI'] = (100 - (100 / (1 + rs))).fillna(50.0)

    # Clean Signals (Only on actual crossover to avoid repeated clutter)
    df['Buy_Signal'] = np.nan
    df['Sell_Signal'] = np.nan

    active_trade = False
    for i in range(1, len(df)):
        c_close = df['Close'].iloc[i]
        p_close = df['Close'].iloc[i-1]
        c_ema = df['EMA_20'].iloc[i]
        p_ema = df['EMA_20'].iloc[i-1]
        rsi = df['RSI'].iloc[i]

        # BUY: Crosses above 20 EMA with bullish RSI
        if not active_trade and p_close <= p_ema and c_close > c_ema and 40 <= rsi <= 68:
            df.loc[df.index[i], 'Buy_Signal'] = df['Low'].iloc[i] * 0.985
            active_trade = True

        # SELL / PROFIT BOOK: Overbought (RSI > 70) or crossing below 20 EMA
        elif active_trade and (rsi >= 70 or (p_close >= p_ema and c_close < c_ema)):
            df.loc[df.index[i], 'Sell_Signal'] = df['High'].iloc[i] * 1.015
            active_trade = False

    return df

# ----------------- UI / SIDEBAR -----------------
st.sidebar.title("🔍 Stock Scanner")

default_list = ["COALINDIA", "JPL", "BLS", "BLSE", "RELIANCE", "SWIGGY", "TATATECH"]
selected_dropdown = st.sidebar.selectbox("Tracked Stocks:", default_list, index=0)

user_search = st.sidebar.text_input(
    "Paste Google Finance URL or Stock Name:",
    value="",
    placeholder="e.g. COALINDIA, https://www.google.com/finance/quote/COALINDIA:NSE"
)

active_ticker = extract_clean_ticker(user_search) if user_search.strip() else selected_dropdown
time_period = st.sidebar.selectbox("Chart Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

st.title("📈 AI Stock Screener & Trading Signals")
st.caption("Real-Time Data Synced with Google Finance (NSE India)")

# ----------------- DATA FETCHING -----------------
with st.spinner(f"Fetching Google Finance data for {active_ticker}..."):
    try:
        # 1. Scrape Google Finance Live Data
        g_data = scrape_google_finance(active_ticker)
        
        # 2. Fetch True NSE History (Append .NS)
        yf_ticker = f"{active_ticker}.NS"
        stock_obj = yf.Ticker(yf_ticker)
        df = stock_obj.history(period=time_period)

        # Fallback if yfinance ticker symbol needs adjustments
        if df.empty or len(df) < 5:
            df = stock_obj.history(period="max")

        if df.empty:
            st.error(f"Data for '{active_ticker}' could not be fetched. Please verify the NSE symbol.")
            st.stop()

        # Update latest close with Google Finance live price
        if g_data["price"]:
            df.loc[df.index[-1], 'Close'] = g_data["price"]

        df = apply_technical_strategy(df)

        # Basic Info
        full_name = g_data["name"] if g_data["name"] else f"{active_ticker} Limited"
        curr_price = float(df['Close'].iloc[-1])
        rsi_val = float(df['RSI'].iloc[-1])
        ema20_val = float(df['EMA_20'].iloc[-1])

        # Support, Resistance, SL, and Target Calculation
        support = float(df['Low'].tail(20).min())
        resistance = float(df['High'].tail(20).max())
        stop_loss = round(support * 0.985, 2)
        risk = max(3.0, curr_price - stop_loss)
        target_1 = round(curr_price + (risk * 1.25), 2)
        target_2 = round(curr_price + (risk * 2.2), 2)

        # Score & Signal Verdict
        score = 5.0
        if curr_price > ema20_val:
            score += 3.0
        if 40 <= rsi_val <= 65:
            score += 2.0
        score = min(10.0, score)

        if score >= 7.5:
            verdict = "STRONG BUY"
            color = "#00c853"
            action_text = f"Trading strongly above 20 EMA with positive RSI ({rsi_val:.1f}). Favorable for entry with stop-loss at ₹{stop_loss:,.2f}."
        elif score >= 5.0:
            verdict = "ACCUMULATE / DIP BUY"
            color = "#64dd17"
            action_text = "Consolidating near support. Gradual accumulation on pullbacks suggested."
        else:
            verdict = "SELL / BOOK PROFIT"
            color = "#d50000"
            action_text = f"Price facing resistance or momentum cooling (RSI {rsi_val:.1f}). Book profits or wait for fresh breakout."

        # ----------------- DISPLAY COMPANY HEADER -----------------
        st.markdown(f"""
            <div class="header-box">
                <h1 style="margin: 0; color: #ffffff; font-size: 2.2rem; font-weight: 700;">🏢 {full_name}</h1>
                <p style="margin: 6px 0 0 0; color: #58a6ff; font-size: 1.1rem;">
                    NSE Ticker: <b>{active_ticker}</b> | Google Finance Verified: <b>{active_ticker}:NSE</b>
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Metric Cards
        c1, c2, c3, c4, c5 = st.columns(5)
        pct_tag = f" ({g_data['change_pct']})" if g_data['change_pct'] else ""
        c1.metric("Live Market Price", f"₹{curr_price:,.2f}{pct_tag}")
        c2.metric("Technical Score", f"{score} / 10")
        c3.metric("Stop-Loss (SL)", f"₹{stop_loss:,.2f}")
        c4.metric("Target 1 (Book 50%)", f"₹{target_1:,.2f}")
        c5.metric("Target 2 (Final)", f"₹{target_2:,.2f}")

        # Verdict Banner
        st.markdown(f"""
            <div style="background: linear-gradient(90deg, {color}20, #161c28); 
                        border: 1px solid {color}; border-left: 6px solid {color}; 
                        padding: 14px 20px; border-radius: 8px; margin: 15px 0;">
                <h3 style="color: {color}; margin: 0;">Trading Verdict: {verdict}</h3>
                <p style="font-size: 15px; margin-top: 6px; margin-bottom: 0; color: #cbd5e1;">{action_text}</p>
            </div>
        """, unsafe_allow_html=True)

        # ----------------- CANDLESTICK CHART -----------------
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])

        # Candles
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name='Price'
        ), row=1, col=1)

        # 20 EMA
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1.4), name='20 EMA'), row=1, col=1)
        
        # 50 EMA if available
        if 'EMA_50' in df and pd.notna(df['EMA_50'].iloc[-1]):
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='orange', width=1.4), name='50 EMA'), row=1, col=1)

        # Buy Markers (Green ▲)
        buys = df[df['Buy_Signal'].notna()]
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys.index, y=buys['Buy_Signal'],
                mode='markers+text',
                marker=dict(symbol='triangle-up', size=14, color='#00e676', line=dict(width=1, color='white')),
                text=['BUY'] * len(buys),
                textposition='bottom center',
                textfont=dict(color='#00e676', size=11, family="Arial Black"),
                name='BUY Signal'
            ), row=1, col=1)

        # Sell Markers (Red ▼)
        sells = df[df['Sell_Signal'].notna()]
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells.index, y=sells['Sell_Signal'],
                mode='markers+text',
                marker=dict(symbol='triangle-down', size=14, color='#ff1744', line=dict(width=1, color='white')),
                text=['PROFIT BOOK'] * len(sells),
                textposition='top center',
                textfont=dict(color='#ff1744', size=11, family="Arial Black"),
                name='PROFIT BOOK / SELL'
            ), row=1, col=1)

        # Volume
        vol_colors = ['#00c853' if r['Close'] >= r['Open'] else '#d50000' for _, r in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)

        fig.update_layout(
            title=dict(text=f"<b>{full_name} ({active_ticker})</b> - Price & Signals", font=dict(size=17, color="#ffffff")),
            height=580,
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # ----------------- EXECUTION & BENCHMARK SUMMARY -----------------
        st.write("### 📌 Trade Execution Details")
        col_a, col_b, col_c = st.columns(3)
        col_a.write(f"• **Current 20 EMA:** ₹{ema20_val:,.2f}")
        col_a.write(f"• **14-Period RSI:** {rsi_val:.1f}")
        col_b.write(f"• **20-Day Support:** ₹{support:,.2f}")
        col_b.write(f"• **20-Day Resistance:** ₹{resistance:,.2f}")
        col_c.write(f"• **Target 1 (Book 50%):** ₹{target_1:,.2f}")
        col_c.write(f"• **Target 2 (Final):** ₹{target_2:,.2f}")

    except Exception as e:
        st.error(f"Error loading {active_ticker}: {str(e)}")
