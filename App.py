import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Terminal Pro", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    [data-testid="stVerticalBlock"] { gap: 0.5rem; }
    .stTextInput > div > div > input { background-color: #111; color: #00ff88; border: 1px solid #333; }
    .side-card {
        background: #111; padding: 12px; border-radius: 10px; border: 1px solid #222; margin-bottom: 15px;
    }
    .ratio-grid { display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.8rem; color: #aaa; }
    .buy { color: #00ff88; font-weight: bold; }
    .sell { color: #ff4b4b; font-weight: bold; }
    .val-highlight { color: #ffffff; font-weight: bold; }
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

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 3.5])

valid_tickers = []
with col_left:
    st.subheader("📁 Portfolio")
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker/Name")
        if name:
            ticker = get_ticker(name)
            if ticker: valid_tickers.append(ticker)
    
    if valid_tickers:
        st.markdown("---")
        st.subheader("📊 Fundamental Data")
        for t in valid_tickers:
            try:
                info = yf.Ticker(t).info
                pe = info.get('forwardPE', 'N/A')
                de = info.get('debtToEquity', 'N/A')
                
                # Render Side Card with Ratios and Insider Mock
                st.markdown(f"""
                <div class="side-card">
                    <div style="font-weight:bold; color:#00ff88; border-bottom:1px solid #333; padding-bottom:4px;">{t}</div>
                    <div class="ratio-grid">
                        <span>P/E: <span class="val-highlight">{f"{pe:.2f}" if isinstance(pe, (int, float)) else pe}</span></span>
                        <span>D/E: <span class="val-highlight">{f"{de:.2f}" if isinstance(de, (int, float)) else de}</span></span>
                    </div>
                    <div style="margin-top:10px; font-size:0.75rem;">
                        Insider: <span class="buy">BUY</span> (Last 30d)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except:
                st.write(f"Data unavailable for {t}")

with col_right:
    # Header & Timeline
    head_left, head_right = st.columns([2, 1])
    with head_left:
        st.title("Performance Intelligence")
    with head_right:
        period = st.select_slider("Timeline", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")

    if valid_tickers:
        # Fetch Data - fetching extra to calculate MAs properly
        raw_data = yf.download(valid_tickers + ["^GSPC"], period="max")['Close']
        if isinstance(raw_data, pd.Series): raw_data = raw_data.to_frame(name=valid_tickers[0])
        
        chart_data = raw_data.last(period).ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- CHARTING ---
        fig = go.Figure()
        
        # Benchmarks & Assets
        for col in norm_data.columns:
            if col == "^GSPC":
                fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name="S&P 500", line=dict(dash='dash', color='#555')))
            else:
                fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col))
        
        # Moving Averages (Primary Asset Only)
        primary = valid_tickers[0]
        if primary in raw_data.columns:
            ma50 = raw_data[primary].rolling(50).mean().last(period)
            ma200 = raw_data[primary].rolling(200).mean().last(period)
            # Normalize MAs to match the scaled chart
            fig.add_trace(go.Scatter(x=ma50.index, y=(ma50/chart_data[primary].iloc[0])*100, name="MA50", line=dict(width=1, color='cyan')))
            fig.add_trace(go.Scatter(x=ma200.index, y=(ma200/chart_data[primary].iloc[0])*100, name="MA200", line=dict(width=1, color='orange')))

        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

        # --- SNAPSHOT METRICS ---
        st.subheader("Asset Momentum")
        m_cols = st.columns(len(valid_tickers))
        for i, t in enumerate(valid_tickers):
            ret = ((chart_data[t].iloc[-1] / chart_data[t].iloc[0]) - 1) * 100
            m_cols[i].metric(t, f"${chart_data[t].iloc[-1]:.2f}", f"{ret:.1f}%")
    else:
        st.info("👈 Add assets in the sidebar to visualize performance.")
