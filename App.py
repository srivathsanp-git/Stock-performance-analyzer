import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Intelligence Terminal", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE GUIDE: EMERALD BOXES & HIGH-CONTRAST BLACK TEXT ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Emerald Container Styling */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 2px solid #059669 !important; 
        border-radius: 14px !important;
        background-color: #10b981 !important; 
        padding: 24px !important;
    }

    .ticker-header { 
        font-size: 2.4rem; 
        font-weight: 800; 
        color: #000000; 
        line-height: 1.0;
        margin-bottom: 2px;
    }
    .price-sub { 
        font-size: 1.4rem; 
        font-weight: 700; 
        color: #000000; 
        margin-bottom: 12px;
        border-bottom: 2px solid rgba(0,0,0,0.1);
        padding-bottom: 8px;
    }

    .label-black { 
        color: #000000; 
        font-size: 0.75rem; 
        text-transform: uppercase; 
        letter-spacing: 0.05em;
        font-weight: 800;
        margin-top: 12px;
        opacity: 0.9;
    }
    
    .value-black { 
        color: #000000; 
        font-size: 1.05rem; 
        font-weight: 600; 
        margin-bottom: 2px;
    }

    [data-testid="stMetric"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- CACHED UTILS ---

@st.cache_data(ttl=3600)
def get_ticker_symbol(name):
    """Resolves names to tickers and caches results to prevent rate limits."""
    name = name.strip()
    if not name: return None
    if name.isupper() and 1 <= len(name) <= 5: return name
    try:
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

@st.cache_data(ttl=3600)
def get_asset_info(ticker):
    """Fetches fundamental data with error handling for rate limits."""
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}

@st.cache_data(ttl=600)
def download_data(tickers, period="max"):
    """Downloads price data in one batch."""
    return yf.download(tickers, period=period, progress=False)['Close']

def format_val(val, suffix=""):
    if val is None or val == "N/A" or val == 0: return "—"
    if isinstance(val, (int, float)):
        if val >= 1e12: return f"{val/1e12:.2f}T{suffix}"
        if val >= 1e9: return f"{val/1e9:.2f}B{suffix}"
        if val >= 1e6: return f"{val/1e6:.2f}M{suffix}"
        return f"{val:.2f}{suffix}"
    return str(val)

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 4.2])

valid_tickers = []
with col_left:
    st.markdown("<h3 style='font-weight:700; color:#10b981;'>PORTFOLIO</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker or Name")
        if name:
            ticker = get_ticker_symbol(name)
            if ticker: valid_tickers.append(ticker)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:700;'>Intelligence Terminal</h1>", unsafe_allow_html=True)
    period_label = h2.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
    days_back = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}[period_label]

    if valid_tickers:
        # Data Pull
        all_symbols = list(set(valid_tickers + ["^GSPC"]))
        df_all = download_data(all_symbols)
        
        start_date = df_all.index[-1] - timedelta(days=days_back)
        chart_data = df_all.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- DYNAMIC COLOR CHART ---
        chart_colors = ["#3b82f6", "#f97316", "#a855f7", "#ec4899", "#eab308"]
        fig = go.Figure()
        
        for idx, col in enumerate(norm_data.columns):
            if col == "^GSPC":
                line_cfg = dict(color="#4b5563", width=1.5, dash='dash')
                label = "S&P 500"
            else:
                line_cfg = dict(color=chart_colors[idx % len(chart_colors)], width=3)
                label = col
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=label, line=line_cfg))
        
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          height=380, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(showgrid=False),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # --- ASSET CARDS ---
        st.markdown("<h3 style='margin-top:20px; font-weight:700; color:#10b981;'>ASSET ANALYSIS</h3>", unsafe_allow_html=True)
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                info = get_asset_info(t)
                
                # Logic to handle Series vs DataFrame indexing
                if isinstance(chart_data, pd.DataFrame) and t in chart_data.columns:
                    curr = chart_data[t].iloc[-1]
                else:
                    curr = chart_data.iloc[-1]
                
                st.markdown(f"<p class='ticker-header'>{t}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='price-sub'>${curr:.2f}</p>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    # Valuation
                    st.markdown("<p class='label-black'>Valuation</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>P/E: {format_val(info.get('trailingPE'))} | Fwd: {format_val(info.get('forwardPE'))}</p>", unsafe_allow_html=True)
                    
                    # Dividend Yield
                    raw_div = info.get('dividendYield', 0) or 0
                    div_val = raw_div if raw_div < 0.2 else raw_div / 100
                    st.markdown("<p class='label-black'>Dividend Yield</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{div_val * 100:.2f}%</p>", unsafe_allow_html=True)
                    
                    # Analyst Target
                    target = info.get('targetMeanPrice')
                    st.markdown("<p class='label-black'>Price Target</p>", unsafe_allow_html=True)
                    if target:
                        upside = ((target / curr) - 1) * 100
                        st.markdown(f"<p class='value-black'>${target} ({upside:.1f}%)</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p class='value-black'>—</p>", unsafe_allow_html=True)
    else:
        st.info("👈 Enter stock tickers or names in the sidebar to begin.")
