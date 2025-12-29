import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import random

# 1. 頁面基礎風格
st.set_page_config(page_title="量化選股 V6.0 - 終極穩定版", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    h1, h2, h3 { color: #00FFCC !important; font-weight: 800; }
    .stInfo { background-color: #0E1117; border: 1px solid #00FFCC; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. 數據抓取：增加抗封鎖與自動重試邏輯
@st.cache_data(ttl=3600)
def fetch_data_robust(code):
    for suffix in [".TW", ".TWO"]:
        full_code = f"{code}{suffix}"
        # 嘗試多次抓取
        for attempt in range(3):
            try:
                ticker = yf.Ticker(full_code)
                # 取得 3 年數據以計算長線百分位
                hist = ticker.history(period="3y", interval="1d")
                if not hist.empty:
                    return hist, ticker.info
            except Exception:
                time.sleep(random.uniform(1, 2)) # 失敗則隨機等待再試
                continue
    return None, None

# 3. 大波段超級趨勢 (SuperTrend) 計算
def calculate_supertrend(df, period=10, multiplier=4): # 提高乘數以抓取更大波段
    df = df.copy()
    hl2 = (df['High'] + df['Low']) / 2
    # ATR 計算 (真實波動幅度)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['Close'].shift(1)), 
               abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(period).mean()
    
    df['upperband'] = hl2 + (multiplier * df['ATR'])
    df['lowerband'] = hl2 - (multiplier * df['ATR'])
    df['in_trend'] = True

    for i in range(1, len(df.index)):
        if df['Close'].iloc[i] > df['upperband'].iloc[i-1]:
            df.iat[i, df.columns.get_loc('in_trend')] = True
        elif df['Close'].iloc[i] < df['lowerband'].iloc[i-1]:
            df.iat[i, df.columns.get_loc('in_trend')] = False
        else:
            df.iat[i, df.columns.get_loc('in_trend')] = df['in_trend'].iloc[i-1]
            if df['in_trend'].iloc[i] and df['lowerband'].iloc[i] < df['lowerband'].iloc[i-1]:
                df.iat[i, df.columns.get_loc('lowerband')] = df['lowerband'].iloc[i-1]
            if not df['in_trend'].iloc[i] and df['upperband'].iloc[i] > df['upperband'].iloc[i-1]:
                df.iat[i, df.columns.get_loc('upperband')] = df['upperband'].iloc[i-1]
    
    df['Trend_Line'] = np.where(df['in_trend'], df['lowerband'], df['upperband'])
    return df

# 4. 指標整合與大波段邏輯
def process_wave_logic(hist):
    df = hist.copy()
    # 技術檔位百分位 (Score)
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    df['Score'] = (p(df['Close']) * 0.6) + (p(df['Close'].diff().rolling(14).mean()) * 0.4)
    
    df = calculate_supertrend(df)
    
    # 成交量過濾：當前量 > 過去 5 日平均量 1.5 倍
    df['Vol_MA5'] = df['Volume'].rolling(5).mean()
    df['Vol_Bump'] = df['Volume'] > (df['Vol_MA5'] * 1.5)
    
    # 【核心大波段買點】：趨勢轉多 + 檔位在低位(<60) + 成交量爆發
    df['Buy'] = np.where(
        (df['in_trend']==True) & (df['in_trend'].shift(1)==False) & 
        (df['Score'] < 60) & (df['Vol_Bump']==True), 
        df['Low']*0.95, np.nan
    )
    # 【大波段賣點】：趨勢轉空
    df['Sell'] = np.where((df['in_trend']==False) & (df['in_trend'].shift(1)==True), df['High']*1.05, np.nan)
    return df

# --- UI 介面 ---
st.title("🎯 大波段量化分析 V6.0")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號 (如: 2330)", value="2330")
    run_btn = st.button("啟動波段掃描")

if run_btn:
    hist_raw, info = fetch_data_robust(stock_input)
    
    if hist_raw is None:
        st.error("🚨 暫時無法獲取數據。請檢查網路或稍後重試。")
    else:
        df = process_wave_logic(hist_raw).tail(350)
        
        st.info(f"📊 **{info.get('longName', stock_input)}** 診斷：\n"
                "🔹 **藍色趨勢線**：只要股價在線上，波段就持續持有。\n"
                "🔹 **買入條件**：趨勢轉多 + 位階低 + 成交量放大。")

        # 繪圖
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{}]],
                           row_heights=[0.75, 0.25])

        # 主圖
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1, secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Trend_Line'], name="波段趨勢線", line=dict(color='#00e5ff', width=3)), row=1, col=1, secondary_y=False)
        
        # 買賣訊號
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="大波段啟動 ▲", mode='markers', marker=dict(symbol='triangle-up', size=18, color='#00ff00', line=dict(width=2, color='white'))), row=1, col=1, secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="趨勢轉弱 ▼", mode='markers', marker=dict(symbol='triangle-down', size=18, color='#ff4444', line=dict(width=2, color='white'))), row=1, col=1, secondary_y=False)

        # 檔位分數
        fig.add_trace(go.Scatter(x=df.index, y=df['Score'], name="技術檔位分數", line=dict(color='rgba(0, 255, 204, 0.4)', width=1.5), fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.05)'), row=1, col=1, secondary_y=True)

        # 成交量
        colors = ['#00ff88' if r['Close'] >= r['Open'] else '#ff4444' for i, r in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=colors), row=2, col=1)

        # 滑動與排除假日
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], rangeslider_visible=False, type='date')
        fig.update_layout(height=800, template="plotly_dark", hovermode="x unified", margin=dict(t=30, b=10))
        
        # 預設看最近一個月
        fig.update_xaxes(range=[df.index[-30], df.index[-1]])
        
        st.plotly_chart(fig, use_container_width=True)
