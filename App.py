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

# --- UTILS ---
@st.cache_data(ttl=3600)
def get_ticker_symbol(name):
    try:
        if name.isupper() and 1 <= len(name) <= 5: return name
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

@st.cache_data(ttl=3600)
def fetch_valuation_metrics(t_str, curr_price):
    try:
        t = yf.Ticker(t_str)
        info = t.info
        t_pe = info.get('trailingPE')
        if not t_pe:
            eps = info.get('trailingEps')
            t_pe = curr_price / eps if eps and eps > 0 else 0
        f_pe = info.get('forwardPE')
        if not f_pe:
            f_eps = info.get('forwardEps')
            f_pe = curr_price / f_eps if f_eps and f_eps > 0 else 0
        divs = t.dividends
        last_div = divs.iloc[-1] if not divs.empty else 0
        q_yield = (last_div / curr_price) * 100 if last_div > 0 else 0
        return {"t_pe": t_pe, "f_pe": f_pe, "q_div": last_div, "q_yield": q_yield}
    except:
        return {"t_pe": 0, "f_pe": 0, "q_div": 0, "q_yield": 0}

@st.cache_data(ttl=600)
def fetch_history(tickers):
    return yf.download(list(set(tickers)), period="2y", progress=False)['Close']

def format_num(val):
    if not val or val == 0 or np.isnan(val): return "—"
    return f"{val:.2f}"

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
    period_label = h2.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y"], value="1y")

    if valid_tickers:
        prices = fetch_history(valid_tickers + ["^GSPC"])
        days = {"1mo":30, "3mo":90, "6mo":180, "1y":365, "2y":730}[period_label]
        chart_data = (prices.tail(days) / prices.tail(days).iloc[0]) * 100

        # --- UPDATED CHART WITH BOTTOM RIGHT LEGEND ---
        fig = go.Figure()
        for c in chart_data.columns:
            is_sp = c == "^GSPC"
            fig.add_trace(go.Scatter(
                x=chart_data.index, y=chart_data[c], 
                name="S&P 500" if is_sp else c,
                line=dict(width=1.5 if is_sp else 3, dash='dash' if is_sp else 'solid', 
                          color="#4b5563" if is_sp else None)
            ))
        
        fig.update_layout(
            template="plotly_dark", 
            height=400, 
            margin=dict(l=0,r=0,t=10,b=0), 
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            # LEGEND POSITIONING
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=0.01,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(0,0,0,0.5)"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        # Asset Analysis
        st.markdown("<h3 style='color:#10b981; font-weight:700;'>VALUATION & FLOW</h3>", unsafe_allow_html=True)
        cols = st.columns(len(valid_tickers))
        
        for i, t in enumerate(valid_tickers):
            with cols[i]:
                raw_p = prices[t].iloc[-1]
                curr_p = float(raw_p.iloc[0]) if hasattr(raw_p, "__len__") else float(raw_p)
                m = fetch_valuation_metrics(t, curr_p)
                
                st.markdown(f"<p class='ticker-header'>{t}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='price-sub'>${curr_p:.2f}</p>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    st.markdown("<p class='label-black'>Trailing P/E</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{format_num(m['t_pe'])}</p>", unsafe_allow_html=True)
                    
                    st.markdown("<p class='label-black'>Forward P/E</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='value-black'>{format_num(m['f_pe'])}</p>", unsafe_allow_html=True)

                    st.markdown("<p class='label-black'>Quarterly Div Yield</p>", unsafe_allow_html=True)
                    div_display = f"{m['q_yield']:.2f}% (${m['q_div']:.2f})" if m['q_div'] > 0 else "0.00%"
                    st.markdown(f"<p class='value-black'>{div_display}</p>", unsafe_allow_html=True)

                    st.markdown("<p class='label-black'>Target (1Y High)</p>", unsafe_allow_html=True)
                    h52 = float(prices[t].tail(252).max())
                    gap = ((h52 / curr_p) - 1) * 100
                    st.markdown(f"<p class='value-black'>${h52:,.2f} ({gap:+.1f}%)</p>", unsafe_allow_html=True)
    else:
        st.info("Input ticker in the sidebar.")
