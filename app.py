import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- PAGE CONFIG & FINTECH THEME -----------------
st.set_page_config(page_title="AI Stock Screener & Trading Signals", layout="wide", initial_sidebar_state="expanded")

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
    .company-header {
        background: #161c28;
        border-left: 5px solid #2962ff;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- COMMON NAME MAPPER -----------------
COMMON_NAME_MAP = {
    "JIO": ("JIOFIN.NS", "Jio Financial Services Limited"),
    "JIOFIN": ("JIOFIN.NS", "Jio Financial Services Limited"),
    "BLS": ("BLS.NS", "BLS International Services Limited"),
    "BLSE": ("BLSE.NS", "BLS E-Services Limited"),
    "SWIGGY": ("SWIGGY.NS", "Swiggy Limited"),
    "ZOMATO": ("ZOMATO.NS", "Zomato Limited"),
    "TATATECH": ("TATATECH.NS", "Tata Technologies Limited"),
    "HYUNDAI": ("HYUNDAI.NS", "Hyundai Motor India Limited"),
    "COAL": ("COALINDIA.NS", "Coal India Limited"),
    "RELIANCE": ("RELIANCE.NS", "Reliance Industries Limited"),
    "TCS": ("TCS.NS", "Tata Consultancy Services Limited"),
    "INFY": ("INFY.NS", "Infosys Limited")
}

def resolve_ticker_and_name(user_input):
    clean = user_input.strip().upper()
    if clean in COMMON_NAME_MAP:
        return COMMON_NAME_MAP[clean][0], COMMON_NAME_MAP[clean][1]
    
    ticker = clean
    if not clean.endswith(".NS") and not clean.endswith(".BO") and len(clean) > 0:
        ticker = f"{clean}.NS"
    return ticker, None

@st.cache_data(ttl=3600)
def fetch_company_full_name(ticker_symbol):
    """Fetches official registered company name."""
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        name = info.get('longName') or info.get('shortName')
        if name:
            return name
    except Exception:
        pass
    clean = ticker_symbol.replace(".NS", "").replace(".BO", "")
    return COMMON_NAME_MAP.get(clean, (ticker_symbol, clean))[1]

# ----------------- GOOGLE FINANCE LIVE SCRAPER -----------------
@st.cache_data(ttl=60)
def fetch_google_finance_live(ticker):
    clean_sym = ticker.replace(".NS", "").replace(".BO", "").strip().upper()
    url = f"https://www.google.com/finance/quote/{clean_sym}:NSE"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            elem = soup.find("div", class_="YMlKec fxKbKc")
            if elem:
                return float(elem.text.replace("₹", "").replace(",", "").strip())
    except Exception:
        pass
    return None

# ----------------- INDICATORS & BUY/SELL SIGNAL ENGINE -----------------
def calculate_adaptive_indicators(df):
    total = len(df)
    
    # Adaptive EMAs
    df['EMA_20'] = df['Close'].ewm(span=min(20, total), adjust=False).mean()
    if total >= 50:
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    else:
        df['EMA_50'] = np.nan

    if total >= 200:
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    else:
        df['EMA_200'] = np.nan

    # RSI
    rsi_win = 14 if total >= 15 else max(3, total - 1)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_win).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_win).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50.0)

    # Volume SMA
    df['Vol_SMA'] = df['Volume'].rolling(window=min(20, total)).mean()

    # --- BUY & SELL / PROFIT BOOKING SIGNALS ON CHART ---
    df['Buy_Signal'] = np.nan
    df['Sell_Signal'] = np.nan

    for i in range(1, len(df)):
        c_close = df['Close'].iloc[i]
        p_close = df['Close'].iloc[i-1]
        c_ema20 = df['EMA_20'].iloc[i]
        p_ema20 = df['EMA_20'].iloc[i-1]
        rsi = df['RSI'].iloc[i]

        # 1. BUY SIGNAL: Price crosses above 20 EMA with positive RSI momentum
        if p_close <= p_ema20 and c_close > c_ema20 and 38 <= rsi <= 65:
            df.loc[df.index[i], 'Buy_Signal'] = df['Low'].iloc[i] * 0.985

        # 2. SELL / PROFIT BOOKING: Overbought exhaustion (RSI > 70) OR Price breaking below 20 EMA
        elif (rsi >= 70) or (p_close >= p_ema20 and c_close < c_ema20 and rsi < 52):
            df.loc[df.index[i], 'Sell_Signal'] = df['High'].iloc[i] * 1.015

    return df

