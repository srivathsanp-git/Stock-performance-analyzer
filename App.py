import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# Function to attempt to get ticker from name (Simple version)
def get_ticker(name):
    # If it looks like a ticker already, return it
    if name.isupper() and len(name) <= 5:
        return name.strip()
    # Otherwise, search yfinance (this is a simplified search logic)
    try:
        search = yf.Ticker(name)
        return search.ticker if search.ticker else name
    except:
        return name

st.set_page_config(page_title="Stock Performance Analyzer", layout="wide")

st.title("📈 Stock vs S&P 500 Analyzer")
st.write("Enter up to 5 stock names or tickers to compare their performance.")

# 1. Setup Input Screen
with st.sidebar:
    st.header("Search Settings")
    names = []
    for i in range(5):
        name = st.text_input(f"Stock {i+1}", key=f"stock_{i}")
        if name:
            names.append(name)
    
    period = st.selectbox("Select Time Period", ["YTD", "1y", "5y", "max"])
    analyze_btn = st.button("Analyze Performance")

# 2. Performance Logic
if analyze_btn and names:
    tickers = [get_ticker(n) for n in names]
    tickers.append("^GSPC")  # Adding S&P 500
    
    # Fetch Data
    data = yf.download(tickers, period=period)['Close']
    
    # Normalize data to show % increase (starting at 0% or 100 base)
    # Formula: (Price / First Price) * 100
    norm_data = (data / data.iloc[0]) * 100
    
    # 3. Dynamic Chart
    fig = go.Figure()
    
    for column in norm_data.columns:
        name = "S&P 500" if column == "^GSPC" else column
        fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[column], mode='lines', name=name))
    
    fig.update_layout(
        title=f"Relative Performance Over {period.upper()}",
        xaxis_title="Date",
        yaxis_title="Normalized Price (Base 100)",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 4. Statistics Table
    st.subheader("Current Market Snapshot")
    cols = st.columns(len(tickers) - 1)
    
    for i, t in enumerate(tickers[:-1]): # Exclude S&P 500 from the metric cards
        current_price = data[t].iloc[-1]
        total_growth = ((data[t].iloc[-1] / data[t].iloc[0]) - 1) * 100
        
        with cols[i]:
            st.metric(label=t, value=f"${current_price:.2f}", delta=f"{total_growth:.2f}%")

elif analyze_btn and not names:
    st.warning("Please enter at least one stock name.")
