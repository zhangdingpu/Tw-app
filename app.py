import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="2330 飆股分析", layout="wide")
st.title("🚀 飆股自動篩選器 - 2330 走勢分析")

# 1. 抓取數據並強制格式化
@st.cache_data
def load_data(ticker):
    # 抓取最近 6 個月的數據，確保 X 軸有足夠時間跨度
    df = yf.download(ticker, period="6mo", interval="1d")
    # 解決 yfinance 多層索引問題
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

import pandas as pd # 確保有導入 pandas
ticker = "2330.TW"
df = load_data(ticker)

if not df.empty:
    # 2. 建立圖表
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.7, 0.3]
    )

    # 繪製 K 線 (Y 軸：價格)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="價格",
        increasing_line_color='#ef5350', # 漲紅
        decreasing_line_color='#26a69a'  # 跌綠
    ), row=1, col=1)

    # 繪製成交量 (Y 軸：張數)
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name="成交量",
        marker_color='rgba(128, 128, 128, 0.5)'
    ), row=2, col=1)

    # 3. 嚴格設定坐標軸 (X軸時間, Y軸價格)
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=700,
        margin=dict(l=50, r=10, t=10, b=10),
        # 設定 Y 軸格式為一般數字，不使用科學符號
        yaxis1=dict(title="價格 (TWD)", side="right", tickformat=".0f"),
        yaxis2=dict(title="成交量", side="right"),
        xaxis=dict(type='date', title="時間")
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("數據抓取失敗，請檢查網路。")