def analyze_stock_adaptive(df, live_price=None):
    curr_price = live_price if live_price else float(df['Close'].iloc[-1])
    candles = len(df)
    is_fresh = candles < 50
    
    rsi = float(df['RSI'].iloc[-1])
    ema_20 = float(df['EMA_20'].iloc[-1])
    curr_vol = float(df['Volume'].iloc[-1])
    avg_vol = float(df['Vol_SMA'].iloc[-1])

    score = 0
    reasons = []

    # Trend Strength
    if curr_price > ema_20:
        score += 4.0
        reasons.append("Bullish Bias: Price holding strongly above 20-day EMA support.")
    else:
        reasons.append("Bearish Bias: Price trading under 20-day EMA pressure.")

    # RSI Check
    if 40 <= rsi <= 62:
        score += 3.5
        reasons.append(f"RSI ({rsi:.1f}): Sweet spot for fresh accumulation (Not Overheated).")
    elif rsi > 70:
        score += 1.0
        reasons.append(f"RSI ({rsi:.1f}): Overbought! High risk of sudden profit booking.")
    else:
        score += 1.5
        reasons.append(f"RSI ({rsi:.1f}): Near support/reversal zone.")

    # Volume Factor
    if curr_vol > avg_vol * 1.25:
        score += 2.5
        reasons.append("Strong Volume: High institutional or retail buying interest.")
    else:
        score += 1.0
        reasons.append("Volume: Normal daily average turnover.")

    score = round(min(10.0, score), 1)

    # Verdicts
    if score >= 7.0:
        verdict = "STRONG BUY"
        color = "#00c853"
        action = "High probability setup. Ideal to enter with disciplined stop-loss."
    elif score >= 5.0:
        verdict = "ACCUMULATE / DIP BUY"
        color = "#64dd17"
        action = "Positive momentum. Add slowly on intraday declines."
    elif score >= 3.5:
        verdict = "HOLD / CAUTION"
        color = "#ffd600"
        action = "Sideways consolidation. Wait for clear breakout above 20 EMA."
    else:
        verdict = "SELL / BOOK PROFIT"
        color = "#d50000"
        action = "Trend breakdown or overbought exhaustion. Book profit or exit."

    lookback = min(20, candles)
    support = float(df['Low'].tail(lookback).min())
    resistance = float(df['High'].tail(lookback).max())
    
    stop_loss = round(support * 0.985, 2)
    risk = max(3.0, curr_price - stop_loss)
    target_1 = round(curr_price + (risk * 1.2), 2)  # Partial Profit Booking Target
    target_2 = round(curr_price + (risk * 2.2), 2)  # Final Target

    return {
        "score": score,
        "verdict": verdict,
        "color": color,
        "action": action,
        "reasons": reasons,
        "price": curr_price,
        "rsi": rsi,
        "support": support,
        "resistance": resistance,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "is_fresh": is_fresh
    }

# ----------------- UI / SIDEBAR -----------------
st.sidebar.title("🔍 Stock Scanner")

default_basket = [
    "BLS.NS",
    "BLSE.NS",
    "JIOFIN.NS",
    "TATATECH.NS",
    "SWIGGY.NS",
    "ZOMATO.NS",
    "COALINDIA.NS",
    "RELIANCE.NS"
]

