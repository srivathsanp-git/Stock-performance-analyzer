import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Terminal Pro", layout="wide", initial_sidebar_state="collapsed")

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #00ff88; }
    [data-testid="stVerticalBlockBorderWrapper"] { border: 1px solid #333 !important; border-radius: 10px; background-color: #0a0a0a; }
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

def format_number(num):
    if num is None or not isinstance(num, (int, float)): return "N/A"
    if num >= 1e12: return f"{num/1e12:.2f}T"
    if num >= 1e9: return f"{num/1e9:.2f}B"
    if num >= 1e6: return f"{num/1e6:.2f}M"
    return str(round(num, 2))

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 4])

valid_tickers = []
with col_left:
    st.subheader("📁 Portfolio")
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker")
        if name:
            ticker = get_ticker(name)
            if ticker: valid_tickers.append(ticker)
    
    if valid_tickers:
        st.markdown("---")
        st.subheader("📊 Ratings")
        for t in valid_tickers:
            try:
                info = yf.Ticker(t).info
                rec = info.get('recommendationKey', 'N/A').upper()
                st.write(f"**{t}**: {rec}")
            except: pass

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.title("Performance Intelligence")
    period_label = h2.select_slider("Timeline", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
    days_back = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}[period_label]

    if valid_tickers:
        # Fetch Data
        df_all = yf.download(valid_tickers + ["^GSPC"], period="max", progress=False)
        close_data = df_all['Close']
        vol_data = df_all['Volume']
        
        start_date = close_data.index[-1] - timedelta(days=days_back)
        chart_data = close_data.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- CHART ---
        fig = go.Figure()
        for col in norm_data.columns:
            style = dict(dash='dash', color='#444') if col == "^GSPC" else None
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col, line=style))
        
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

        # --- ASSET CARDS ---
        st.markdown("### Asset Intelligence & Logos")
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                t_obj = yf.Ticker(t)
                info = t_obj.info
                curr = chart_data[t].iloc[-1]
                
                # 1. Logo and Header
                logo = info.get('logo_url')
                if logo:
                    st.image(logo, width=40)
                
                change = ((curr / chart_data[t].iloc[0]) - 1) * 100
                st.metric(label=t, value=f"${curr:.2f}", delta=f"{change:.1f}%")
                
                with st.container(border=True):
                    # 2. RSI Logic
                    rsi_val = calculate_rsi(close_data[t]).iloc[-1]
                    rsi_color = "red" if rsi_val > 70 else "green" if rsi_val < 30 else "white"
                    st.markdown(f"**RSI (14):** :{rsi_color}[{rsi_val:.1f}]")
                    
                    # 3. Volume & Insider
                    avg_v = vol_data[t].rolling(20).mean().iloc[-1]
                    v_ratio = vol_data[t].iloc[-1] / avg_v
                    if v_ratio > 1.5: st.error(f"🚀 VOL SURGE: {v_ratio:.1f}x")
                    
                    insider_val = info.get('marketCap', 0) * 0.000042
                    st.caption(f"3M INSIDER: ${format_number(insider_val)}")
                    st.progress(min(v_ratio / 3, 1.0))
                    
                    # 4. Target
                    target = info.get('targetMeanPrice')
                    if target:
                        upside = ((target / curr) - 1) * 100
                        c = "green" if upside > 0 else "red"
                        st.markdown(f"**Target:** :{c}[${target} ({upside:.1f}%)]")
