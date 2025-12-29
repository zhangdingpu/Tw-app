import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 設定網頁標題
st.set_page_config(page_title="飆股篩選器-2330測試", layout="wide")

st.title("🚀 飆股自動篩選器 - 2330 走勢分析")

# 1. 抓取數據 (台積電 2330)
@st.cache_data # 增加快取，避免重複抓取
def load_data(ticker):
    df = yf.download(ticker, period="1y")
    return df

ticker = "2330.TW"
data = load_data(ticker)

if not data.empty:
    # 2. 建立繪圖
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_heights=[0.7, 0.3])

    # K線圖
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name="收盤價",
        increasing_line_color='#ef5350', # 漲紅
        decreasing_line_color='#26a69a'  # 跌綠
    ), row=1, col=1)

    # 成交量
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Volume'],
        name="成交量",
        marker_color='gray'
    ), row=2, col=1)

    # 樣式設定 (比照截圖的黑色主題)
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=10, r=10, t=30, b=10)
    )

    # 3. 顯示圖表
    st.plotly_chart(fig, use_container_width=True)
    
    # 顯示數據表格供確認
    st.subheader("最新數據摘要")
    st.write(data.tail())
else:
    st.error("找不到數據，請檢查網路連線或代碼。")