selected_picker = st.sidebar.selectbox("Trending / Watchlist:", default_basket)
user_search = st.sidebar.text_input("Search Any Stock (e.g. BLS, JIO, SWIGGY, TCS):", "").strip()

active_symbol, default_name = resolve_ticker_and_name(user_search) if user_search else (selected_picker, None)
company_name = default_name if default_name else fetch_company_full_name(active_symbol)

time_period = st.sidebar.selectbox("Chart Period", ["3mo", "6mo", "1y", "2y"], index=2)

st.title("📈 AI Stock Screener & Real-Time Trading Signals")
st.caption("Live Candlestick Chart with Automatic BUY / PROFIT BOOKING Signals & Multi-Target Risk Management")

# ----------------- MAIN DATA PROCESSING -----------------
try:
    with st.spinner(f"Loading data & signals for {company_name}..."):
        t_active = yf.Ticker(active_symbol)
        df_hist = t_active.history(period=time_period)

        if df_hist.empty or len(df_hist) < 3:
            df_hist = t_active.history(period="max")

        if df_hist.empty or len(df_hist) < 3:
            st.error(f"'{active_symbol}' ka data nahi mil paya. Kripya symbol check karein.")
            st.stop()

        df_hist = calculate_adaptive_indicators(df_hist)
        g_live = fetch_google_finance_live(active_symbol)
        analysis = analyze_stock_adaptive(df_hist, g_live)

        # ----------------- COMPANY FULL NAME HEADER -----------------
        st.markdown(f"""
            <div class="company-header">
                <h2 style="margin: 0; color: #ffffff;">🏢 {company_name}</h2>
                <span style="color: #58a6ff; font-weight: 600;">NSE Ticker: {active_symbol}</span>
                {" | <span style='color: #ff9800; font-weight: 600;'>[🆕 IPO / Fresh Listing Mode]</span>" if analysis['is_fresh'] else ""}
            </div>
        """, unsafe_allow_html=True)

        # ----------------- METRICS CARDS (TARGETS & STOPLOSS) -----------------
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Current Market Price", f"₹{analysis['price']:,.2f}")
        c2.metric("Composite Score", f"{analysis['score']} / 10")
        c3.metric("Stop-Loss (SL)", f"₹{analysis['stop_loss']:,.2f}")
        c4.metric("Target 1 (Book 50%)", f"₹{analysis['target_1']:,.2f}")
        c5.metric("Target 2 (Final)", f"₹{analysis['target_2']:,.2f}")

        # VERDICT BANNER
        st.markdown(f"""
            <div style="background: linear-gradient(90deg, {analysis['color']}22, #161c28); 
                        border: 1px solid {analysis['color']}; 
                        border-left: 6px solid {analysis['color']}; 
                        padding: 15px 20px; 
                        border-radius: 8px; 
                        margin: 15px 0;">
                <h3 style="color: {analysis['color']}; margin: 0;">Market Verdict: {analysis['verdict']}</h3>
                <p style="font-size: 15px; margin-top: 6px; margin-bottom: 0; color: #cbd5e1;">{analysis['action']}</p>
            </div>
        """, unsafe_allow_html=True)

        # ----------------- TABS -----------------
        tab_chart, tab_tech, tab_radar = st.tabs([
            "📊 Candlestick Chart with Buy/Sell Signals",
            "⚡ Technical Factors & Levels",
            "🎯 Next Session Radar"
        ])

        # TAB 1: CHART WITH DIRECT BUY/SELL MARKERS
        with tab_chart:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df_hist.index, open=df_hist['Open'], high=df_hist['High'], low=df_hist['Low'], close=df_hist['Close'],
                name='Price'
            ), row=1, col=1)

            # EMAs
            if 'EMA_20' in df_hist:
                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA_20'], line=dict(color='yellow', width=1.2), name='20 EMA'), row=1, col=1)
            if 'EMA_50' in df_hist and pd.notna(df_hist['EMA_50'].iloc[-1]):
                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA_50'], line=dict(color='orange', width=1.2), name='50 EMA'), row=1, col=1)
            if 'EMA_200' in df_hist and pd.notna(df_hist['EMA_200'].iloc[-1]):
                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA_200'], line=dict(color='cyan', width=1.5), name='200 EMA'), row=1, col=1)

            # --- PLOT BUY SIGNALS (GREEN UP TRIANGLES) ---
            buys = df_hist[df_hist['Buy_Signal'].notna()]
            if not buys.empty:
                fig.add_trace(go.Scatter(
                    x=buys.index,
                    y=buys['Buy_Signal'],
                    mode='markers+text',
                    marker=dict(symbol='triangle-up', size=14, color='#00e676', line=dict(width=1, color='white')),
                    text=['BUY'] * len(buys),
                    textposition='bottom center',
                    textfont=dict(color='#00e676', size=10, family="Arial Black"),
                    name='BUY Signal'
                ), row=1, col=1)

            # --- PLOT SELL / PROFIT BOOKING SIGNALS (RED DOWN TRIANGLES) ---
            sells = df_hist[df_hist['Sell_Signal'].notna()]
            if not sells.empty:
                fig.add_trace(go.Scatter(
                    x=sells.index,
                    y=sells['Sell_Signal'],
                    mode='markers+text',
                    marker=dict(symbol='triangle-down', size=14, color='#ff1744', line=dict(width=1, color='white')),
                    text=['PROFIT BOOK / SELL'] * len(sells),
                    textposition='top center',
                    textfont=dict(color='#ff1744', size=10, family="Arial Black"),
                    name='SELL / Book Profit'
                ), row=1, col=1)

            # Volume Bars
            vol_colors = ['#00c853' if r['Close'] >= r['Open'] else '#d50000' for _, r in df_hist.iterrows()]
            fig.add_trace(go.Bar(x=df_hist.index, y=df_hist['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)

            fig.update_layout(
                title=f"{company_name} ({active_symbol}) - Price Action & Signals",
                height=560,
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        # TAB 2: TECHNICAL DETAILS
        with tab_tech:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.write("#### 🎯 Execution Strategy:")
                for r in analysis['reasons']:
                    st.write(f"• {r}")
                st.info(f"💡 **Profit Booking Rule:** Target 1 (₹{analysis['target_1']:,.2f}) aane par 50% quantity book karein aur baaki quantity ka Stop-Loss apne Buy Price par trail kar dein.")
            with col_t2:
                st.write("#### 📌 Key Price Benchmarks:")
                st.write(f"• **Recent Support (Swing Low):** ₹{analysis['support']:,.2f}")
                st.write(f"• **Recent Resistance (Swing High):** ₹{analysis['resistance']:,.2f}")
                st.write(f"• **14-Period RSI:** {analysis['rsi']:.2f}")
                st.write(f"• **Total Trading History:** {len(df_hist)} sessions")

        # TAB 3: NEXT SESSION RADAR
        with tab_radar:
            st.subheader("🎯 Next Session Action Watchlist")
            radar_rows = []
            for s in default_basket:
                try:
                    h = yf.Ticker(s).history(period="6mo")
                    if len(h) >= 3:
                        h = calculate_adaptive_indicators(h)
                        gp = fetch_google_finance_live(s)
                        an = analyze_stock_adaptive(h, gp)
                        c_name = fetch_company_full_name(s)
                        radar_rows.append({
                            "Company": c_name,
                            "Ticker": s.replace(".NS", ""),
                            "Price": f"₹{an['price']:,.2f}",
                            "Action": an['verdict'],
                            "Stop-Loss": f"₹{an['stop_loss']:,.2f}",
                            "Target 1": f"₹{an['target_1']:,.2f}",
                            "Target 2": f"₹{an['target_2']:,.2f}"
                        })
                except Exception:
                    continue
            if radar_rows:
                st.dataframe(pd.DataFrame(radar_rows), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error loading dashboard: {str(e)}")
