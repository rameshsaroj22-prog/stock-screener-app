import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- PAGE CONFIG & FINTECH THEME -----------------
st.set_page_config(page_title="AI Stock Screener & IPO Radar", layout="wide", initial_sidebar_state="expanded")

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
    </style>
""", unsafe_allow_html=True)

# ----------------- SMART SYMBOL MAPPER -----------------
# Agar user common naam likhe to automatic NSE symbol me badal jaye
COMMON_NAME_MAP = {
    "JIO": "JIOFIN.NS",
    "JIOFIN": "JIOFIN.NS",
    "JIO PLATFORM": "JIOFIN.NS",
    "JIO FINANCIAL": "JIOFIN.NS",
    "BLS": "BLSE.NS",
    "BLSE": "BLSE.NS",
    "BLS INTERNATIONAL": "BLS.NS",
    "BLS E-SERVICES": "BLSE.NS",
    "TATATECH": "TATATECH.NS",
    "TATA TECH": "TATATECH.NS",
    "SWIGGY": "SWIGGY.NS",
    "ZOMATO": "ZOMATO.NS",
    "HYUNDAI": "HYUNDAI.NS",
    "OLA": "OLAELEC.NS",
    "OLAELEC": "OLAELEC.NS",
    "COAL": "COALINDIA.NS"
}

def resolve_ticker(user_input):
    clean = user_input.strip().upper()
    if clean in COMMON_NAME_MAP:
        return COMMON_NAME_MAP[clean]
    if not clean.endswith(".NS") and not clean.endswith(".BO") and len(clean) > 0:
        # Default assume Indian NSE
        return f"{clean}.NS"
    return clean

# ----------------- GOOGLE FINANCE LIVE SCRAPER -----------------
@st.cache_data(ttl=60)
def fetch_google_finance_live(ticker):
    """Fetches real-time price directly from Google Finance."""
    clean_sym = ticker.replace(".NS", "").replace(".BO", "").strip().upper()
    url = f"https://www.google.com/finance/quote/{clean_sym}:NSE"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            elem = soup.find("div", class_="YMlKec fxKbKc")
            if elem:
                price_val = float(elem.text.replace("₹", "").replace(",", "").strip())
                return price_val
    except Exception:
        pass
    return None

# ----------------- ADAPTIVE INDICATOR ENGINE (NEW IPO FRIENDLY) -----------------
def calculate_adaptive_indicators(df):
    total_candles = len(df)
    
    # Adaptive EMAs: Jitna data available ho utne ka EMA nikalein
    if total_candles >= 5:
        df['EMA_5'] = df['Close'].ewm(span=min(5, total_candles), adjust=False).mean()
    if total_candles >= 20:
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    else:
        df['EMA_20'] = df['Close'].ewm(span=total_candles, adjust=False).mean()

    if total_candles >= 50:
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    else:
        df['EMA_50'] = np.nan

    if total_candles >= 200:
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    else:
        df['EMA_200'] = np.nan

    # RSI (14) ya shorter window for fresh listings
    rsi_window = 14 if total_candles >= 15 else max(3, total_candles - 1)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_window).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50.0)

    # Volume SMA
    vol_win = min(20, total_candles)
    df['Vol_SMA'] = df['Volume'].rolling(window=vol_win).mean()

    return df

def analyze_stock_adaptive(df, live_price=None):
    curr_price = live_price if live_price else float(df['Close'].iloc[-1])
    candles = len(df)
    is_fresh_listing = candles < 50
    
    rsi = float(df['RSI'].iloc[-1])
    ema_20 = float(df['EMA_20'].iloc[-1]) if 'EMA_20' in df else curr_price
    curr_vol = float(df['Volume'].iloc[-1])
    avg_vol = float(df['Vol_SMA'].iloc[-1]) if 'Vol_SMA' in df else curr_vol

    score = 0
    reasons = []

    if is_fresh_listing:
        reasons.append(f"📌 Fresh Listing / Recent IPO: Trading history is {candles} days old.")
        # Short-term IPO momentum checks
        if curr_price > ema_20:
            score += 4.0
            reasons.append("Short-term Uptrend: Holding above its 20-day moving average.")
        else:
            reasons.append("Under Pressure: Trading below its initial listing moving average.")

        # RSI Momentum for IPOs
        if 40 <= rsi <= 65:
            score += 3.5
            reasons.append(f"Healthy RSI ({rsi:.1f}): Steady accumulation without being overbought.")
        elif rsi > 70:
            score += 1.5
            reasons.append(f"Overheated RSI ({rsi:.1f}): High volatility risk after listing.")
        else:
            score += 1.5
            reasons.append(f"Subdued RSI ({rsi:.1f}): Post-listing base building.")

    else:
        # Full technical assessment for matured stocks
        ema_50 = float(df['EMA_50'].iloc[-1]) if pd.notna(df['EMA_50'].iloc[-1]) else ema_20
        ema_200 = float(df['EMA_200'].iloc[-1]) if pd.notna(df['EMA_200'].iloc[-1]) else ema_50

        if curr_price > ema_50 and ema_50 >= ema_200:
            score += 4.0
            reasons.append("Strong Bullish Trend: Trading above 50 & 200 EMA.")
        elif curr_price > ema_20:
            score += 2.5
            reasons.append("Active Momentum: Holding firmly above 20 EMA.")
        else:
            reasons.append("Weakness: Below major EMAs.")

        if 35 <= rsi <= 60:
            score += 3.5
            reasons.append(f"RSI ({rsi:.1f}): Prime accumulation zone.")
        elif rsi > 70:
            score += 1.0
            reasons.append(f"RSI ({rsi:.1f}): Overbought (short-term caution).")
        else:
            score += 1.5
            reasons.append(f"RSI ({rsi:.1f}): Oversold rebound candidate.")

    # Volume Factor
    if curr_vol > avg_vol * 1.2:
        score += 2.5
        reasons.append("Volume Surge: Higher than average buying interest.")
    else:
        score += 1.0
        reasons.append("Volume: Normal trading flow.")

    score = round(min(10.0, score), 1)

    if score >= 7.0:
        verdict = "STRONG BUY"
        color = "#00c853"
        action = "High momentum breakout. Good candidate for tomorrow's opening dip."
    elif score >= 5.0:
        verdict = "BUY / ACCUMULATE"
        color = "#64dd17"
        action = "Positive accumulation structure. Suitable for staged buying."
    elif score >= 3.5:
        verdict = "HOLD / NEUTRAL"
        color = "#ffd600"
        action = "Consolidation phase. Wait for a clear directional breakout."
    else:
        verdict = "SELL / AVOID"
        color = "#d50000"
        action = "Persistent selling pressure. Keep strict stop-loss or stay away."

    lookback = min(20, candles)
    support = float(df['Low'].tail(lookback).min())
    resistance = float(df['High'].tail(lookback).max())
    stop_loss = round(support * 0.985, 2)
    target = round(curr_price + max(5.0, (curr_price - stop_loss) * 2), 2)

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
        "target": target,
        "is_fresh": is_fresh_listing
    }

# ----------------- UI / SIDEBAR -----------------
st.sidebar.title("🔍 Stock & IPO Screener")

# Basket with popular newly listed + established stocks
default_basket = [
    "JIOFIN.NS",     # Jio Financial Services
    "BLSE.NS",       # BLS E-Services (Recent Listing)
    "BLS.NS",        # BLS International
    "TATATECH.NS",   # Tata Technologies
    "SWIGGY.NS",     # Swiggy
    "ZOMATO.NS",     # Zomato
    "RELIANCE.NS",
    "TCS.NS"
]

selected_picker = st.sidebar.selectbox("Trending / New Listings:", default_basket)
user_search = st.sidebar.text_input("Search Any Stock (e.g. BLS, JIO, SWIGGY, INFY):", "").strip()

active_symbol = resolve_ticker(user_search) if user_search else selected_picker

st.title("📈 AI Stock Screener & Tomorrow's Focus List")
st.caption("Works for Fresh IPOs, Newly Listed Companies & Established Giants | Google Finance Synced")

# ----------------- TABS -----------------
tab_radar, tab_chart, tab_tech = st.tabs([
    "🎯 Tomorrow's Buy Radar",
    "📊 Candlestick Chart",
    "⚡ Technical Factors"
])

# TAB 1: RADAR TABLE (SCANS NEW & OLD STOCKS ALIKE)
with tab_radar:
    st.subheader("🎯 Scanner: Action Stocks for Next Session")
    st.write("Dynamic scan across trending newly listed companies and core leaders:")

    radar_rows = []
    with st.spinner("Analyzing basket with real-time indicators..."):
        for sym in default_basket:
            try:
                # Fetch max history available without hardcoding 1y
                t = yf.Ticker(sym)
                h = t.history(period="6mo")
                if len(h) >= 3:
                    h = calculate_adaptive_indicators(h)
                    g_price = fetch_google_finance_live(sym)
                    res = analyze_stock_adaptive(h, g_price)
                    
                    category = "🆕 New IPO" if res['is_fresh'] else "🏢 Regular"
                    radar_rows.append({
                        "Type": category,
                        "Stock": sym.replace(".NS", ""),
                        "Live Price": f"₹{res['price']:,.2f}",
                        "Signal": res['verdict'],
                        "Score": f"{res['score']} / 10",
                        "Key Support": f"₹{res['support']:,.2f}",
                        "Stop-Loss": f"₹{res['stop_loss']:,.2f}",
                        "Target": f"₹{res['target']:,.2f}"
                    })
            except Exception:
                continue

    if radar_rows:
        df_radar = pd.DataFrame(radar_rows)
        st.dataframe(df_radar, use_container_width=True, hide_index=True)
    else:
        st.info("Scanner refreshing... Please wait.")

# ----------------- ACTIVE STOCK DETAILS -----------------
st.divider()
try:
    with st.spinner(f"Loading data for {active_symbol}..."):
        t_active = yf.Ticker(active_symbol)
        df_hist = t_active.history(period="1y")

        # Agar 1y me data kam hai, to 'max' period try karein
        if df_hist.empty or len(df_hist) < 3:
            df_hist = t_active.history(period="max")

        if df_hist.empty or len(df_hist) < 3:
            st.error(f"'{active_symbol}' ka data find nahi hua. Kripya check karein ki symbol sahi hai (jaise JIOFIN.NS, BLSE.NS).")
            st.stop()

        df_hist = calculate_adaptive_indicators(df_hist)
        g_live = fetch_google_finance_live(active_symbol)
        analysis = analyze_stock_adaptive(df_hist, g_live)

        status_badge = " [🆕 Fresh Listing / IPO Mode]" if analysis['is_fresh'] else ""
        st.subheader(f"📊 Detailed Review: {active_symbol}{status_badge}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Live Market Price", f"₹{analysis['price']:,.2f}")
        c2.metric("Composite Score", f"{analysis['score']} / 10")
        c3.metric("Key Stop-Loss", f"₹{analysis['stop_loss']:,.2f}")
        c4.metric("Estimated Target", f"₹{analysis['target']:,.2f}")

        # DECISION BANNER
        st.markdown(f"""
            <div style="background: linear-gradient(90deg, {analysis['color']}22, #161c28); 
                        border: 1px solid {analysis['color']}; 
                        border-left: 6px solid {analysis['color']}; 
                        padding: 16px 20px; 
                        border-radius: 8px; 
                        margin: 15px 0;">
                <h3 style="color: {analysis['color']}; margin: 0;">Verdict: {analysis['verdict']}</h3>
                <p style="font-size: 15px; margin-top: 6px; margin-bottom: 0; color: #cbd5e1;">{analysis['action']}</p>
            </div>
        """, unsafe_allow_html=True)

        # TAB 2: CANDLESTICK CHART
        with tab_chart:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
            fig.add_trace(go.Candlestick(
                x=df_hist.index, open=df_hist['Open'], high=df_hist['High'], low=df_hist['Low'], close=df_hist['Close'], name='Price'
            ), row=1, col=1)

            if 'EMA_20' in df_hist:
                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA_20'], line=dict(color='yellow', width=1.2), name='20 EMA'), row=1, col=1)
            if 'EMA_50' in df_hist and pd.notna(df_hist['EMA_50'].iloc[-1]):
                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA_50'], line=dict(color='orange', width=1.2), name='50 EMA'), row=1, col=1)
            if 'EMA_200' in df_hist and pd.notna(df_hist['EMA_200'].iloc[-1]):
                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA_200'], line=dict(color='cyan', width=1.5), name='200 EMA'), row=1, col=1)

            vol_colors = ['#00c853' if r['Close'] >= r['Open'] else '#d50000' for _, r in df_hist.iterrows()]
            fig.add_trace(go.Bar(x=df_hist.index, y=df_hist['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)

            fig.update_layout(height=520, margin=dict(l=10, r=10, t=20, b=10), xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        # TAB 3: TECHNICAL SUMMARY
        with tab_tech:
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                st.write("#### Key Decision Factors:")
                for r in analysis['reasons']:
                    st.write(f"• {r}")
            with c_t2:
                st.write("#### Key Price Levels:")
                st.write(f"• **Support (Swing Low):** ₹{analysis['support']:,.2f}")
                st.write(f"• **Resistance (Swing High):** ₹{analysis['resistance']:,.2f}")
                st.write(f"• **RSI Value:** {analysis['rsi']:.2f}")
                st.write(f"• **Total Trading History:** {len(df_hist)} sessions")

except Exception as e:
    st.error(f"Error during analysis: {str(e)}")
