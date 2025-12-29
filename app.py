import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎設定
st.set_page_config(page_title="量化選股 V7.0 - 艾達趨勢版", layout="wide")

# 2. 抗封鎖抓取數據
@st.cache_data(ttl=3600)
def fetch_stock_data(code):
    for suffix in [".TW", ".TWO"]:
        ticker = yf.Ticker(f"{code}{suffix}")
        hist = ticker.history(period="3y")
        if not hist.empty: return hist, ticker.info
    return None, None

# 3. 艾達趨勢指標計算
def calculate_elder_keltner(df):
    # EMA 20 (波段核心線)
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    # ATR (計算通道寬度)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(20).mean()
    
    # 肯特納通道
    df['KC_Upper'] = df['EMA20'] + (2 * df['ATR'])
    df['KC_Lower'] = df['EMA20'] - (2 * df['ATR'])
    
    # 艾達透視指標 (Bull/Bear Power)
    df['Bull_Power'] = df['High'] - df['EMA20']
    df['Bear_Power'] = df['Low'] - df['EMA20']
    
    # 技術檔位百分位 (Score)
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    df['Score'] = (p(df['Close']) * 0.6) + (p(df['Bull_Power']) * 0.4)
    
    # 【艾達波段買賣邏輯】
    # 買入：股價站上 EMA20 且 Bear_Power 轉正 (代表空頭力道衰竭) 且 位階中低
    df['Buy'] = np.where(
        (df['Close'] > df['EMA20']) & (df['Bear_Power'] > 0) & 
        (df['Bear_Power'].shift(1) < 0) & (df['Score'] < 75),
        df['Low'] * 0.96, np.nan
    )
    
    # 賣出：股價跌破 EMA20 或 Bull_Power 轉負
    df['Sell'] = np.where(
        (df['Close'] < df['EMA20']) & (df['Close'].shift(1) > df['EMA20']),
        df['High'] * 1.04, np.nan
    )
    return df

# --- UI 介面 ---
st.title("🎯 大波段量化選股 V7.0 (艾達趨勢系統)")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    if st.button("執行艾達波段掃描"):
        st.session_state.run = True

if "run" in st.session_state:
    hist_raw, info = fetch_stock_data(stock_input)
    if hist_raw is None:
        st.error("數據抓取失敗，請檢查代號")
    else:
        df = calculate_elder_keltner(hist_raw).tail(300)
        st.info(f"📊 **{info.get('longName', stock_input)}** 波段診斷：\n"
                "🔹 **藍色背景區**：肯特納通道，股價在通道上半部代表強勢波段。\n"
                "🔹 **核心邏輯**：當空頭力道(Bear Power)消失且站上均線時，即為穩健起漲點。")

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

        # 主圖
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['KC_Upper'], name="通道上軌", line=dict(color='rgba(0, 255, 204, 0.2)')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], name="波段核心線", line=dict(color='cyan', width=2)), row=1, col=1)
        
        # 買賣點
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="波段起點 ▲", mode='markers', marker=dict(symbol='triangle-up', size=18, color='#00FF00')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="趨勢結束 ▼", mode='markers', marker=dict(symbol='triangle-down', size=18, color='#FF4444')), row=1, col=1)

        # 艾達力道圖 (下方子圖)
        fig.add_trace(go.Bar(x=df.index, y=df['Bull_Power'], name="牛力(多頭)", marker_color='#00ff88'), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Bear_Power'], name="熊力(空頭)", marker_color='#ff4444'), row=2, col=1)

        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], type='date')
        fig.update_layout(height=850, template="plotly_dark", hovermode="x unified")
        fig.update_xaxes(range=[df.index[-50], df.index[-1]])
        
        st.plotly_chart(fig, use_container_width=True)
