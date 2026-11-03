import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- PAGE CONFIG & THEME -----------------
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
    </style>
""", unsafe_allow_html=True)

# ----------------- GOOGLE FINANCE LIVE SCRAPER -----------------
@st.cache_data(ttl=60)
def fetch_google_finance_live(ticker, exchange="NSE"):
    """
    Fetches real-time price and daily stats directly from Google Finance
    without needing any broker API or keys.
    """
    clean_ticker = ticker.replace(".NS", "").replace(".BO", "").strip().upper()
    url = f"https://www.google.com/finance/quote/{clean_ticker}:{exchange}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Current price element on Google Finance
        price_elem = soup.find("div", class_="YMlKec fxKbKc")
        if not price_elem:
            return None

        price_str = price_elem.text.replace("₹", "").replace(",", "").strip()
        live_price = float(price_str)

        # Daily change %
        pct_elem = soup.find("div", class_="JwB6zf")
        pct_change = pct_elem.text.strip() if pct_elem else "0.0%"

        return {
            "price": live_price,
            "change_pct": pct_change,
            "source": "Google Finance Live"
        }
    except Exception:
        return None

# ----------------- TECHNICAL INDICATORS -----------------
def calculate_indicators(df):
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    return df

def analyze_signals(df, live_price=None):
    curr_price = live_price if live_price else float(df['Close'].iloc[-1])
    rsi = float(df['RSI'].iloc[-1])
    ema_20 = float(df['EMA_20'].iloc[-1])
    ema_50 = float(df['EMA_50'].iloc[-1])
    ema_200 = float(df['EMA_200'].iloc[-1])
    macd = float(df['MACD'].iloc[-1])
    signal = float(df['Signal_Line'].iloc[-1])
    curr_vol = float(df['Volume'].iloc[-1])
    avg_vol = float(df['Vol_SMA20'].iloc[-1])

    score = 0
    reasons = []

    # Trend logic
    if curr_price > ema_50 and ema_50 > ema_200:
        score += 3.5
        reasons.append("Bullish Trend: Price trading firmly above 50 & 200 EMA.")
    elif curr_price > ema_20:
        score += 2.0
        reasons.append("Short-term Momentum: Holding above 20-day EMA.")
    else:
        reasons.append("Weakness: Trading below key moving averages.")

    # RSI
    if 35 <= rsi <= 55:
        score += 3.0
        reasons.append(f"RSI ({rsi:.1f}): Reversal accumulation zone.")
    elif 55 < rsi <= 68:
        score += 2.5
        reasons.append(f"RSI ({rsi:.1f}): Active bullish momentum.")
    elif rsi > 70:
        score += 0.5
        reasons.append(f"RSI ({rsi:.1f}): Overbought territory (pullback risk).")
    else:
        score += 1.0
        reasons.append(f"RSI ({rsi:.1f}): Deep oversold zone.")

    # MACD
    if macd > signal:
        score += 2.0
        reasons.append("MACD: Positive crossover active.")
    else:
        reasons.append("MACD: Negative downward pressure.")

    # Volume
    if curr_vol > avg_vol * 1.3:
        score += 1.5
        reasons.append("Volume Breakout: Heavy buyer participation today.")
    else:
        reasons.append("Volume: Normal baseline activity.")

    score = round(score, 1)

    if score >= 7.5:
        verdict = "STRONG BUY"
        color = "#00c853"
        action = "High-probability setup for tomorrow's opening. Keep trailing stop-loss."
    elif score >= 5.5:
        verdict = "BUY / ACCUMULATE"
        color = "#64dd17"
        action = "Positive setup. Suitable to enter on intraday dips."
    elif score >= 4.0:
        verdict = "HOLD / NEUTRAL"
        color = "#ffd600"
        action = "Range-bound movement. Avoid fresh high entry."
    else:
        verdict = "SELL / AVOID"
        color = "#d50000"
        action = "Deteriorating technical levels. Book profits or avoid fresh buy."

    support = float(df['Low'].tail(20).min())
    resistance = float(df['High'].tail(20).max())
    stop_loss = round(support * 0.985, 2)
    target = round(curr_price + (curr_price - stop_loss) * 2, 2)

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
        "target": target
    }

# ----------------- UI / SIDEBAR -----------------
st.sidebar.title(" Google Finance Radar")

# Daily Watchlist pool
default_basket = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "TATAMOTORS.NS", "HDFCBANK.NS", "SBIN.NS", "ITC.NS", "COALINDIA.NS"]
selected_ticker = st.sidebar.selectbox("Select Active Stock:", default_basket)
custom_ticker = st.sidebar.text_input("Or Search Any Ticker (e.g. ZOMATO.NS, JIOFIN.NS):", "").strip().upper()

active_symbol = custom_ticker if custom_ticker else selected_ticker

st.title(" AI Stock Screener & Tomorrow's Buy Watchlist")
st.caption("Real-time pricing synced with Google Finance | Quantitative 10-Point Technical Engine")

# ----------------- TABS: TOMORROW'S WATCHLIST & DEEP ANALYSIS -----------------
tab_radar, tab_chart, tab_tech = st.tabs([
    " Tomorrow's Action Watchlist",
    " Interactive Candlestick Chart",
    " Technical Breakdown"
])

# TAB 1: AUTOMATED RADAR FOR TOMORROW'S MARKET OPEN
with tab_radar:
    st.subheader(" Scanner: Best Stocks for Tomorrow's Session")
    st.write("Calculated on End-of-Day Momentum, Volume Surge, and EMA Alignment:")

    radar_results = []
    with st.spinner("Scanning basket using Google Finance & Technical Indicators..."):
        for sym in default_basket:
            try:
                hist = yf.Ticker(sym).history(period="6mo")
                if len(hist) > 30:
                    hist = calculate_indicators(hist)
                    g_data = fetch_google_finance_live(sym)
                    live_p = g_data['price'] if g_data else None
                    res = analyze_signals(hist, live_p)
                    
                    radar_results.append({
                        "Stock": sym.replace(".NS", ""),
                        "Live Price": f"₹{res['price']:,.2f}",
                        "Signal": res['verdict'],
                        "Score": f"{res['score']} / 10",
                        "Entry Zone": f"₹{res['price']:,.2f}",
                        "Suggested SL": f"₹{res['stop_loss']:,.2f}",
                        "Target": f"₹{res['target']:,.2f}"
                    })
            except Exception:
                continue

    if radar_results:
        radar_df = pd.DataFrame(radar_results)
        # Sort so highest score / Strong Buy appears on top
        st.dataframe(radar_df, use_container_width=True, hide_index=True)
    else:
        st.info("Scanner running... Click Refresh to update quotes.")

# ----------------- ACTIVE STOCK EVALUATION -----------------
st.divider()
try:
    hist = yf.Ticker(active_symbol).history(period="1y")
    if hist.empty or len(hist) < 30:
        st.error(f"Data not available for {active_symbol}. Please ensure the ticker format is correct.")
        st.stop()

    hist = calculate_indicators(hist)
    g_data = fetch_google_finance_live(active_symbol)
    live_price = g_data['price'] if g_data else float(hist['Close'].iloc[-1])
    price_tag = f"₹{live_price:,.2f}" + (f" ({g_data['change_pct']})" if g_data else "")

    analysis = analyze_signals(hist, live_price)

    st.subheader(f" Detailed Analysis: {active_symbol}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Live Market Price", price_tag)
    c2.metric("Composite Score", f"{analysis['score']} / 10")
    c3.metric("Key Stop-Loss", f"₹{analysis['stop_loss']:,.2f}")
    c4.metric("Estimated Target", f"₹{analysis['target']:,.2f}")

    # VERDICT BANNER
    st.markdown(f"""
        <div style="background: linear-gradient(90deg, {analysis['color']}20, #161c28); 
                    border: 1px solid {analysis['color']}; 
                    border-left: 6px solid {analysis['color']}; 
                    padding: 16px 20px; 
                    border-radius: 8px; 
                    margin: 15px 0;">
            <h3 style="color: {analysis['color']}; margin: 0;">Decision: {analysis['verdict']}</h3>
            <p style="font-size: 15px; margin-top: 6px; margin-bottom: 0; color: #cbd5e1;">{analysis['action']}</p>
        </div>
    """, unsafe_allow_html=True)

    # TAB 2: CHART
    with tab_chart:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA_20'], line=dict(color='yellow', width=1), name='20 EMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA_50'], line=dict(color='orange', width=1.2), name='50 EMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA_200'], line=dict(color='cyan', width=1.5), name='200 EMA'), row=1, col=1)

        vol_colors = ['#00c853' if r['Close'] >= r['Open'] else '#d50000' for _, r in hist.iterrows()]
        fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)

        fig.update_layout(height=540, margin=dict(l=10, r=10, t=20, b=10), xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    # TAB 3: TECHNICAL SUMMARY
    with tab_tech:
        c_t1, c_t2 = st.columns(2)
        with c_t1:
            st.write("#### Key Decision Factors:")
            for r in analysis['reasons']:
                st.write(f"• {r}")
        with c_t2:
            st.write("#### Price Benchmarks:")
            st.write(f"• **20-Day Support:** ₹{analysis['support']:,.2f}")
            st.write(f"• **20-Day Resistance:** ₹{analysis['resistance']:,.2f}")
            st.write(f"• **14-Period RSI:** {analysis['rsi']:.2f}")

except Exception as e:
    st.error(f"Error loading dashboard: {str(e)}")
