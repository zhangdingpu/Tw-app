import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import random

# 1. 頁面風格
st.set_page_config(page_title="量化選股 Pro - 穩定波段版", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    h1, h2, h3 { color: #00FFCC !important; font-weight: 800; }
    .stInfo { background-color: #0E1117; border: 1px solid #00FFCC; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. 數據抓取：增加抗封鎖邏輯
@st.cache_data(ttl=7200) # 延長快取至 2 小時
def fetch_data_stable(code):
    suffixes = [".TW", ".TWO"]
    # 模擬瀏覽器標頭
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    
    for suffix in suffixes:
        full_code = f"{code}{suffix}"
        try:
            ticker = yf.Ticker(full_code)
            # 使用隨機標頭與延遲防止被封
            time.sleep(random.uniform(0.5, 1.5)) 
            hist = ticker.history(period="3y", proxy=None)
            
            if not hist.empty:
                return hist, ticker.info
        except Exception as e:
            if "RateLimitError" in str(e):
                st.warning(f"偵測到請求頻繁，正在嘗試繞過限制...")
                time.sleep(2)
            continue
    return None, None

# 3. 超級趨勢 SuperTrend (大波段核心)
def calculate_supertrend(df, period=10, multiplier=3):
    df = df.copy()
    hl2 = (df['High'] + df['Low']) / 2
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

# 4. 指標整合
def process_indicators(hist):
    df = hist.copy()
    # 技術檔位百分位
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    # 使用收盤價與 RSI 綜合評分
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain/loss))
    df['Score'] = (p(df['RSI']) * 0.4) + (p(df['Close']) * 0.6)
    
    df = calculate_supertrend(df)
    
    # 訊號：低位階轉強
    df['Buy'] = np.where((df['in_trend']==True) & (df['in_trend'].shift(1)==False) & (df['Score'] < 55), df['Low']*0.96, np.nan)
    df['Sell'] = np.where((df['in_trend']==False) & (df['in_trend'].shift(1)==True), df['High']*1.04, np.nan)
    return df

# --- UI ---
st.title("🎯 大波段量化選股 V5.2 (穩定升級版)")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號 (如: 2330)", value="2330")
    run_btn = st.button("執行全維度分析")

if run_btn:
    hist_raw, info = fetch_data_stable(stock_input)
    
    if hist_raw is None:
        st.error("🚨 暫時無法獲取數據。這通常是 Yahoo Finance 限制了存取 IP。請等待 1-2 分鐘後重試，或嘗試查詢不同股票。")
    else:
        df = process_indicators(hist_raw).tail(300)
        
        st.info(f"📊 **{info.get('longName', stock_input)}** 波段診斷表")
        
        # 建立圖表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.08, specs=[[{"secondary_y": True}], [{}]],
                           row_heights=[0.75, 0.25])

        # 主圖：K線與趨勢
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1, secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Trend_Line'], name="趨勢防守線", line=dict(color='#00e5ff', width=2)), row=1, col=1, secondary_y=False)
        
        # 買賣點
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="波段起點 ▲", mode='markers', marker=dict(symbol='triangle-up', size=15, color='#00ff00')), row=1, col=1, secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="波段結束 ▼", mode='markers', marker=dict(symbol='triangle-down', size=15, color='#ff0000')), row=1, col=1, secondary_y=False)

        # 檔位分數
        fig.add_trace(go.Scatter(x=df.index, y=df['Score'], name="技術檔位分數", line=dict(color='rgba(255,255,255,0.4)', width=1), fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.05)'), row=1, col=1, secondary_y=True)

        # 成交量
        colors = ['#00ff88' if r['Close'] >= r['Open'] else '#ff4444' for i, r in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=colors), row=2, col=1)

        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], rangeslider_visible=False)
        fig.update_layout(height=800, template="plotly_dark", hovermode="x unified", margin=dict(t=30, b=10))
        fig.update_xaxes(range=[df.index[-50], df.index[-1]])
        
        st.plotly_chart(fig, use_container_width=True)

st.caption("提示：若頻繁出現錯誤，建議部署在私有伺服器或使用固定 IP。")
