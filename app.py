import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta  # 核心：確保這行在頂部
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# 1. 頁面配置 (必須是第一個 Streamlit 命令)
st.set_page_config(page_title="AI 趨勢評分導航器", layout="wide")

# 2. 抗封鎖抓取函數
@st.cache_data(ttl=3600)
def fetch_data(code):
    try:
        # 先嘗試上市代號
        ticker = yf.Ticker(f"{code}.TW")
        df = ticker.history(period="1y")
        # 若無資料再嘗試上櫃代號
        if df.empty:
            ticker = yf.Ticker(f"{code}.TWO")
            df = ticker.history(period="1y")
        return df
    except Exception as e:
        st.error(f"資料抓取失敗: {e}")
        return pd.DataFrame()

# 3. 核心邏輯
def get_rating(score, st_trend):
    if st_trend == 1:
        if score >= 85: return "🔥 強烈買入 (Strong Buy)", "success"
        if score >= 60: return "✅ 買入 (Buy)", "info"
        return "⏳ 觀望 (Wait/Hold)", "warning"
    else:
        if score <= 20: return "💀 強烈賣出 (Strong Sell)", "error"
        if score <= 45: return "⚠️ 賣出 (Sell)", "error"
        return "⏳ 觀望 (Wait/Hold)", "warning"

# --- UI 介面 ---
st.title("🤖 AI 綜合量化評分系統")

# 在側邊欄放置輸入框
with st.sidebar:
    st.header("設定")
    stock_input = st.text_input("輸入台股代號 (如: 2330)", value="2330")
    st.write("---")
    st.write("💡 **診斷條件：**")
    st.write("1. 60MA 斜率向上")
    st.write("2. ADX > 25")
    st.write("3. SuperTrend 轉多")
    st.write("4. 成交量 > 5日均量 1.5倍")
    st.write("5. RSI < 75")

if stock_input:
    with st.spinner('AI 正在診斷中，請稍候...'):
        df_raw = fetch_data(stock_input)
        
        if not df_raw.empty:
            df = df_raw.copy()
            # 計算指標
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['MA60_Slope'] = df['MA60'].diff(3)
            adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            st_data = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=4.0)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['Vol_MA5'] = df['Volume'].rolling(5).mean()
            
            df = pd.concat([df, adx, st_data], axis=1)
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # 評分邏輯
            score = 0
            if last['MA60_Slope'] > 0: score += 20
            if last['ADX_14'] > 25: score += 20
            if last['SUPERTd_10_4.0'] == 1: 
                score += 30
                if prev['SUPERTd_10_4.0'] == -1: score += 10
            if last['Volume'] > (last['Vol_MA5'] * 1.5): score += 15
            if 40 < last['RSI'] < 75: score += 5

            rating, status_color = get_rating(score, last['SUPERTd_10_4.0'])

            # 顯示評級
            if status_color == "success": st.success(f"### 評級：{rating}")
            elif status_color == "info": st.info(f"### 評級：{rating}")
            elif status_color == "warning": st.warning(f"### 評級：{rating}")
            else: st.error(f"### 評級：{rating}")

            # 顯示圖表
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="60MA", line=dict(color='yellow')), row=1, col=1)
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("無法取得數據，請確認代號是否正確。")
