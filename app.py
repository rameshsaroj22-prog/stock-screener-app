import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- PAGE CONFIG -----------------
st.set_page_config(page_title="AI Stock Analyzer & Screener", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .metric-card {
        background-color: #1e222d;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #2962ff;
        margin-bottom: 10px;
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
        tech_reasons.append("मजबूत अपट्रेंड: शेयर का भाव 50 और 200 EMA के ऊपर ट्रेड कर रहा है (Bullish Alignment)।")
    elif curr_price > ema_20:
        tech_score += 0.75
        tech_reasons.append("शॉर्ट-टर्म मोमेंटम: 20 EMA से ऊपर सपोर्ट ले रहा है।")
    else:
        tech_reasons.append("डाउनट्रेंड/कमजोरी: शेयर प्रमुख मूविंग एवरेज के नीचे फिसल चुका है।")

    # 2. RSI Check
    if 30 <= rsi <= 50:
        tech_score += 1.5
        tech_reasons.append(f"RSI वैल्यू {rsi:.1f} है: शेयर वैल्यू जोन/रिवर्सल एरिया में है।")
    elif 50 < rsi <= 68:
        tech_score += 1.0
        tech_reasons.append(f"RSI वैल्यू {rsi:.1f} है: बुलिश मोमेंटम एक्टिव है।")
    elif rsi > 70:
        tech_score += 0.2
        tech_reasons.append(f"RSI {rsi:.1f} (Overbought): नई खरीदारी पर मुनाफावसूली का जोखिम हो सकता है।")
    else:
        tech_score += 0.5
        tech_reasons.append(f"RSI {rsi:.1f} (Oversold): भारी गिरावट, बाउंसबैक का इंतजार करें।")

    # 3. MACD Check
    if macd > signal:
        tech_score += 1.0
        tech_reasons.append("MACD बुलिश: MACD लाइन सिग्नल लाइन के ऊपर ट्रेड कर रही है।")
    else:
        tech_reasons.append("MACD बेयरिश: सेलिंग प्रेशर का संकेत।")

    # 4. Volume Check
    if curr_vol > avg_vol:
        tech_score += 1.0
        tech_reasons.append("हाई वॉल्यूम: संस्थागत और बड़े खरीदारों की सक्रियता दिख रही है।")
    else:
        tech_reasons.append("नॉर्मल वॉल्यूम: ट्रेडिंग वॉल्यूम औसत स्तर पर है।")

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
        fund_reasons.append(f"मजबूत ROE: {roe*100:.1f}% (कंपनी अपनी पूंजी पर बेहतरीन रिटर्न दे रही है)।")
    elif roe and roe > 0.08:
        fund_score += 0.75
        fund_reasons.append(f"औसत ROE: {roe*100:.1f}%.")
    else:
        fund_reasons.append("कमजोर रिटर्न रेश्यो (ROE)।")

    # Debt Check
    if debt_equity is not None:
        debt_ratio = debt_equity / 100.0 if debt_equity > 10 else debt_equity
        if debt_ratio < 0.5:
            fund_score += 1.5
            fund_reasons.append(f"कर्जमुक्त/सुरक्षित: Debt-to-Equity {debt_ratio:.2f} (बहुत कम कर्ज)।")
        elif debt_ratio <= 1.0:
            fund_score += 1.0
            fund_reasons.append(f"नियंत्रित कर्ज: Debt-to-Equity {debt_ratio:.2f}।")
        else:
            fund_reasons.append(f"हाई डेट रिस्क: Debt-to-Equity {debt_ratio:.2f} (कंपनी पर अधिक कर्ज है)।")
    else:
        fund_score += 0.5

    # Profit Margins
    if profit_margin and profit_margin > 0.12:
        fund_score += 1.0
        fund_reasons.append(f"हेल्दी मार्जिन: नेट प्रॉफिट मार्जिन {profit_margin*100:.1f}% है।")
    elif profit_margin and profit_margin > 0:
        fund_score += 0.5
        fund_reasons.append(f"प्रॉफिट मार्जिन: {profit_margin*100:.1f}%।")
    else:
        fund_reasons.append("कंपनी का प्रॉफिट मार्जिन कमजोर या नकारात्मक है।")

    # PE Valuation
    if pe and 5 < pe < 35:
        fund_score += 1.0
        fund_reasons.append(f"उचित मूल्यांकन (Fair Valuation): P/E रेशियो {pe:.1f} है।")
    elif pe and pe >= 35:
        fund_score += 0.3
        fund_reasons.append(f"प्रीमियम वैल्यूएशन: P/E {pe:.1f} (महंगा स्टॉक)।")
    else:
        fund_reasons.append("वैल्यूएशन डेटा सीमित या नकारात्मक आय।")

    total_score = round(tech_score + fund_score, 1)

    # FINAL VERDICT
    if total_score >= 7.5:
        verdict = "STRONG BUY (मजबूत खरीदारी)"
        verdict_color = "#00c853"
        action = "टेक्निकल ब्रेकआउट और मजबूत फंडामेंटल का संगम। स्टॉप-लॉस के साथ फ्रेश एंट्री बनाई जा सकती है।"
    elif total_score >= 6.0:
        verdict = "BUY / ACCUMULATE (संभलकर खरीदें)"
        verdict_color = "#64dd17"
        action = "डिप्स (गिरावट) पर धीरे-धीरे एक्युमुलेट करें। ट्रेंड सकारात्मक है।"
    elif total_score >= 4.0:
        verdict = "HOLD / NEUTRAL (बने रहें / वेट करें)"
        verdict_color = "#ffd600"
        action = "नई खरीदारी करने से बचें। पुराने निवेशक ट्रेलिंग स्टॉप-लॉस के साथ होल्ड कर सकते हैं।"
    else:
        verdict = "SELL / AVOID (बिक्री / दूरी बनाएं)"
        verdict_color = "#d50000"
        action = "तकनीकी कमजोरी या खराब वित्तीय आंकड़े। मुनाफावसूली करें या नए पैसे लगाने से बचें।"

    # Target & Stop Loss Calculation (Swing Trading Benchmark)
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
symbol_input = st.sidebar.text_input("स्टॉक सिंबल दर्ज करें", value="TCS.NS")
st.sidebar.caption("💡 भारतीय स्टॉक्स के लिए .NS या .BO लगाएं (उदा. RELIANCE.NS, INFY.NS, HDFCBANK.NS)। US स्टॉक्स के लिए TSLA, NVDA।")

time_period = st.sidebar.selectbox("टाइमफ्रेम (Timeframe)", ["6mo", "1y", "2y", "5y"], index=1)

# ----------------- MAIN EXECUTION -----------------
st.title("📈 AI Stock Fundamental & Technical Advisor")

if symbol_input:
    with st.spinner(f"{symbol_input} का डेटा लोड और एनालिसिस हो रहा है..."):
        try:
            ticker = yf.Ticker(symbol_input.strip().upper())
            df = ticker.history(period=time_period)

            if df.empty or len(df) < 50:
                st.error("इस सिंबल का डेटा प्राप्त नहीं हुआ। कृपया सही सिंबल चेक करें।")
                st.stop()

            df = calculate_indicators(df)
            info = ticker.info
            analysis = analyze_stock(info, df)

            # TOP SUMMARY BAR
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("करंट मार्केट प्राइस", f"₹{analysis['curr_price']:,.2f}")
            c2.metric("कुल स्कोर", f"{analysis['score']} / 10")
            c3.metric("सुझाया गया स्टॉप-लॉस", f"₹{analysis['stop_loss']:,.2f}")
            c4.metric("अनुमानित टारगेट", f"₹{analysis['target']:,.2f}")

            # DECISION BANNER
            st.markdown(f"""
                <div style="background-color: {analysis['verdict_color']}20; border: 2px solid {analysis['verdict_color']}; padding: 18px; border-radius: 8px; margin: 15px 0;">
                    <h2 style="color: {analysis['verdict_color']}; margin: 0;">निर्णय: {analysis['verdict']}</h2>
                    <p style="font-size: 16px; margin-top: 8px; color: #ffffff;">{analysis['action']}</p>
                </div>
            """, unsafe_allow_html=True)

            # TABS FOR DEEP ANALYSIS
            tab_chart, tab_tech, tab_fund = st.tabs(["📊 इंटरैक्टिव कैंडलस्टिक चार्ट", "⚡ टेक्निकल एनालिसिस", "🏢 फंडामेंटल रेश्यो"])

            # TAB 1: CHART
            with tab_chart:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
                
                # Candlesticks
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                    name='Price'
                ), row=1, col=1)

                # EMAs
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name='20 EMA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='orange', width=1.2), name='50 EMA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='cyan', width=1.5), name='200 EMA'), row=1, col=1)

                # Volume Bar
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
                    st.subheader(f"टेक्निकल स्कोर: {analysis['tech_score']} / 5")
                    for reason in analysis['tech_reasons']:
                        st.write(f"• {reason}")
                with col_t2:
                    st.write("**प्रमुख लेवल्स (Support & Resistance):**")
                    st.write(f"• **20-डे सपोर्ट:** ₹{analysis['support']:,.2f}")
                    st.write(f"• **20-डे रेजिस्टेंस:** ₹{analysis['resistance']:,.2f}")
                    st.write(f"• **14-पीरियड RSI:** {analysis['rsi']:.2f}")

            # TAB 3: FUNDAMENTALS
            with tab_fund:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.subheader(f"फंडामेंटल स्कोर: {analysis['fund_score']} / 5")
                    for reason in analysis['fund_reasons']:
                        st.write(f"• {reason}")
                with col_f2:
                    st.write("**वित्तीय आंकड़े (Financial Snapshot):**")
                    st.write(f"• **मार्केट कैप:** ₹{info.get('marketCap', 0):,}")
                    st.write(f"• **P/E Ratio:** {info.get('trailingPE', 'N/A')}")
                    st.write(f"• **Book Value:** ₹{info.get('bookValue', 'N/A')}")
                    st.write(f"• **52-वीक हाई:** ₹{info.get('fiftyTwoWeekHigh', 'N/A')}")
                    st.write(f"• **52-वीक लो:** ₹{info.get('fiftyTwoWeekLow', 'N/A')}")

        except Exception as e:
            st.error(f"विश्लेषण के दौरान त्रुटि आई: {str(e)}")