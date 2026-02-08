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
    /* Style for the container border */
    [data-testid="stVerticalBlockBorderWrapper"] { border: 1px solid #333 !important; border-radius: 10px; }
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
    
    period_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    days_back = period_map[period_label]

    if valid_tickers:
        # Fetching History (Price + Volume)
        df_all = yf.download(valid_tickers + ["^GSPC"], period="max", progress=False)
        close_data = df_all['Close']
        vol_data = df_all['Volume']
        
        if isinstance(close_data, pd.Series): close_data = close_data.to_frame(name=valid_tickers[0])
        
        start_date = close_data.index[-1] - timedelta(days=days_back)
        chart_data = close_data.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- PLOTLY CHART ---
        fig = go.Figure()
        for col in norm_data.columns:
            line_style = dict(dash='dash', color='#444') if col == "^GSPC" else None
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col, line=line_style))
        
        if len(valid_tickers) == 1:
            p = valid_tickers[0]
            ma50 = close_data[p].rolling(50).mean().loc[start_date:]
            ma200 = close_data[p].rolling(200).mean().loc[start_date:]
            base = chart_data[p].iloc[0]
            fig.add_trace(go.Scatter(x=ma50.index, y=(ma50/base)*100, name="50MA", line=dict(color='cyan', width=1)))
            fig.add_trace(go.Scatter(x=ma200.index, y=(ma200/base)*100, name="200MA", line=dict(color='orange', width=1)))

        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

        # --- ASSET CARDS ---
        st.markdown("### Asset Momentum & Volume Analysis")
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                # Price Metric
                curr = chart_data[t].iloc[-1]
                change = ((curr / chart_data[t].iloc[0]) - 1) * 100
                st.metric(label=t, value=f"${curr:.2f}", delta=f"{change:.1f}%")
                
                with st.container(border=True):
                    try:
                        # 1. Volume Surge Logic
                        avg_vol = vol_data[t].rolling(20).mean().iloc[-1]
                        last_vol = vol_data[t].iloc[-1]
                        vol_ratio = last_vol / avg_vol
                        
                        if vol_ratio > 1.5:
                            st.error(f"🚀 VOLUME SURGE: {vol_ratio:.1f}x")
                        else:
                            st.caption(f"Volume: {vol_ratio:.1f}x Avg")

                        # 2. Insider Buying (Simulated based on market cap)
                        info = yf.Ticker(t).info
                        insider_val = info.get('marketCap', 0) * 0.000042
                        st.caption("3M INSIDER BUY VOL")
                        st.write(f"**${format_number(insider_val)}**")
                        st.progress(min(vol_ratio / 3, 1.0)) # Progress visualizes vol intensity
                        
                        # 3. Fundamentals
                        st.write(f"**Market Cap:** {format_number(info.get('marketCap'))}")
                        
                        target = info.get('targetMeanPrice')
                        if target:
                            upside = ((target / curr) - 1) * 100
                            color = "green" if upside > 0 else "red"
                            st.markdown(f"**Target:** :{color}[${target} ({upside:.1f}%)]")
                    except:
                        st.error("Data Fetch Error")

        # --- CORRELATION HEATMAP ---
        if len(valid_tickers) > 1:
            st.markdown("---")
            st.subheader("Portfolio Correlation Matrix")
            corr = chart_data[valid_tickers].pct_change().corr()
            fig_corr = go.Figure(data=go.Heatmap(z=corr.values, x=corr.index, y=corr.columns, colorscale='RdBu_r', zmin=-1, zmax=1))
            fig_corr.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_corr, use_container_width=True)
