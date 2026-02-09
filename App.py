import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
    </style>
    """, unsafe_allow_html=True)

# --- DATA FETCHING ---

@st.cache_data(ttl=3600)
def get_ticker_symbol(name):
    try:
        if name.isupper() and 1 <= len(name) <= 5: return name
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

@st.cache_data(ttl=3600)
def fetch_metrics(t_str, curr_price):
    try:
        t = yf.Ticker(t_str)
        info = t.info
        t_pe = info.get('trailingPE') or (curr_price / info.get('trailingEps') if info.get('trailingEps') else 0)
        f_pe = info.get('forwardPE') or (curr_price / info.get('forwardEps') if info.get('forwardEps') else 0)
        divs = t.dividends
        last_div = divs.iloc[-1] if not divs.empty else 0
        q_yield = (last_div / curr_price) * 100 if last_div > 0 else 0
        
        buy_vol, sell_vol = 0, 0
        try:
            insider = t.insider_transactions
            if insider is not None and not insider.empty:
                buys = insider[insider['Text'].str.contains('Purchase|Acquisition', case=False, na=False)]
                buy_vol = buys['Shares'].sum()
                sales = insider[insider['Text'].str.contains('Sale|Disposition', case=False, na=False)]
                sell_vol = sales['Shares'].sum()
        except: pass
        return {"t_pe": t_pe, "f_pe": f_pe, "q_div": last_div, "q_yield": q_yield, "i_buy": buy_vol, "i_sell": sell_vol}
    except: return {"t_pe":0, "f_pe":0, "q_div":0, "q_yield":0, "i_buy":0, "i_sell":0}

@st.cache_data(ttl=600)
def fetch_history(tickers):
    return yf.download(list(set(tickers)), period="max", progress=False)['Close']

def format_vol(val):
    if not val or val == 0: return "0"
    if val >= 1e6: return f"{val/1e6:.1f}M"
    return f"{val/1e3:.1f}K" if val >= 1e3 else f"{int(val)}"

# --- UI LAYOUT ---
col_left, col_right = st.columns([1, 4.2])

valid_tickers = []
with col_left:
    st.markdown("<h3 style='font-weight:700; color:#10b981;'>PORTFOLIO</h3>", unsafe_allow_html=True)
    for i in range(5):
        name = st.text_input(f"Asset {i+1}", key=f"a{i}", placeholder="Ticker")
        if name:
            sym = get_ticker_symbol(name)
            if sym: valid_tickers.append(sym)

with col_right:
    h1, h2 = st.columns([3, 1])
    h1.markdown("<h1 style='font-weight:700;'>Intelligence Terminal</h1>", unsafe_allow_html=True)
    
    range_options = ["3 Months", "6 Months", "1 Year", "5 Years", "Life Time"]
    period_label = h2.select_slider("Range", options=range_options, value="1 Year")

    if valid_tickers:
        all_prices = fetch_history(valid_tickers + ["^GSPC"])
        
        # Determine Window
        window_map = {"3 Months": 90, "6 Months": 180, "1 Year": 365, "5 Years": 1825}
        days = window_map.get(period_label, len(all_prices))

        chart_prices = all_prices.tail(days).ffill()
        norm_data = (chart_prices / chart_prices.iloc[0]) * 100

        # Performance Chart
        fig = go.Figure()
        for c in norm_data.columns:
            is_sp = (c == "^GSPC")
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[c], name="S&P 500" if is_sp else c,
                                     line=dict(width=1.5 if is_sp else 3, dash='dash' if is_sp else 'solid')))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=10,b=0),
                          legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("<h3 style='color:#10b981; font-weight:700;'>MARKET INTELLIGENCE</h3>", unsafe_allow_html=True)
        cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with cols[i]:
                # Performance Math
                asset_curr = chart_prices[t].iloc[-1]
                asset_growth = ((asset_curr / chart_prices[t].iloc[0]) - 1) * 100
                sp_growth = ((chart_prices["^GSPC"].iloc[-1] / chart_prices["^GSPC"].iloc[0]) - 1) * 100
                
                status_emoji = "🚀" if asset_growth > sp_growth else "📉"
                m = fetch_metrics(t, asset_curr)
                
                st.markdown(f"<p class='ticker-header'>{t}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='price-sub'>${asset_curr:.2f}</p>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    # 1. GROWTH & STATUS
                    st.markdown(f"<p class='label-black'>Growth vs S&P ({period_label})</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{status_emoji} {asset_growth:+.1f}% <span style='font-size:0.8rem; opacity:0.7;'>(S&P: {sp_growth:+.1f}%)</span></p>", unsafe_allow_html=True)

                    # 2. VALUATION
                    st.markdown("<p class='label-black'>P/E (Trail | Fwd)</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{m['t_pe']:.1f} | {m['f_pe']:.1f}</p>", unsafe_allow_html=True)

                    # 3. INSIDER
                    st.markdown("<p class='label-black'>Insider (Buy | Sell)</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{format_vol(m['i_buy'])} | {format_vol(m['i_sell'])}</p>", unsafe_allow_html=True)

                    # 4. DIVIDEND
                    st.markdown("<p class='label-black'>Quarterly Div Yield</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{m['q_yield']:.2f}% (${m['q_div']:.2f})</p>", unsafe_allow_html=True)
    else:
        st.info("Input ticker in the sidebar to initialize terminal.")
