import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面風格優化
st.set_page_config(page_title="量化選股 V8.5 - 終極波段版", layout="wide")
st.markdown("""<style>.main { background-color: #000000; } h1,h2,h3 { color: #00FFCC !important; }</style>""", unsafe_allow_html=True)

# 2. 穩定抓取數據 (含快取)
@st.cache_data(ttl=3600)
def fetch_data(code):
    for suffix in [".TW", ".TWO"]:
        ticker = yf.Ticker(f"{code}{suffix}")
        hist = ticker.history(period="3y")
        if not hist.empty: return hist, ticker.info
    return None, None

# 3. 核心邏輯整合：慣性斜率 + 靈敏成交量
def calculate_ultimate_system(df):
    df = df.copy()
    # 使用 WMA 提升貼合度 (減少落後)
    w = np.arange(1, 21)
    df['Trend_Line'] = df['Close'].rolling(20).apply(lambda x: np.dot(x, w)/w.sum(), raw=True)
    
    # 斜率：只需 1 日轉正即反應
    df['Slope'] = df['Trend_Line'].diff(1)
    
    # 檔位分數 (放寬至 75 分)
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    df['Score'] = (p(df['Close']) * 0.5) + (p(df['Close'].diff().rolling(10).mean()) * 0.5)
    
    # 成交量：只要比 5 日平均多 1.1 倍即可 (輕微放量)
    df['Vol_MA'] = df['Volume'].rolling(5).mean()
    
    # 【整合買入條件】：斜率向上 + 站上線 + 位階合理 + 微量增
    df['Buy'] = np.where(
        (df['Slope'] > 0) & (df['Close'] > df['Trend_Line']) & 
        (df['Score'] < 75) & (df['Volume'] > df['Vol_MA'] * 1.1),
        df['Low'] * 0.96, np.nan
    )
    
    # 【整合賣出條件】：斜率轉負 (彎頭向下)
    df['Sell'] = np.where(
        (df['Slope'] < 0) & (df['Slope'].shift(1) >= 0),
        df['High'] * 1.04, np.nan
    )
    return df

# --- UI 介面 ---
st.title("🎯 大波段量化選股 V8.5 (整合優化版)")
stock_input = st.sidebar.text_input("輸入台股代號", value="2330")

if st.sidebar.button("啟動整合分析"):
    raw, info = fetch_data(stock_input)
    if raw is not None:
        df = calculate_ultimate_system(raw).tail(300)
        st.success(f"✅ 已成功優化 {info.get('longName')} 的波段訊號")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
        
        # 主圖 (K線 + 趨勢線)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Trend_Line'], name="波段趨勢線", line=dict(color='#00e5ff', width=3)), row=1, col=1)
        
        # 買賣點 (加大顯示)
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="波段起點 ▲", mode='markers', marker=dict(symbol='triangle-up', size=20, color='#00ff00', line=dict(width=2, color='white'))), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="趨勢轉弱 ▼", mode='markers', marker=dict(symbol='triangle-down', size=20, color='#ff4444', line=dict(width=2, color='white'))), row=1, col=1)

        # 底部斜率圖 (讓你一眼看出趨勢有沒有變色)
        colors = ['#00FFCC' if s > 0 else '#FF4444' for s in df['Slope']]
        fig.add_trace(go.Bar(x=df.index, y=df['Slope'], name="趨勢斜率", marker_color=colors), row=2, col=1)

        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], type='date')
        fig.update_layout(height=800, template="plotly_dark", hovermode="x unified", margin=dict(t=30, b=10))
        fig.update_xaxes(range=[df.index[-45], df.index[-1]]) # 預設顯示最近一個半月
        
        st.plotly_chart(fig, use_container_width=True)
