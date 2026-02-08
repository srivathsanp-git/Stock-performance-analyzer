import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- CUSTOM THEMING (Robinhood/Apple Style) ---
st.set_page_config(page_title="Portfolio Insights", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    .stTextInput > div > div > input {
        background-color: #1a1a1a;
        color: white;
        border-radius: 12px;
        border: 1px solid #333;
        padding: 10px;
    }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00ff88; font-weight: 600; }
    .stButton>button {
        width: 100%;
        border-radius: 25px;
        background-color: #00ff88;
        color: black;
        font-weight: bold;
        border: none;
        height: 45px;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #05d676; transform: scale(1.02); }
    
    /* News Card Styling */
    .news-card {
        background-color: #111111;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #222;
        transition: 0.2s;
    }
    .news-card:hover { border-color: #444; background-color: #161616; }
    .news-title { font-size: 18px; font-weight: 600; color: #ffffff; text-decoration: none; }
    .news-meta { font-size: 12px; color: #888; margin-top: 8px; }
    .news-tag { 
        background-color: #333; 
        color: #00ff88; 
        padding: 2px 8px; 
        border-radius: 5px; 
        font-size: 10px; 
        text-transform: uppercase;
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC FUNCTIONS ---

def get_ticker_from_name(name):
    name = name.strip()
    if name.isupper() and 1 <= len(name) <= 5:
        return name
    try:
        search = yf.Search(name, max_results=1)
        return search.quotes[0]['symbol'] if search.quotes else None
    except Exception:
        return None

# --- UI LAYOUT ---

st.title("📈 Performance Intelligence")
st.write("Compare assets and stay informed with real-time market narratives.")

col1, col2, col3, col4, col5 = st.columns(5)
inputs = [col1.text_input("Asset 1", placeholder="Apple", key="i1"),
          col2.text_input("Asset 2", placeholder="Tesla", key="i2"),
          col3.text_input("Asset 3", key="i3"),
          col4.text_input("Asset 4", key="i4"),
          col5.text_input("Asset 5", key="i5")]

period = st.select_slider("Select Time Horizon", 
                          options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], value="1y")

if st.button("Generate Analysis"):
    valid_tickers = []
    
    with st.spinner("Analyzing market symbols..."):
        for name in inputs:
            if name:
                symbol = get_ticker_from_name(name)
                if symbol:
                    valid_tickers.append(symbol)
                else:
                    st.error(f"Invalid Asset: '{name}'. Please check the company name.")
                    st.stop()
    
    if valid_tickers:
        all_to_fetch = valid_tickers + ["^GSPC"]
        data = yf.download(all_to_fetch, period=period)['Close']
        
        if isinstance(data, pd.Series):
            data = data.to_frame()

        norm_data = (data / data.iloc[0]) * 100

        # --- CHARTING ---
        fig = go.Figure()
        for col in norm_data.columns:
            is_sp = col == "^GSPC"
            label = "S&P 500" if is_sp else col
            fig.add_trace(go.Scatter(
                x=norm_data.index, 
                y=norm_data[col],
                name=label,
                line=dict(width=3 if is_sp else 2, 
                          dash='dash' if is_sp else 'solid', 
                          color="#555555" if is_sp else None),
                hovertemplate='%{y:.2f}%'
            ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", y=1.1),
            yaxis=dict(showgrid=False),
            xaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- METRICS ---
        st.subheader("Market Snapshot")
        m_cols = st.columns(len(valid_tickers))
        for i, t in enumerate(valid_tickers):
            change = ((data[t].iloc[-1] / data[t].iloc[0]) - 1) * 100
            m_cols[i].metric(label=t, value=f"${data[t].iloc[-1]:.2f}", delta=f"{change:.2f}%")

        # --- NEWS SECTION ---
        st.markdown("---")
        st.subheader("Latest Market Narratives")
        
        # Collect news from all valid tickers
        for t in valid_tickers:
            ticker_obj = yf.Ticker(t)
            news_items = ticker_obj.news[:3] # Top 3 per stock
            
            for item in news_items:
                # Convert timestamp to readable date
                date_str = datetime.fromtimestamp(item['providerPublishTime']).strftime('%b %d, %Y')
                
                st.markdown(f"""
                <div class="news-card">
                    <span class="news-tag">{t}</span>
                    <a href="{item['link']}" target="_blank" class="news-title">{item['title']}</a>
                    <div class="news-meta">{item['publisher']} • {date_str}</div>
                </div>
                """, unsafe_allow_html=True)

elif st.button("Generate Analysis", disabled=True):
    pass
