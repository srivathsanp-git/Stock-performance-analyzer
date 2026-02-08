import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

# --- CUSTOM THEMING ---
st.set_page_config(page_title="Portfolio Insights", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    .stTextInput > div > div > input { background-color: #1a1a1a; color: white; border-radius: 12px; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00ff88; font-weight: 600; }
    .stButton>button { width: 100%; border-radius: 25px; background-color: #00ff88; color: black; font-weight: bold; height: 45px; }
    .news-card { background-color: #111111; border-radius: 15px; padding: 20px; margin-bottom: 15px; border: 1px solid #222; }
    .news-title { font-size: 18px; font-weight: 600; color: #ffffff; text-decoration: none; }
    .news-tag { background-color: #333; color: #00ff88; padding: 2px 8px; border-radius: 5px; font-size: 10px; margin-right: 8px; }
    </style>
    """, unsafe_allow_html=True)

def get_ticker_from_name(name):
    name = name.strip()
    if not name: return None
    if name.isupper() and 1 <= len(name) <= 5: return name
    try:
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except: return None

# --- UI LAYOUT ---
st.title("📈 Performance Intelligence")
col1, col2, col3, col4, col5 = st.columns(5)
input_names = [col1.text_input(f"Asset {i+1}", key=f"i{i}") for i in range(5)]
period = st.select_slider("Select Time Horizon", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")

button_disabled = not any(input_names)

if st.button("Generate Analysis", disabled=button_disabled, key="main_analysis_btn"):
    valid_tickers = []
    for name in input_names:
        if name:
            symbol = get_ticker_from_name(name)
            if symbol: valid_tickers.append(symbol)

    if valid_tickers:
        all_to_fetch = list(set(valid_tickers + ["^GSPC"]))
        data = yf.download(all_to_fetch, period=period)['Close']
        if isinstance(data, pd.Series): data = data.to_frame(name=valid_tickers[0])
        data = data.ffill().dropna()

        # Normalization
        norm_data = (data / data.iloc[0]) * 100

        # --- CHARTING ---
        fig = go.Figure()
        for col in norm_data.columns:
            is_sp = col == "^GSPC"
            fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name="S&P 500" if is_sp else col,
                                     line=dict(width=3 if is_sp else 2, dash='dash' if is_sp else 'solid', 
                                     color="#555555" if is_sp else None)))
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # --- METRICS & RISK ASSESSMENT ---
        st.subheader("Market Snapshot & Risk Profile")
        
        # Calculation for Risk Table
        returns = data.pct_change().dropna()
        risk_data = []
        
        for t in valid_tickers:
            if t in data.columns:
                total_ret = ((data[t].iloc[-1] / data[t].iloc[0]) - 1) * 100
                volatility = returns[t].std() * np.sqrt(252) * 100
                risk_data.append({"Ticker": t, "Total Return": f"{total_ret:.2f}%", "Annualized Volatility": f"{volatility:.2f}%"})
        
        # Display Metrics in columns
        m_cols = st.columns(len(valid_tickers))
        for i, t in enumerate(valid_tickers):
            if t in data.columns:
                current_price = data[t].iloc[-1]
                change = ((data[t].iloc[-1] / data[t].iloc[0]) - 1) * 100
                m_cols[i].metric(label=t, value=f"${current_price:.2f}", delta=f"{change:.2f}%")

        # Display Risk Table
        st.table(pd.DataFrame(risk_data).set_index("Ticker"))

        # --- NEWS ---
        st.markdown("---")
        st.subheader("Latest Market Narratives")
        for t in valid_tickers:
            news_items = yf.Ticker(t).news[:2]
            for item in news_items:
                date_str = datetime.fromtimestamp(item['providerPublishTime']).strftime('%b %d, %Y')
                st.markdown(f'<div class="news-card"><span class="news-tag">{t}</span><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a><div class="news-meta">{item["publisher"]} • {date_str}</div></div>', unsafe_allow_html=True)
