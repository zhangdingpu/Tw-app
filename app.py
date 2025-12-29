import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎設定
st.set_page_config(page_title="量化選股 V3.0 Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    h1, h2, h3 { color: #00FFCC !important; font-weight: 800; }
    .stAlert { border-radius: 10px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# 2. 數據抓取 (加上 Cache 避免 Rate Limit)
@st.cache_data(ttl=3600) # 快取 1 小時
def fetch_stock_data(code):
    for suffix in [".TW", ".TWO"]:
        ticker = yf.Ticker(f"{code}{suffix}")
        hist = ticker.history(period="3y")
        if not hist.empty:
            return hist, ticker.info
    return None, None

# 3. 指標計算邏輯
def calculate_metrics(hist):
    df = hist.copy()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + gain/loss))
    
    # MA & BIAS
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['BIAS'] = (df['Close'] - df['MA20']) / df['MA20'] * 100
    
    # 技術檔位百分位 (0-100)
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    df['Score'] = (p(df['RSI']) * 0.5) + (p(df['BIAS']) * 0.5)
    
    # 訊號
    df['Buy'] = np.where((df['MA20'].shift(1) <= df['MA60'].shift(1)) & (df['MA20'] > df['MA60']), df['Low']*0.98, np.nan)
    df['Sell'] = np.where((df['MA20'].shift(1) >= df['MA60'].shift(1)) & (df['MA20'] < df['MA60']), df['High']*1.02, np.nan)
    return df

# --- UI 介面 ---
st.title("🎯 四維度量化選股 V3.0 (流暢優化版)")

with st.sidebar:
    stock_code = st.text_input("輸入台股代號", value="2330")
    if st.button("啟動分析"):
        st.session_state.run = True

if "run" in st.session_state:
    hist_raw, info = fetch_stock_data(stock_code)
    
    if hist_raw is None:
        st.error("❌ 抓取失敗：請檢查代號或稍後再試。")
    else:
        df = calculate_metrics(hist_raw).tail(400)
        
        # [優化] 解釋文字放在最上方
        st.info(f"📊 **{info.get('longName', stock_code)}** 分析報告：\n"
                "🔹 **綠色▲**：黃金交叉買點 | **紅色▼**：死亡交叉賣點\n"
                "🔹 **底層綠色區塊**：技術檔位分數 (越高代表越過熱，越低代表越便宜)")

        # 建立雙軸圖表
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 主 Y 軸：K 線與均線
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="K線", increasing_line_color='#00ff88', decreasing_line_color='#ff4444'
        ), secondary_y=False)
        
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20", line=dict(color='#00e5ff', width=1.2)), secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="MA60", line=dict(color='#cc00ff', width=1.2)), secondary_y=False)

        # 訊號圖標
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="買入", mode='markers', marker=dict(symbol='triangle-up', size=14, color='#00ff00')), secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="賣出", mode='markers', marker=dict(symbol='triangle-down', size=14, color='#ff0000')), secondary_y=False)

        # 副 Y 軸：檔位分數 (固定範圍 0-100)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Score'], name="技術檔位分數",
            line=dict(color='rgba(0, 255, 204, 0.5)', width=2),
            fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.1)'
        ), secondary_y=True)

        # [優化] 滑動順暢度設定
        fig.update_xaxes(
            rangebreaks=[dict(bounds=["sat", "mon"])], # 跳過假日
            rangeslider_visible=True,
            rangeslider_thickness=0.1,
            type='date'
        )
        
        fig.update_layout(
            height=700, # 固定高度
            margin=dict(l=10, r=10, t=20, b=10),
            template="plotly_dark",
            hovermode="x unified",
            yaxis_title="股價 (TWD)",
            yaxis2=dict(title="檔位分數 (0-100)", range=[0, 105], side="right", showgrid=False),
            legend=dict(orientation="h", y=1.1)
        )

        # 預設顯示最近 30 根 K 線
        fig.update_xaxes(range=[df.index[-35], df.index[-1]])

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})
