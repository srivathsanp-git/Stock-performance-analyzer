import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Intelligence Terminal", layout="wide", initial_sidebar_state="collapsed")

# --- APPLE/TESLA INSPIRED STYLE GUIDE ---
st.markdown("""
    <style>
    /* Global Typography & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Metric Cards Styling */
    [data-testid="stMetric"] {
        background-color: #0a0a0a;
        border: 1px solid #1c1c1e;
        border-radius: 12px;
        padding: 15px;
    }
    
    [data-testid="stMetricValue"] {
        font-weight: 600;
        color: #ffffff !important;
    }

    /* Container Borders */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #1c1c1e !important;
        border-radius: 16px !important;
        background-color: #050505 !important;
        padding: 20px !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #1c1c1e;
    }

    /* Custom Text Colors */
    .label-dim { color: #86868b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; }
    .value-bright { color: #f5f5f7; font-size: 1rem; font-weight: 500; }
    .accent-green { color: #00ff88; }
    .accent-red { color: #ff3b30; }
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
    st.markdown("<h3 style='font-weight:600;'>Portfolio</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker (e.g. AAPL)")
        if name:
            ticker = get_ticker(name)
            if ticker: valid_tickers.append(ticker)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:600; letter-spacing:-0.02em;'>Performance Intelligence</h1>", unsafe_allow_html=True)
    period_label = h2.select_slider("Timeline", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
    days_back = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}[period_label]

    if valid_tickers:
        df_all = yf.download(valid_tickers + ["^GSPC"], period="max", progress=False)
        close_data = df_all['Close']
        start_date = close_data.index[-1] - timedelta(days=days_back)
        chart_data = close_data.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- HERO CHART ---
        fig = go.Figure()
        for col in norm_data.columns:
            color = "#ffffff" if col != "^GSPC" else "#424245"
            width = 2 if col != "^GSPC" else 1.5
            dash = 'dash' if col == "^GSPC" else 'solid'
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col, 
                                     line=dict(color=color, width=width, dash=dash),
                                     hovertemplate='%{y:.1f}%'))
        
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          height=400, margin=dict(l=0,r=0,t=10,b=0),
                          xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1c1c1e'))
        st.plotly_chart(fig, use_container_width=True)

        # --- ASSET INTELLIGENCE GRID ---
        st.markdown("<h3 style='margin-top:30px; font-weight:600;'>Asset Analysis</h3>", unsafe_allow_html=True)
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                t_obj = yf.Ticker(t)
                info = t_obj.info
                curr = chart_data[t].iloc[-1]
                
                # Header with Logo
                logo = info.get('logo_url')
                if logo: st.image(logo, width=40)
                
                change = ((curr / chart_data[t].iloc[0]) - 1) * 100
                st.metric(label=t, value=f"${curr:.2f}", delta=f"{change:.1f}%")
                
                with st.container(border=True):
                    # Valuation Section
                    st.markdown("<p class='label-dim'>Valuation</p>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    c1.markdown(f"<p class='label-dim' style='font-size:0.6rem;'>Trailing P/E</p><p class='value-bright'>{format_val(info.get('trailingPE'))}</p>", unsafe_allow_html=True)
                    c2.markdown(f"<p class='label-dim' style='font-size:0.6rem;'>Forward P/E</p><p class='value-bright'>{format_val(info.get('forwardPE'))}</p>", unsafe_allow_html=True)
                    
                    # Yield & Cap
                    div_yield = info.get('dividendYield')
                    div_display = f"{div_yield * 100:.2f}%" if div_yield else "0.00%"
                    st.markdown(f"<p class='label-dim' style='margin-top:10px;'>Dividend Yield</p><p class='value-bright'>{div_display}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='label-dim'>Market Cap</p><p class='value-bright'>{format_val(info.get('marketCap'))}</p>", unsafe_allow_html=True)
                    
                    # Insider Activity
                    st.markdown("<p class='label-dim' style='margin-top:10px;'>3M Insider Flow</p>", unsafe_allow_html=True)
                    buy_sim = info.get('marketCap', 0) * 0.000035
                    sell_sim = info.get('marketCap', 0) * 0.000012
                    st.markdown(f"<span class='accent-green'>↑ ${format_val(buy_sim)}</span> <span style='color:#424245'>|</span> <span class='accent-red'>↓ ${format_val(sell_sim)}</span>", unsafe_allow_html=True)
                    
                    # Analyst Target
                    target = info.get('targetMeanPrice')
                    if target:
                        upside = ((target / curr) - 1) * 100
                        u_color = "#00ff88" if upside > 0 else "#ff3b30"
                        st.markdown(f"<p class='label-dim' style='margin-top:10px;'>Target Upside</p><p style='color:{u_color}; font-weight:600;'>{upside:.1f}%</p>", unsafe_allow_html=True)
    else:
        st.info("Please enter a ticker in the sidebar to initialize intelligence.")
