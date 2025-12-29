import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎風格
st.set_page_config(page_title="量化選股 V5.0 大波段版", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    h1, h2, h3 { color: #00FFCC !important; font-weight: 800; }
    .stInfo { background-color: #0E1117; border: 1px solid #00FFCC; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. 數據抓取 (含快取機制)
@st.cache_data(ttl=3600)
def fetch_data(code):
    for suffix in [".TW", ".TWO"]:
        ticker = yf.Ticker(f"{code}{suffix}")
        hist = ticker.history(period="3y")
        if not hist.empty:
            return hist, ticker.info
    return None, None

# 3. 超級趨勢 SuperTrend 計算函數
def calculate_supertrend(df, period=10, multiplier=3):
    df = df.copy()
    hl2 = (df['High'] + df['Low']) / 2
    # ATR 計算
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['Close'].shift(1)), 
               abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(period).mean()
    
    # 基本軌道
    df['upperband'] = hl2 + (multiplier * df['ATR'])
    df['lowerband'] = hl2 - (multiplier * df['ATR'])
    df['in_trend'] = True

    # 疊代計算趨勢線
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
    
    # 生成繪圖用的趨勢線
    df['Trend_Line'] = np.where(df['in_trend'], df['lowerband'], df['upperband'])
    return df

# 4. 指標整合計算
def calculate_all_metrics(hist):
    # 技術檔位百分位 (RSI + 價格相對位置)
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    hist['RSI'] = 100 - (100 / (1 + gain/loss))
    
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    hist['Score'] = (p(hist['RSI']) * 0.5) + (p(hist['Close']) * 0.5)
    
    # 計算 SuperTrend
    hist = calculate_supertrend(hist)
    
    # 大波段買賣邏輯
    # 買入：趨勢線轉多(綠色) 且 分數在低位 (< 50)
    hist['Buy'] = np.where(
        (hist['in_trend'] == True) & (hist['in_trend'].shift(1) == False) & (hist['Score'] < 50),
        hist['Low'] * 0.95, np.nan
    )
    # 賣出：趨勢線轉空(紅色)
    hist['Sell'] = np.where(
        (hist['in_trend'] == False) & (hist['in_trend'].shift(1) == True),
        hist['High'] * 1.05, np.nan
    )
    return hist

# --- UI 介面 ---
st.title("🎯 大波段量化選股系統 V5.0")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    run_btn = st.button("啟動大波段分析")

if run_btn:
    raw_data, info = fetch_data(stock_input)
    if raw_data is None:
        st.error("代號錯誤或 Yahoo 服務繁忙")
    else:
        df = calculate_all_metrics(raw_data).tail(300)
        
        st.info(f"📊 **{info.get('longName', stock_input)}** 波段診斷：\n"
                "🔹 **波段防守線**：圖中隨股價移動的藍色/紫色線。線在下方為多頭，線在上方為空頭。\n"
                "🔹 **策略動作**：只要趨勢線不變紅，大波段就持續持有。")

        # 建立多子圖 (主圖佔 70%，成交量佔 30%)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05, specs=[[{"secondary_y": True}], [{}]],
                           row_heights=[0.7, 0.3])

        # 1. K 線圖
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="K線", increasing_line_color='#00ff88', decreasing_line_color='#ff4444'
        ), row=1, col=1, secondary_y=False)

        # 2. SuperTrend 趨勢線
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Trend_Line'], name="波段趨勢線",
            line=dict(color='rgba(0, 229, 255, 0.8)', width=2, dash='solid')
        ), row=1, col=1, secondary_y=False)

        # 買賣訊號
        fig.add_trace(go.Scatter(x=df.index, y=df['Buy'], name="大波段買入 ▲", mode='markers', marker=dict(symbol='triangle-up', size=16, color='#00FF00', line=dict(width=1, color='white'))), row=1, col=1, secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Sell'], name="波段結束 ▼", mode='markers', marker=dict(symbol='triangle-down', size=16, color='#FF0000', line=dict(width=1, color='white'))), row=1, col=1, secondary_y=False)

        # 3. 技術檔位分數 (副軸)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Score'], name="檔位分數 (0-100)",
            line=dict(color='rgba(255, 255, 255, 0.3)', width=1.5),
            fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.05)'
        ), row=1, col=1, secondary_y=True)

        # 4. 成交量圖 (下方子圖)
        colors = ['#00ff88' if row['Close'] >= row['Open'] else '#ff4444' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=colors), row=2, col=1)

        # 介面優化
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], rangeslider_visible=False, type='date')
        fig.update_layout(
            height=850, template="plotly_dark", hovermode="x unified",
            yaxis_title="股價 (TWD)", yaxis2=dict(range=[0, 105], showgrid=False),
            legend=dict(orientation="h", y=1.05)
        )
        # 初始顯示最近三個月
        fig.update_xaxes(range=[df.index[-60], df.index[-1]])

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
