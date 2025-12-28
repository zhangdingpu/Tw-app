import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ... (前面的數據抓取代碼保持不變)

# 建立兩個子圖，上方是 K 線，下方是買入評分線
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.05, 
    row_heights=[0.7, 0.3],
    subplot_titles=("股價 K 線與 MA200", "🔥 綜合買入建議分數 (0-100)")
)

# 1. 上方圖表：K 線
fig.add_trace(go.Candlestick(
    x=hist.index, open=hist['Open'], high=hist['High'], 
    low=hist['Low'], close=hist['Close'], name="K線"
), row=1, col=1)

# 加入 MA200 趨勢線
fig.add_trace(go.Scatter(
    x=hist.index, y=hist['twoHundredDayAverage'], 
    name="MA200", line=dict(color='orange', width=2)
), row=1, col=1)

# 2. 下方圖表：這就是你要的那條「買入判斷線」
# 我們假設 score_series 是你計算出來的加權分數 (0-100)
# 這裡先用邏輯模擬一條線：
score_series = (hist['Close'] / hist['Close'].rolling(20).mean() * 50) + 25 # 範例權重邏輯

fig.add_trace(go.Scatter(
    x=hist.index, y=score_series, 
    name="買入評分", 
    line=dict(color='red', width=3),
    fill='tozeroy', # 填滿下方顏色
    fillcolor='rgba(255, 0, 0, 0.2)'
), row=2, col=1)

# 設定評分線的 Y 軸範圍固定在 0-100
fig.update_yaxes(range=[0, 110], row=2, col=1)

# 加入門檻基準線
fig.add_hline(y=70, line_dash="dash", line_color="green", annotation_text="強力買入區", row=2, col=1)

fig.update_layout(height=800, template="plotly_dark", showlegend=False, xaxis_rangeslider_visible=False)

st.plotly_chart(fig, use_container_width=True)
