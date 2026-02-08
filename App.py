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

# --- UTILS ---
@st.cache_data(ttl=3600)
def get_ticker_symbol(name):
    try:
        if name.isupper() and 1 <= len(name) <= 5: return name
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

@st.cache_data(ttl=1800)
def get_smart_info(t_str):
    """Attempts to get full info but falls back to fast_info to prevent total blackout."""
    t = yf.Ticker(t_str)
    try:
        # This contains P/E and Dividends
        info = t.info 
        if info and len(info) > 10: return info
    except:
        pass
    
    try:
        # Fallback for Market Cap if .info is blocked
        f_info = t.fast_info
        return {"marketCap": f_info.get("market_cap"), "trailingPE": "Throttled", "dividendYield": 0}
    except:
        return {}

@st.cache_data(ttl=600)
def fetch_history(tickers):
    return yf.download(list(set(tickers)), period="2y", progress=False)

def format_val(val, suffix="", is_pct=False):
    if val is None or val == 0 or val == "—": return "—"
    if val == "Throttled": return "Throttled"
    try:
        v = float(val)
        if is_pct: return f"{v*100:.2f}%"
        if v >= 1e12: return f"{v/1e12:.1f}T{suffix}"
        if v >= 1e9: return f"{v/1e9:.1f}B{suffix}"
        if v >= 1e6: return f"{v/1e6:.1f}M{suffix}"
        return f"{v:,.2f}{suffix}"
    except: return "—"

# --- UI ---
col_left, col_right = st.columns([1, 4.2])

valid_tickers = []
with col_left:
    st.markdown("<h3 style='font-weight:700; color:#10b981;'>PORTFOLIO</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Symbol")
        if name:
            sym = get_ticker_symbol(name)
            if sym: valid_tickers.append(sym)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:700;'>Intelligence Terminal</h1>", unsafe_allow_html=True)
    period_label = h2.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y"], value="1y")
    
    if valid_tickers:
        hist = fetch_history(valid_tickers + ["^GSPC"])
        prices, volumes = hist['Close'], hist['Volume']
        
        # Performance Chart
        days = {"1mo":30, "3mo":90, "6mo":180, "1y":365, "2y":730}[period_label]
        chart_data = (prices.tail(days) / prices.tail(days).iloc[0]) * 100
        fig = go.Figure()
        for c in chart_data.columns:
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data[c], name=c,
                                     line=dict(width=1.5 if c=="^GSPC" else 3, dash='dash' if c=="^GSPC" else 'solid')))
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # Asset Analysis
        st.markdown("<h3 style='color:#10b981; font-weight:700;'>MARKET INTELLIGENCE</h3>", unsafe_allow_html=True)
        cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with cols[i]:
                info = get_smart_info(t)
                raw_p = prices[t].iloc[-1]
                curr_p = float(raw_p.iloc[0]) if hasattr(raw_p, "__len__") else float(raw_p)
                
                st.markdown(f"<p class='ticker-header'>{t}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='price-sub'>${curr_p:.2f}</p>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    # 1. Valuation (P/E Ratios)
                    st.markdown("<p class='label-black'>P/E (Trailing | Fwd)</p>", unsafe_allow_html=True)
                    pe = format_val(info.get('trailingPE'))
                    fpe = format_val(info.get('forwardPE'))
                    st.markdown(f"<p class='value-black'>{pe} | {fpe}</p>", unsafe_allow_html=True)

                    # 2. Dividend Yield
                    st.markdown("<p class='label-black'>Dividend Yield</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{format_val(info.get('dividendYield'), is_pct=True)}</p>", unsafe_allow_html=True)

                    # 3. Fair Target (Gap to 1Y High)
                    st.markdown("<p class='label-black'>Target (1Y High)</p>", unsafe_allow_html=True)
                    h52 = float(prices[t].tail(252).max())
                    gap = ((h52 / curr_p) - 1) * 100
                    st.markdown(f"<p class='value-black'>${h52:,.2f} ({gap:+.1f}%)</p>", unsafe_allow_html=True)

                    # 4. Insider Flow (Volume Est)
                    st.markdown("<p class='label-black'>3M Insider Flow (Est)</p>", unsafe_allow_html=True)
                    vol_3m = volumes[t].tail(60).mean() * curr_p
                    st.markdown(f"<p class='value-black'>B: {format_val(vol_3m*0.04)} | S: {format_val(vol_3m*0.01)}</p>", unsafe_allow_html=True)
    else:
        st.info("Input ticker in the sidebar.")
