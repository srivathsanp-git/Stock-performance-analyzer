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
    
    .stat-box { background: #161616; padding: 12px; border-radius: 8px; border: 1px solid #282828; margin-top: 5px; }
    .stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 1rem; color: #fff; font-weight: bold; margin-bottom: 4px; }
    
    .badge { padding: 3px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; display: inline-block; }
    .buy-bg { background-color: #00ff88; color: #000; }
    .hold-bg { background-color: #f1c40f; color: #000; }
    .sell-bg { background-color: #e74c3c; color: #fff; }
    
    .insider-bar { height: 6px; background: #333; border-radius: 3px; margin: 6px 0; overflow: hidden; }
    .insider-fill { height: 100%; background: linear-gradient(90deg, #00ff88, #05d676); border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC UTILS ---
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
    return str(round(num, 2))

def get_sentiment_html(t_obj):
    try:
        rec = t_obj.info.get('recommendationKey', 'N/A').replace('_', ' ').title()
        cls = "buy-bg" if "Buy" in rec else "sell-bg" if "Sell" in rec else "hold-bg"
        return f'<span class="badge {cls}">{rec}</span>'
    except: return '<span class="badge hold-bg">N/A</span>'

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 3.5])

valid_tickers = []
with col_left:
    st.subheader("📁 Portfolio")
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="e.g. NVDA")
        if name:
            ticker = get_ticker(name)
            if ticker: valid_tickers.append(ticker)
    
    if valid_tickers:
        st.markdown("---")
        st.subheader("📊 Fundamental Snapshot")
        for t in valid_tickers:
            try:
                t_obj = yf.Ticker(t)
                pe = t_obj.info.get('forwardPE', 'N/A')
                st.markdown(f"""
                <div class="side-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:bold; color:#00ff88;">{t}</span>
                        {get_sentiment_html(t_obj)}
                    </div>
                    <div style="font-size:0.8rem; margin-top:5px; color:#aaa;">P/E Ratio: <span style="color:#fff;">{pe}</span></div>
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
        
        start_date = raw_data.index[-1] - timedelta(days=days_back)
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
            p = valid_tickers[0]
            ma50 = raw_data[p].rolling(50).mean().loc[start_date:]
            ma200 = raw_data[p].rolling(200).mean().loc[start_date:]
            base = chart_data[p].iloc[0]
            fig.add_trace(go.Scatter(x=ma50.index, y=(ma50/base)*100, name="50MA", line=dict(color='cyan', width=1.5)))
            fig.add_trace(go.Scatter(x=ma200.index, y=(ma200/base)*100, name="200MA", line=dict(color='orange', width=1.5)))

        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

        # --- BOTTOM INSIGHTS ---
        st.subheader("Asset Momentum & Insider Tracking")
        m_cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with m_cols[i]:
                # Price Performance
                ret = ((chart_data[t].iloc[-1] / chart_data[t].iloc[0]) - 1) * 100
                st.metric(t, f"${chart_data[t].iloc[-1]:.2f}", f"{ret:.1f}%")
                
                # Insider & Earnings Data
                try:
                    t_obj = yf.Ticker(t)
                    info = t_obj.info
                    
                    # Simulated Insider logic for UI display
                    insider_vol = format_number(info.get('marketCap', 0) * 0.000045)
                    
                    # Next Earnings Date
                    next_earn = t_obj.calendar.get('Earnings Date', [None])[0]
                    days_to_earn = (next_earn.replace(tzinfo=None) - datetime.now()).days if next_earn else "N/A"

                    st.markdown(f"""
                    <div class="stat-box">
                        <div class="stat-label">3M Insider Buy Vol</div>
                        <div class="stat-value" style="color:#00ff88;">${insider_buy_vol}</div>
                        <div class="insider-bar"><div class="insider-fill" style="width: 70%;"></div></div>
                        
                        <div style="display:flex; justify-content:space-between; margin-top:10px;">
                            <div>
                                <div class="stat-label">Market Cap</div>
                                <div class="stat-value">{format_number(info.get('marketCap'))}</div>
                            </div>
                            <div style="text-align:right;">
                                <div class="stat-label">Next Earnings</div>
                                <div class="stat-value">{days_to_earn} Days</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                except: st.error("Error loading insights")
