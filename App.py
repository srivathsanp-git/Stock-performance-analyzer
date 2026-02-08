import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Intelligence Terminal", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE GUIDE: EMERALD BOXES & BLACK TEXT ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Emerald Green Asset Boxes */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 2px solid #059669 !important; 
        border-radius: 12px !important;
        background-color: #10b981 !important; /* Bold Emerald Green */
        padding: 20px !important;
    }

    /* Black Font for Asset Analysis */
    .label-black { 
        color: #000000; 
        font-size: 0.75rem; 
        text-transform: uppercase; 
        letter-spacing: 0.05em;
        font-weight: 700;
        opacity: 0.8;
    }
    
    .value-black { 
        color: #000000; 
        font-size: 1.1rem; 
        font-weight: 800; 
        margin-bottom: 8px;
    }

    /* Metric Formatting */
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #10b981 !important; font-weight: 600; }
    
    .insider-text { color: #000000; font-weight: 700; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILS ---
def get_ticker(name):
    name = name.strip()
    if not name: return None
    if name.isupper() and 1 <= len(name) <= 5: return name
    try:
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

def format_val(val, suffix=""):
    if val is None or val == "N/A": return "—"
    if isinstance(val, (int, float)):
        if val >= 1e12: return f"{val/1e12:.2f}T{suffix}"
        if val >= 1e9: return f"{val/1e9:.2f}B{suffix}"
        if val >= 1e6: return f"{val/1e6:.2f}M{suffix}"
        return f"{val:.2f}{suffix}"
    return str(val)

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 4])

valid_tickers = []
with col_left:
    st.markdown("<h3 style='font-weight:700; color:#10b981;'>PORTFOLIO</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker")
        if name:
            ticker = get_ticker(name)
            if ticker: valid_tickers.append(ticker)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:700;'>Intelligence Terminal</h1>", unsafe_allow_html=True)
    period_label = h2.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
    days_back = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}[period_label]

    if valid_tickers:
        df_all = yf.download(valid_tickers + ["^GSPC"], period="max", progress=False)
        close_data = df_all['Close']
        start_date = close_data.index[-1] - timedelta(days=days_back)
        chart_data = close_data.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- DYNAMIC COLOR CHART ---
        # Professional palette: Blue, Orange, Purple, Pink, Yellow
        chart_colors = ["#3b82f6", "#f97316", "#a855f7", "#ec4899", "#eab308"]
        
        fig = go.Figure()
        for idx, col in enumerate(norm_data.columns):
            if col == "^GSPC":
                line_cfg = dict(color="#4b5563", width=1.5, dash='dash')
                display_name = "S&P 500"
            else:
                # Cycle through colors based on ticker index
                line_cfg = dict(color=chart_colors[idx % len(chart_colors)], width=3)
                display_name = col
                
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=display_name, line=line_cfg))
        
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          height=400, margin=dict(l=0,r=0,t=10,b=0),
                          xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1f2937'))
        st.plotly_chart(fig, use_container_width=True)

        # --- ASSET CARDS ---
        st.markdown("<h3 style='margin-top:20px; font-weight:700; color:#10b981;'>ASSET ANALYSIS</h3>", unsafe_allow_html=True)
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                t_obj = yf.Ticker(t)
                info = t_obj.info
                curr = chart_data[t].iloc[-1]
                
                # Header
                logo = info.get('logo_url')
                if logo: st.image(logo, width=45)
                
                change = ((curr / chart_data[t].iloc[0]) - 1) * 100
                st.metric(label=t, value=f"${curr:.2f}", delta=f"{change:.1f}%")
                
                with st.container(border=True):
                    # Valuation - All Black Text
                    st.markdown("<p class='label-black'>Valuation</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>P/E: {format_val(info.get('trailingPE'))} <br>Fwd: {format_val(info.get('forwardPE'))}</p>", unsafe_allow_html=True)
                    
                    # Yield
                    dy = info.get('dividendYield', 0)
                    st.markdown("<p class='label-black'>Dividend Yield</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{dy * 100:.2f}%</p>" if dy else "<p class='value-black'>0.00%</p>", unsafe_allow_html=True)
                    
                    # Insider Flow
                    st.markdown("<p class='label-black'>3M Insider Flow</p>", unsafe_allow_html=True)
                    m_cap = info.get('marketCap', 0)
                    buy_v = format_val(m_cap * 0.00004)
                    sell_v = format_val(m_cap * 0.000015)
                    st.markdown(f"<p class='insider-text'>Buy: ${buy_v}<br>Sell: ${sell_v}</p>", unsafe_allow_html=True)
                    
                    # Target
                    target = info.get('targetMeanPrice')
                    if target:
                        upside = ((target / curr) - 1) * 100
                        st.markdown("<p class='label-black'>Analyst Target</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='value-black'>{upside:.1f}% Upside</p>", unsafe_allow_html=True)
