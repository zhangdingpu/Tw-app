import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面風格
st.set_page_config(page_title="量化選股 V4.0 - 低買高賣邏輯版", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    h1, h2, h3 { color: #00FFCC !important; font-weight: 800; }
    .stInfo { background-color: #112233; border: 1px solid #00FFCC; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. 數據抓取與緩存
@st.cache_data(ttl=3600)
def fetch_data(code):
    for suffix in [".TW", ".TWO"]:
        ticker = yf.Ticker(f"{code}{suffix}")
        hist = ticker.history(period="3y")
        if not hist.empty:
            return hist, ticker.info
    return None, None

# 3. 核心指標計算 (改用布林通道與位階過濾)
def calculate_advanced_metrics(hist):
    df = hist.copy()
    
    # 技術指標基礎
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + gain/loss))
    
    # 布林通道 (20, 2)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (2 * df['STD'])
    df['Lower'] = df['MA20'] - (2 * df['STD'])
    
    # 歷史百分位檔位計算 (0-100)
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    df['Score'] = (p(df['RSI']) * 0.5) + (p(df['Close'].rolling(20).apply(lambda x: (x[-1]-x.mean())/x.std() if x.std() != 0 else 0)) * 0.5)
    
    # --- [核心修改] 買賣決策邏輯 ---
    # 買入：分數低於 40(便宜) 且 股價站上中軌(轉強)
    df['Buy'] = np.where(
        (df['Score'] < 40) & (df['Close'] > df['MA20']) & (df['Close'].shift(1) <= df['MA20'].shift(1)),
        df['Low'] * 0.97, np.nan
    )
    
    # 賣出：分數高於 70(過熱) 且 股價跌破布林上軌(轉弱)
    df['Sell'] = np.where(
        (df['Score'] > 70) & (df['Close'] < df['Upper']) & (df['Close'].shift(1) >= df['Upper'].shift(1)),
        df['High'] * 1.03, np.nan
    )
    
    return df

# --- UI 介面 ---
st.title("🎯 量化選股 V4.0 (位階轉折版)")

with st.sidebar:
    stock_code = st.text_input("輸入台股代號", value="2330")
    start_btn = st.button("啟動高低位分析")

if start_btn:
    hist_raw, info = fetch_data(stock_code)
    
    if hist_raw is None:
        st.error("數據抓取失敗，請檢查代號。")
    else:
        df = calculate_advanced_metrics(hist_raw).tail(300)
        
        # 解釋文字移至上方
        st.info(f"📊 **{info.get('longName', stock_code)}** 決策指南：\n"
                "🔹 **綠色▲ 買入**：技術檔位在**低位(便宜區)**且股價站上月線，代表起漲點。\n"
                "🔹 **紅色▼ 賣出**：技術檔位在**高位(過熱區)**且股價脫離強勢區，代表獲利點。\n"
                "🔹 **中間青色線**：布林中軌(月線)，股價之上看多，之下看空。")

        # 繪製圖表
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 1. K 線圖
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="K線", increasing_line_color='#00ff88', decreasing_line_color='#ff4444'
        ), secondary_y=False)

        # 2. 布林通道 (輔助視覺)
        fig.add_trace(go.Scatter(x=df.index, y=df['Upper'], name="布林上軌", line=dict(color='rgba(255,255,255,0.2)', dash='dot')), secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="布林中軌(月線)", line=dict(color='cyan', width=1.5)), secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Lower'], name="布林下軌", line=dict(color='rgba(255,255,255,0.2)', dash='dot')), secondary_y=False)

        # 3. 修正後的買賣訊號
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="低位買入 ▲", mode='markers', marker=dict(symbol='triangle-up', size=15, color='#00ff00', line=dict(width=1, color='white'))), secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="高位賣出 ▼", mode='markers', marker=dict(symbol='triangle-down', size=15, color='#ff0000', line=dict(width=1, color='white'))), secondary_y=False)

        # 4. 技術檔位分數 (副軸)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Score'], name="技術檔位分數",
            line=dict(color='rgba(0, 255, 204, 0.6)', width=2),
            fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.1)'
        ), secondary_y=True)

        # 互動與縮放優化
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], rangeslider_visible=True, type='date')
        fig.update_layout(
            height=750, template="plotly_dark", hovermode="x unified",
            yaxis_title="股價 (TWD)", yaxis2=dict(title="檔位分數 (0-100)", range=[0, 105], side="right", showgrid=False),
            legend=dict(orientation="h", y=1.05)
        )
        # 預設顯示最近一個月
        fig.update_xaxes(range=[df.index[-30], df.index[-1]])

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
