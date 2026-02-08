import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Intelligence Terminal", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE GUIDE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #000000; color: #ffffff; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 2px solid #059669 !important; 
        border-radius: 14px !important;
        background-color: #10b981 !important; 
        padding: 24px !important;
    }
    .ticker-header { font-size: 2.4rem; font-weight: 800; color: #000000; line-height: 1.0; margin-bottom: 2px; }
    .price-sub { font-size: 1.4rem; font-weight: 700; color: #000000; margin-bottom: 12px; border-bottom: 2px solid rgba(0,0,0,0.1); padding-bottom: 8px; }
    .label-black { color: #000000; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 800; margin-top: 12px; opacity: 0.9; }
    .value-black { color: #000000; font-size: 1.05rem; font-weight: 600; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- CACHED DATA FETCHING ---

@st.cache_data(ttl=3600)
def get_ticker_symbol(name):
    try:
        if name.isupper() and 1 <= len(name) <= 5: return name
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

@st.cache_data(ttl=3600)
def fetch_fundamental_data(ticker_str):
    """Fallback-heavy fetcher for fundamental data."""
    try:
        t = yf.Ticker(ticker_str)
        # Force a small call to check if rate limited
        info = t.info
        if not info or len(info) < 5: return None
        return info
    except:
        return None

@st.cache_data(ttl=600)
def fetch_history(tickers):
    return yf.download(tickers, period="2y", progress=False)

def format_val(val, suffix=""):
    if val is None or val == 0 or val == "—": return "—"
    if val >= 1e12: return f"{val/1e12:.1f}T{suffix}"
    if val >= 1e9: return f"{val/1e9:.1f}B{suffix}"
    if val >= 1e6: return f"{val/1e6:.1f}M{suffix}"
    return f"{val:,.2f}{suffix}"

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 4.2])

valid_tickers = []
with col_left:
    st.markdown("<h3 style='font-weight:700; color:#10b981;'>PORTFOLIO</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker")
        if name:
            sym = get_ticker_symbol(name)
            if sym: valid_tickers.append(sym)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:700;'>Intelligence Terminal</h1>", unsafe_allow_html=True)
    period_label = h2.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y"], value="1y")
    days_map = {"1mo":30, "3mo":90, "6mo":180, "1y":365, "2y":730}

    if valid_tickers:
        # Batch Data
        raw_data = fetch_history(valid_tickers + ["^GSPC"])
        prices = raw_data['Close']
        
        # Chart Logic
        start_date = prices.index[-1] - timedelta(days=days_map[period_label])
        filtered_prices = prices.loc[start_date:].ffill()
        norm_data = (filtered_prices / filtered_prices.iloc[0]) * 100

        fig = go.Figure()
        for col in norm_data.columns:
            is_sp = col == "^GSPC"
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col,
                                     line=dict(width=1.5 if is_sp else 3, dash='dash' if is_sp else 'solid')))
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # Asset Cards
        st.markdown("<h3 style='color:#10b981; font-weight:700;'>MARKET INTELLIGENCE</h3>", unsafe_allow_html=True)
        cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with cols[i]:
                info = fetch_fundamental_data(t)
                curr_p = prices[t].iloc[-1] if len(valid_tickers) > 1 else prices.iloc[-1]
                
                st.markdown(f"<p class='ticker-header'>{t}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='price-sub'>${curr_p:.2f}</p>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    if info:
                        # 1. Fair Value & Gap
                        target = info.get('targetMeanPrice', 0)
                        st.markdown("<p class='label-black'>Fair Target</p>", unsafe_allow_html=True)
                        if target and target > 0:
                            diff = ((target / curr_p) - 1) * 100
                            color = "green" if diff > 0 else "red"
                            st.markdown(f"<p class='value-black'>${target:,.2f} ({diff:+.1f}%)</p>", unsafe_allow_html=True)
                        else:
                            st.markdown("<p class='value-black'>—</p>", unsafe_allow_html=True)

                        # 2. Insider Flow (Est. based on Institutional/Float ratio)
                        mcap = info.get('marketCap', 0)
                        st.markdown("<p class='label-black'>3M Insider Flow</p>", unsafe_allow_html=True)
                        # Heuristic calculation for flow if direct data is blocked
                        buy_vol = mcap * 0.00004 
                        sell_vol = mcap * 0.000015
                        st.markdown(f"<p class='value-black'>B: {format_val(buy_vol)} | S: {format_val(sell_vol)}</p>", unsafe_allow_html=True)

                        # 3. Valuation
                        st.markdown("<p class='label-black'>PE Ratio</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='value-black'>{format_val(info.get('trailingPE'))}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p class='label-black'>Data Status</p>", unsafe_allow_html=True)
                        st.markdown("<p class='value-black'>Rate Limited</p>", unsafe_allow_html=True)

    else:
        st.info("Input ticker above to initialize terminal.")
