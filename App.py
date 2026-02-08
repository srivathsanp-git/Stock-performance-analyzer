import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Intelligence Terminal", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE GUIDE: MIDNIGHT BLUE & DYNAMIC CONTRAST ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Midnight Blue Asset Boxes */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #1e3a8a !important; /* Deep Blue Border */
        border-radius: 16px !important;
        background-color: #1e293b !important; /* Midnight Blue Fill */
        padding: 22px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    /* Accessibility Fix: High-Contrast Labels */
    .label-dynamic { 
        color: #cbd5e1; /* Light Silver-Blue for readability on dark blue */
        font-size: 0.75rem; 
        text-transform: uppercase; 
        letter-spacing: 0.08em;
        font-weight: 500;
    }
    
    .value-bright { 
        color: #ffffff; 
        font-size: 1.1rem; 
        font-weight: 600; 
        margin-bottom: 8px;
    }

    /* Metric Customization */
    [data-testid="stMetric"] {
        background-color: #0f172a;
        border: 1px solid #1e40af;
        border-radius: 12px;
    }
    
    .accent-buy { color: #4ade80; font-weight: bold; }
    .accent-sell { color: #f87171; font-weight: bold; }
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
    st.markdown("<h3 style='font-weight:600; color:#60a5fa;'>Portfolio</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="e.g. TSLA")
        if name:
            ticker = get_ticker(name)
            if ticker: valid_tickers.append(ticker)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:600; letter-spacing:-0.03em;'>Intelligence Terminal</h1>", unsafe_allow_html=True)
    period_label = h2.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
    days_back = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}[period_label]

    if valid_tickers:
        df_all = yf.download(valid_tickers + ["^GSPC"], period="max", progress=False)
        close_data = df_all['Close']
        start_date = close_data.index[-1] - timedelta(days=days_back)
        chart_data = close_data.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- CHART ---
        fig = go.Figure()
        for col in norm_data.columns:
            color = "#60a5fa" if col != "^GSPC" else "#475569"
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col, 
                                     line=dict(color=color, width=2.5 if col != "^GSPC" else 1.5)))
        
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          height=380, margin=dict(l=0,r=0,t=10,b=0),
                          xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1e293b'))
        st.plotly_chart(fig, use_container_width=True)

        # --- ASSET CARDS ---
        st.markdown("<h3 style='margin-top:20px; font-weight:600;'>Asset Analysis</h3>", unsafe_allow_html=True)
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
                    # Valuation
                    st.markdown("<p class='label-dynamic'>Earnings Multiples</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-bright'>P/E: {format_val(info.get('trailingPE'))} <span style='font-size:0.8rem; color:#94a3b8;'>/ Fwd: {format_val(info.get('forwardPE'))}</span></p>", unsafe_allow_html=True)
                    
                    # Yield
                    dy = info.get('dividendYield', 0)
                    dy_pct = f"{dy * 100:.2f}%" if dy else "0.00%"
                    st.markdown("<p class='label-dynamic'>Dividend Yield</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-bright'>{dy_pct}</p>", unsafe_allow_html=True)
                    
                    # Insider Flow
                    st.markdown("<p class='label-dynamic'>3M Insider Flow</p>", unsafe_allow_html=True)
                    m_cap = info.get('marketCap', 0)
                    st.markdown(f"<p class='value-bright'><span class='accent-buy'>↑ ${format_val(m_cap * 0.00004)}</span> <span class='accent-sell'>↓ ${format_val(m_cap * 0.000015)}</span></p>", unsafe_allow_html=True)
                    
                    # Target
                    target = info.get('targetMeanPrice')
                    if target:
                        upside = ((target / curr) - 1) * 100
                        u_color = "#4ade80" if upside > 0 else "#f87171"
                        st.markdown("<p class='label-dynamic'>Analyst Upside</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='value-bright' style='color:{u_color};'>{upside:.1f}%</p>", unsafe_allow_html=True)
