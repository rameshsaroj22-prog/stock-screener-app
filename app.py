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
    page_title="Kotak Neo Terminal | AI Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- KOTAK NEO PROFESSIONAL FINTECH CSS -----------------
st.markdown("""
    <style>
    /* Global Background */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top Index Bar */
    .index-ribbon {
        display: flex;
        gap: 15px;
        background: #161b22;
        border-bottom: 1px solid #30363d;
        padding: 10px 18px;
        margin-top: -30px;
        margin-bottom: 15px;
        border-radius: 6px;
    }
    .index-pill {
        background: #21262d;
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 0.85rem;
        display: flex;
        gap: 8px;
        align-items: center;
        border: 1px solid #30363d;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    
    /* Neo Company Header */
    .neo-header {
        background: linear-gradient(90deg, #161b22 0%, #1f2937 100%);
        border: 1px solid #30363d;
        border-left: 5px solid #00b0ff;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 18px;
    }
    
    /* Stat Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
        font-size: 0.8rem !important;
        font-weight: 500;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f0f6fc !important;
        font-size: 1.35rem !important;
        font-weight: 700;
    }

    /* Trade Pad / Order Box */
    .trade-pad {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 18px;
        margin-top: 10px;
    }
    
    /* Neo Badges */
    .badge-buy {
        background-color: rgba(0, 200, 83, 0.15);
        color: #00c853;
        border: 1px solid #00c853;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-sell {
        background-color: rgba(255, 61, 0, 0.15);
        color: #ff3d00;
        border: 1px solid #ff3d00;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </
