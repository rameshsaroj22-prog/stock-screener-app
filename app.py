import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- PAGE CONFIG -----------------
st.set_page_config(page_title="AI Stock Advisor & Screener", layout="wide", initial_sidebar_state="expanded")

# ----------------- CUSTOM PAGE STYLING (THEME COLOR UPDATE) -----------------
st.markdown("""
    <style>
    /* Main App Background */
    .stApp {
        background: linear-gradient(180deg, #0b0e14 0%, #101520 100%);
        color: #e6edf3;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #121722 !important;
        border-right: 1px solid #1f2937;
    }
    
    /* Top Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #161c28;
        border: 1px solid #232d3f;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
        font-weight: 500;
        font-size: 0.9rem;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-weight: 700;
    }

    /* Subheader & Section Titles */
    h1, h2, h3, h4 {
        color: #f0f6fc !important;
        font-weight: 600;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #21262d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 6px 6px 0px 0px;
        color: #8b949e;
        padding: 8px 16px;
        border: 1px solid #30363d;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f293d !important;
        color: #58a6ff !important;
        border-color: #388bfd !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- HELPER FUNCTIONS -----------------
def calculate_indicators(df):
    """Calculates EMA, RSI, and MACD on historical data."""
    # Exponential Moving Averages
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']

    # Volume 20 SMA
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    return df

def analyze_stock(info, hist):
    """Combines Technical and Fundamental metrics to score the stock."""
    curr_price = hist['Close'].iloc[-1]
    rsi = hist['RSI'].iloc[-1]
    ema_20 = hist['EMA_20'].iloc[-1]
    ema_50 = hist['EMA_50'].iloc[-1]
    ema_200 = hist['EMA_200'].iloc[-1]
    macd = hist['MACD'].iloc[-1]
    signal = hist['Signal_Line'].iloc[-1]
    curr_vol = hist['Volume'].iloc[-1]
    avg_vol = hist['Vol_SMA20'].iloc[-1]

    tech_score = 0
    tech_reasons = []

    # 1. Trend Analysis (EMA)
    if curr_price > ema_50 and ema_50 > ema_200:
        tech_score += 1.5
        tech_reasons.append("Strong Uptrend: Price trading above both 50 & 200 EMA (Bullish Golden Alignment).")
    elif curr_price > ema_20:
        tech_score += 0.75
        tech_reasons.append("Short-term Momentum: Finding support above the 20 EMA.")
    else:
        tech_reasons.append("Downtrend/Weakness: Price slipped below major Moving Averages.")

    # 2. RSI Check
    if 30 <= rsi <= 50:
        tech_score += 1.5
        tech_reasons.append(f"RSI Value ({rsi:.1f}): Stock is in Value/Reversal Support Zone.")
    elif 50 < rsi <= 68:
        tech_score += 1.0
        tech_reasons.append(f"RSI Value ({rsi:.1f}): Bullish momentum is active.")
    elif rsi > 70:
        tech_score += 0.2
        tech_reasons.append(f"RSI Value ({rsi:.1f}) - Overbought: High risk of near-term profit booking.")
    else:
        tech_score += 0.5
        tech_reasons.append(f"RSI Value ({rsi:.1f}) - Oversold: Heavy decline, await bounce confirmation.")

    # 3. MACD Check
    if macd > signal:
        tech_score += 1.0
        tech_reasons.append("MACD Bullish: MACD line is trading above the Signal line.")
    else:
        tech_reasons.append("MACD Bearish: Selling pressure is indicated.")

    # 4. Volume Check
    if curr_vol > avg_vol:
        tech_score += 1.0
        tech_reasons.append("High Volume: Strong institutional and buyer participation.")
    else:
        tech_reasons.append("Normal Volume: Trading volume is around the 20-day average.")

    # FUNDAMENTAL ANALYSIS
    fund_score = 0
    fund_reasons = []

    pe = info.get('trailingPE', None)
    roe = info.get('returnOnEquity', None)
    debt_equity = info.get('debtToEquity', None)
    profit_margin = info.get('profitMargins', None)

    # ROE Check
    if roe and roe > 0.15:
        fund_score += 1.5
        fund_reasons.append(f"Strong ROE: {roe*100:.1f}% (Company generating solid returns on equity).")
    elif roe and roe > 0.08:
        fund_score += 0.75
        fund_reasons.append(f"Moderate ROE: {roe*100:.1f}%.")
    else:
        fund_reasons.append("Weak return ratio (ROE).")

    # Debt Check
    if debt_equity is not None:
        debt_ratio = debt_equity / 100.0 if debt_equity > 10 else debt_equity
        if debt_ratio < 0.5:
            fund_score += 1.5
            fund_reasons.append(f"Low Debt / Safe: Debt-to-Equity {debt_ratio:.2f}.")
        elif debt_ratio <= 1.0:
            fund_score += 1.0
            fund_reasons.append(f"Controlled Debt: Debt-to-Equity {debt_ratio:.2f}.")
        else:
            fund_reasons.append(f"High Debt Risk: Debt-to-Equity {debt_ratio:.2f} (Elevated liabilities).")
    else:
        fund_score += 0.5

    # Profit Margins
    if profit_margin and profit_margin > 0.12:
        fund_score += 1.0
        fund_reasons.append(f"Healthy Margins: Net profit margin is {profit_margin*100:.1f}%.")
    elif profit_margin and profit_margin > 0:
        fund_score += 0.5
        fund_reasons.append(f"Net Profit Margin: {profit_margin*100:.1f}%.")
    else:
        fund_reasons.append("Company profit margin is weak or negative.")

    # PE Valuation
    if pe and 5 < pe < 35:
        fund_score += 1.0
        fund_reasons.append(f"Fair Valuation: P/E ratio is {pe:.1f}.")
    elif pe and pe >= 35:
        fund_score += 0.3
        fund_reasons.append(f"Premium Valuation: P/E ratio is {pe:.1f} (High valuation multiple).")
    else:
        fund_reasons.append("Valuation data is limited or negative earnings.")

    total_score = round(tech_score + fund_score, 1)

    # FINAL VERDICT
    if total_score >= 7.5:
        verdict = "STRONG BUY"
        verdict_color = "#00c853"
        action = "Strong confluence of technical breakout and solid fundamentals. Fresh entry recommended with defined stop-loss."
    elif total_score >= 6.0:
        verdict = "BUY / ACCUMULATE"
        verdict_color = "#64dd17"
        action = "Favorable trend. Suitable for steady accumulation on minor pullbacks/dips."
    elif total_score >= 4.0:
        verdict = "HOLD / NEUTRAL"
        verdict_color = "#ffd600"
        action = "Avoid aggressive fresh purchases. Existing investors can maintain position with trailing stop-loss."
    else:
        verdict = "SELL / AVOID"
        verdict_color = "#d50000"
        action = "Technical breakdown or deteriorating financial indicators. Consider booking profits or avoiding entry."

    # Target & Stop Loss Calculation
    support = hist['Low'].tail(20).min()
    resistance = hist['High'].tail(20).max()
    stop_loss = round(support * 0.98, 2)
    target = round(curr_price + (curr_price - stop_loss) * 2, 2)

    return {
        "score": total_score,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "action": action,
        "tech_score": tech_score,
        "fund_score": fund_score,
        "tech_reasons": tech_reasons,
        "fund_reasons": fund_reasons,
        "curr_price": curr_price,
        "rsi": rsi,
        "stop_loss": stop_loss,
        "target": target,
        "support": support,
        "resistance": resistance
    }

# ----------------- UI / SIDEBAR -----------------
st.sidebar.title("🔍 Stock Scanner")
symbol_input = st.sidebar.text_input("Enter Stock Ticker", value="COALINDIA.NS")
st.sidebar.caption("💡 For Indian stocks, append .NS or .BO (e.g. RELIANCE.NS, COALINDIA.NS, INFY.NS). For US stocks: AAPL, TSLA, NVDA.")

time_period = st.sidebar.selectbox("Timeframe", ["6mo", "1y", "2y", "5y"], index=1)

# ----------------- MAIN EXECUTION -----------------
st.title("📈 AI Stock Fundamental & Technical Advisor")

if symbol_input:
    with st.spinner(f"Fetching data and running analysis for {symbol_input}..."):
        try:
            ticker = yf.Ticker(symbol_input.strip().upper())
            df = ticker.history(period=time_period)

            if df.empty or len(df) < 50:
                st.error("No sufficient historical data found for this symbol. Please verify the ticker format.")
                st.stop()

            df = calculate_indicators(df)
            info = ticker.info
            analysis = analyze_stock(info, df)

            # TOP SUMMARY METRICS BAR
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Market Price", f"₹{analysis['curr_price']:,.2f}")
            c2.metric("Composite Score", f"{analysis['score']} / 10")
            c3.metric("Suggested Stop-Loss", f"₹{analysis['stop_loss']:,.2f}")
            c4.metric("Estimated Target", f"₹{analysis['target']:,.2f}")

            # DECISION BANNER (CUSTOM FINTECH CARD)
            st.markdown(f"""
                <div style="background: linear-gradient(90deg, {analysis['verdict_color']}18, #161c28); 
                            border: 1px solid {analysis['verdict_color']}; 
                            border-left: 6px solid {analysis['verdict_color']}; 
                            padding: 18px 24px; 
                            border-radius: 10px; 
                            margin: 20px 0;">
                    <h2 style="color: {analysis['verdict_color']}; margin: 0; font-size: 1.6rem; letter-spacing: 0.5px;">
                        Verdict: {analysis['verdict']}
                    </h2>
                    <p style="font-size: 15px; margin-top: 8px; margin-bottom: 0; color: #cbd5e1;">
                        {analysis['action']}
                    </p>
                </div>
            """, unsafe_allow_html=True)

            # TABS FOR DEEP ANALYSIS
            tab_chart, tab_tech, tab_fund = st.tabs([
                "📊 Interactive Candlestick Chart", 
                "⚡ Technical Analysis", 
                "🏢 Fundamental Ratios"
            ])

            # TAB 1: CHART (UNCHANGED CHART COLOUR CODES)
            with tab_chart:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
                
                # Candlesticks
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                    name='Price'
                ), row=1, col=1)

                # EMAs (Colors remain: yellow, orange, cyan)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name='20 EMA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='orange', width=1.2), name='50 EMA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='cyan', width=1.5), name='200 EMA'), row=1, col=1)

                # Volume Bar (Colors remain: green, red)
                colors = ['green' if row['Close'] >= row['Open'] else 'red' for _, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

                fig.update_layout(
                    height=580,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark"
                )
                st.plotly_chart(fig, use_container_width=True)

            # TAB 2: TECHNICAL DETAILS
            with tab_tech:
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.subheader(f"Technical Score: {analysis['tech_score']} / 5")
                    for reason in analysis['tech_reasons']:
                        st.write(f"• {reason}")
                with col_t2:
                    st.subheader("Key Price Levels")
                    st.write(f"• **20-Day Support:** ₹{analysis['support']:,.2f}")
                    st.write(f"• **20-Day Resistance:** ₹{analysis['resistance']:,.2f}")
                    st.write(f"• **14-Period RSI:** {analysis['rsi']:.2f}")

            # TAB 3: FUNDAMENTALS
            with tab_fund:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.subheader(f"Fundamental Score: {analysis['fund_score']} / 5")
                    for reason in analysis['fund_reasons']:
                        st.write(f"• {reason}")
                with col_f2:
                    st.subheader("Financial Snapshot")
                    st.write(f"• **Market Cap:** ₹{info.get('marketCap', 0):,}")
                    st.write(f"• **P/E Ratio:** {info.get('trailingPE', 'N/A')}")
                    st.write(f"• **Book Value:** ₹{info.get('bookValue', 'N/A')}")
                    st.write(f"• **52-Week High:** ₹{info.get('fiftyTwoWeekHigh', 'N/A')}")
                    st.write(f"• **52-Week Low:** ₹{info.get('fiftyTwoWeekLow', 'N/A')}")

        except Exception as e:
            st.error(f"Error during analysis: {str(e)}")
