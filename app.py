import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# 網頁基礎設定
st.set_page_config(page_title="2330 K線分析", layout="wide")

st.title("📊 台積電 (2330.TW) 技術走勢圖")

# 1. 獲取數據 (確保處理 yfinance 的索引問題)
@st.cache_data
def get_stock_data(ticker):
    # 下載最近半年的日K數據
    df = yf.download(ticker, period="6mo", interval="1d")
    # 強制扁平化多層索引欄位 (yfinance 0.2.x+ 版本的常見問題)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

ticker = "2330.TW"
df = get_stock_data(ticker)

if not df.empty:
    # 2. 建立包含兩個子圖的畫布
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True,           # 共用時間軸
        vertical_spacing=0.03,      # 子圖間距
        row_heights=[0.75, 0.25]    # K線佔 75%，成交量佔 25%
    )

    # 3. 繪製 K線 (Candlestick)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="K線",
        increasing_line_color='#ef5350', # 漲：紅
        decreasing_line_color='#26a69a', # 跌：綠
        increasing_fillcolor='#ef5350',
        decreasing_fillcolor='#26a69a'
    ), row=1, col=1)

    # 4. 繪製成交量 (Volume)
    # 根據漲跌設定成交量柱狀圖顏色
    colors = ['#ef5350' if close >= open else '#26a69a' 
              for open, close in zip(df['Open'], df['Close'])]
    
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name="成交量",
        marker_color=colors,
        opacity=0.8
    ), row=2, col=1)

    # 5. 比照 TradingView 的黑色主題美化
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False, # 關閉下方縮放條，介面更乾淨
        height=700,
        margin=dict(l=20, r=50, t=10, b=10),
        # Y軸設定：價格放在右側，符合你的截圖習慣
        yaxis1=dict(title="價格 (TWD)", side="right", tickformat=".0f", gridcolor='#2a2e39'),
        yaxis2=dict(title="成交量", side="right", gridcolor='#2a2e39'),
        xaxis=dict(gridcolor='#2a2e39', type='date')
    )

    # 6. 在 Streamlit 顯示
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("目前無法獲取 2330.TW 的數據，請稍後再試。")
