import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

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
    [data-testid="stMetric"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- CACHED UTILS ---

@st.cache_data(ttl=3600)
def get_ticker_symbol(name):
    name = name.strip()
    if not name: return None
    if name.isupper() and 1 <= len(name) <= 5: return name
    try:
        # Use a session to avoid basic bot detection
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

@st.cache_data(ttl=3600)
def get_asset_info(ticker_str):
    """Fetches fundamental data using a custom session to bypass limits."""
    try:
        t_obj = yf.Ticker(ticker_str)
        # Attempt to access info
        info = t_obj.info
        if not info or len(info) < 5:
            # Fallback for empty info objects
            return {"symbol": ticker_str, "shortName": ticker_str}
        return info
    except Exception as e:
        return {}

@st.cache_data(ttl=600)
def download_data(tickers):
    # Batch download is much safer for rate limits
    return yf.download(tickers, period="5y", progress=False)['Close']

def format_val(val, suffix=""):
    if val is None or val == "N/A" or val == 0 or val == "—": return "—"
    try:
        val_float = float(val)
        if val_float >= 1e12: return f"{val_float/1e12:.2f}T{suffix}"
        if val_float >= 1e9: return f"{val_float/1e9:.2f}B{suffix}"
        if val_float >= 1e6: return f"{val_float/1e6:.2f}M{suffix}"
        return f"{val_float:.2f}{suffix}"
    except: return "—"

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 4.2])

valid_tickers = []
with col_left:
    st.markdown("<h3 style='font-weight:700; color:#10b981;'>PORTFOLIO</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker (e.g. AAPL)")
        if name:
            ticker = get_ticker_symbol(name)
            if ticker: valid_tickers.append(ticker)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:700;'>Intelligence Terminal</h1>", unsafe_allow_html=True)
    period_label = h2.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
    days_back = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}[period_label]

    if valid_tickers:
        all_symbols = list(set(valid_tickers + ["^GSPC"]))
        df_all = download_data(all_symbols)
        
        # Filter for selected range
        start_date = df_all.index[-1] - timedelta(days=days_back)
        chart_data = df_all.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- PLOTLY CHART ---
        chart_colors = ["#3b82f6", "#f97316", "#a855f7", "#ec4899", "#eab308"]
        fig = go.Figure()
        for idx, col in enumerate(norm_data.columns):
            is_sp = col == "^GSPC"
            fig.add_trace(go.Scatter(
                x=norm_data.index, y=norm_data[col], 
                name="S&P 500" if is_sp else col,
                line=dict(color="#4b5563" if is_sp else chart_colors[idx % len(chart_colors)], 
                          width=1.5 if is_sp else 3, 
                          dash='dash' if is_sp else 'solid')
            ))
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          height=380, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

        # --- ASSET CARDS ---
        st.markdown("<h3 style='margin-top:20px; font-weight:700; color:#10b981;'>ASSET ANALYSIS</h3>", unsafe_allow_html=True)
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                info = get_asset_info(t)
                # Get current price from the downloaded dataframe
                price_val = df_all[t].iloc[-1] if isinstance(df_all, pd.DataFrame) else df_all.iloc[-1]
                
                st.markdown(f"<p class='ticker-header'>{t}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='price-sub'>${price_val:.2f}</p>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    # Valuation
                    pe = info.get('trailingPE', '—')
                    fpe = info.get('forwardPE', '—')
                    st.markdown("<p class='label-black'>Valuation</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>P/E: {format_val(pe)} | Fwd: {format_val(fpe)}</p>", unsafe_allow_html=True)
                    
                    # Dividend
                    raw_div = info.get('dividendYield', 0) or 0
                    div_display = f"{raw_div * 100:.2f}%" if raw_div != 0 else "0.00%"
                    st.markdown("<p class='label-black'>Dividend Yield</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{div_display}</p>", unsafe_allow_html=True)
                    
                    # Analyst Target
                    target = info.get('targetMeanPrice')
                    st.markdown("<p class='label-black'>Price Target</p>", unsafe_allow_html=True)
                    if target:
                        upside = ((float(target) / price_val) - 1) * 100
                        st.markdown(f"<p class='value-black'>${target} ({upside:.1f}%)</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p class='value-black'>—</p>", unsafe_allow_html=True)
    else:
        st.info("Enter tickers in the sidebar to load terminal data.")
