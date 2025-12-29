import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="量化選股 V8.0 - 終極慣性版", layout="wide")

@st.cache_data(ttl=3600)
def fetch_data(code):
    for suffix in [".TW", ".TWO"]:
        ticker = yf.Ticker(f"{code}{suffix}")
        hist = ticker.history(period="3y")
        if not hist.empty: return hist, ticker.info
    return None, None

def calculate_momentum_system(df):
    # 1. 趨勢核心：線性加權均線 (WMA) 比普通均線更貼合股價
    weights = np.arange(1, 21)
    df['WMA20'] = df['Close'].rolling(20).apply(lambda x: np.dot(x, weights)/weights.sum(), raw=True)
    
    # 2. 斜率計算 (Slope)：判斷趨勢的角度
    df['Slope'] = df['WMA20'].diff(3) 
    
    # 3. 技術檔位分數 (更加靈敏)
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    df['Score'] = (p(df['Close']) * 0.4) + (p(df['Close'].diff().rolling(10).mean()) * 0.6)
    
    # 4. 【終極波段邏輯】
    # 買入：斜率轉正 (向上翹) 且 分數在低位 (< 50) 且 價格站在 WMA 上
    df['Buy'] = np.where(
        (df['Slope'] > 0) & (df['Slope'].shift(1) <= 0) & 
        (df['Score'] < 50) & (df['Close'] > df['WMA20']),
        df['Low'] * 0.97, np.nan
    )
    
    # 賣出：斜率轉負 (向下彎) 或 股價跌破 WMA
    df['Sell'] = np.where(
        (df['Slope'] < 0) & (df['Slope'].shift(1) >= 0),
        df['High'] * 1.03, np.nan
    )
    return df

# --- UI 介面 ---
st.title("🎯 量化選股 V8.0 (終極慣性系統)")
stock_input = st.sidebar.text_input("輸入台股代號", value="2330")
if st.sidebar.button("分析大波段"):
    raw, info = fetch_data(stock_input)
    if raw is not None:
        df = calculate_momentum_system(raw).tail(300)
        st.info(f"📈 **{info.get('longName')}** 診斷：買點出現在趨勢剛『抬頭』且位階便宜時。")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['WMA20'], name="趨勢生命線", line=dict(color='#00FFCC', width=3)), row=1, col=1)
        
        # 買賣點
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="波段起點 ▲", mode='markers', marker=dict(symbol='triangle-up', size=18, color='#00FF00', line=dict(width=2, color='white'))), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="趨勢轉弱 ▼", mode='markers', marker=dict(symbol='triangle-down', size=18, color='#FF4444', line=dict(width=2, color='white'))), row=1, col=1)

        # 斜率柱狀圖 (輔助判斷趨勢強弱)
        colors = ['#00FFCC' if s > 0 else '#FF4444' for s in df['Slope']]
        fig.add_trace(go.Bar(x=df.index, y=df['Slope'], name="趨勢斜率", marker_color=colors), row=2, col=1)

        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], type='date')
        fig.update_layout(height=800, template="plotly_dark", hovermode="x unified")
        fig.update_xaxes(range=[df.index[-60], df.index[-1]])
        st.plotly_chart(fig, use_container_width=True)
