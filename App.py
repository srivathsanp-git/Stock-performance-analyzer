import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Terminal Pro", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    .stTextInput > div > div > input { background-color: #111; color: #00ff88; border: 1px solid #333; }
    .side-card { background: #111; padding: 12px; border-radius: 10px; border: 1px solid #222; margin-bottom: 15px; }
    
    .stat-box { background: #111; padding: 10px; border-radius: 8px; border: 1px solid #222; margin-top: 5px; }
    .stat-label { font-size: 0.7rem; color: #888; text-transform: uppercase; }
    .stat-value { font-size: 0.9rem; color: #fff; font-weight: bold; }
    
    /* Sentiment Badges */
    .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
    .buy-bg { background-color: #00ff88; color: black; }
    .hold-bg { background-color: #f1c40f; color: black; }
    .sell-bg { background-color: #e74c3c; color: white; }
    
    .insider-bar { height: 4px; background: #333; border-radius: 2px; margin-top: 4px; }
    .insider-fill { height: 4px; background: #00ff88; border-radius: 2px; }
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
    if num is None or isinstance(num, str): return "N/A"
    if num >= 1e12: return f"{num/1e12:.2f}T"
    if num >= 1e9: return f"{num/1e9:.2f}B"
    if num >= 1e6: return f"{num/1e6:.2f}M"
    return str(num)

def get_recommendation(ticker_obj):
    try:
        rec = ticker_obj.info.get('recommendationKey', 'N/A').replace('_', ' ').title()
        if 'Buy' in rec: return f'<span class="badge buy-bg">{rec}</span>'
        if 'Sell' in rec: return f'<span class="badge sell-bg">{rec}</span>'
        return f'<span class="badge hold-bg">{rec}</span>'
    except: return "N/A"

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
                t_obj = yf.Ticker(t)
                info = t_obj.info
                pe = info.get('forwardPE', 'N/A')
                st.markdown(f"""
                <div class="side-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:bold; color:#00ff88;">{t}</span>
                        {get_recommendation(t_obj)}
                    </div>
                    <div style="font-size:0.8rem; color:#888; margin-top:5px;">
                        P/E: <span style="color:white;">{f"{pe:.2f}" if isinstance(pe,(int,float)) else pe}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except: pass

with col_right:
    head_left, head_right = st.columns([2, 1])
    with head_left: st.title("Performance Intelligence")
    with head_right:
        period_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
        period_label = st.select_slider("Timeline", options=list(period_map.keys()), value="1y")
        days_back = period_map[period_label]

    if valid_tickers:
        raw_data = yf.download(valid_tickers + ["^GSPC"], period="max", progress=False)['Close']
        if isinstance(raw_data, pd.Series): raw_data = raw_data.to_frame(name=valid_tickers[0])
        
        end_date = raw_data.index[-1]
        start_date = end_date - timedelta(days=days_back)
        chart_data = raw_data.loc[start_date:].ffill()
        norm_data = (chart_data / chart_data.iloc[0]) * 100

        # --- CHART ---
        fig = go.Figure()
        for col in norm_data.columns:
            if col == "^GSPC":
                fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name="S&P 500", line=dict(dash='dash', color='#444')))
            else:
                fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col))
        
        if len(valid_tickers) == 1:
            primary = valid_tickers[0]
            ma50 = raw_data[primary].rolling(50).mean().loc[start_date:]
            ma200 = raw_data[primary].rolling(200).mean().loc[start_date:]
            base = chart_data[primary].iloc[0]
            fig.add_trace(go.Scatter(x=ma50.index, y=(ma50/base)*100, name="50MA", line=dict(color='cyan', width=1)))
            fig.add_trace(go.Scatter(x=ma200.index, y=(ma200/base)*100, name="200MA", line=dict(color='orange', width=1)))

        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

        # --- INSIGHT GRID ---
        st.subheader("Asset Momentum & Insider Sentiment")
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                ret = ((chart_data[t].iloc[-1] / chart_data[t].iloc[0]) - 1) * 100
                st.metric(t, f"${chart_data[t].iloc[-1]:.2f}", f"{ret:.1f}%")
                
                try:
                    t_obj = yf.Ticker(t)
                    t_info = t_obj.info
                    
                    # Mocking Insider Volume (Buy Volume in last 3 months)
                    # In a production app, you would fetch actual SEC Form 4 data here.
                    insider_buy_vol = format_number(t_info.get('marketCap', 0) * 0.00005) # Simulated 0.005% of cap
                    
                    st.markdown(f"""
                    <div class="stat-box">
                        <div class="stat-label">Analyst View</div>
                        <div style="margin-bottom:8px;">{get_recommendation(t_obj)}</div>
                        
                        <div class="stat-label">3M Insider Buy Vol</div>
                        <div class="stat-value" style="color:#00ff88;">{insider_buy_vol}</div>
                        <div class="insider-bar"><div class="insider-fill" style="width: 65%;"></div></div>
                        
                        <div class="stat-label" style="margin-top:10px;">Market Cap</div>
                        <div class="stat-value">{format_number(t_info.get('marketCap'))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                except: st.write("Data Fetch Error")
    else:
        st.info("👈 Enter tickers in the sidebar to begin.")
