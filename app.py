import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import time

st.set_page_config(page_title="AI 趨勢評分系統", layout="wide")

@st.cache_data(ttl=3600)
def fetch_data_safe(code):
    time.sleep(random.uniform(0.5, 1.5))
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="2y", timeout=15) 
            if not df.empty: return df
        except: continue
    return pd.DataFrame()

def calculate_all_signals(df):
    df = df.copy()
    # 1. 指標運算
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['MA60_Slope'] = df['MA60'].diff(3)
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    st_data = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=4.0)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['Vol_MA5'] = df['Volume'].rolling(5).mean()
    df = pd.concat([df, adx, st_data], axis=1)
    
    # 2. AI 評分與評級
    scores, ratings = [], []
    for i in range(len(df)):
        if i < 60:
            scores.append(0); ratings.append("None")
            continue
        s, curr, prev = 0, df.iloc[i], df.iloc[i-1]
        if curr['MA60_Slope'] > 0: s += 20
        if curr['ADX_14'] > 25: s += 20
        if curr['SUPERTd_10_4.0'] == 1:
            s += 30
            if prev['SUPERTd_10_4.0'] == -1: s += 10
        if curr['Volume'] > (curr['Vol_MA5'] * 1.5): s += 15
        if 40 < curr['RSI'] < 75: s += 5
        scores.append(s)
        if curr['SUPERTd_10_4.0'] == 1:
            ratings.append("Strong Buy" if s >= 85 else "Buy" if s >= 65 else "Wait")
        else:
            ratings.append("Strong Sell" if s <= 25 else "Sell" if s <= 50 else "Wait")
            
    df['AI_Score'] = scores
    df['AI_Rating'] = ratings
    return df

# --- UI 介面 ---
st.title("🤖 AI 趨勢指標匯入系統")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

if stock_input:
    df_raw = fetch_data_safe(stock_input)
    if not df_raw.empty:
        df = calculate_all_signals(df_raw)
        last = df.iloc[-1]
        
        # 顯示目前的診斷評級
        st.subheader(f"📊 目前評級：{last['AI_Rating']}")
        
        # 指標詳情儀表板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("AI 總分", f"{int(last['AI_Score'])}")
        c2.metric("ADX 動能", f"{last['ADX_14']:.1f}")
        c3.metric("RSI 熱度", f"{last['RSI']:.1f}")
        c4.metric("量能倍率", f"{last['Volume']/last['Vol_MA5']:.1f}x")

        # 核心：主圖標註所有指標
        df_plot = df.tail(120) # 顯示最近半年
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
        
        # 1. K線圖
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="K線"), row=1, col=1)
        
        # 2. 匯入 60MA (黃線)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA60'], name="60MA (季線)", line=dict(color='yellow', width=2)), row=1, col=1)
        
        # 3. 匯入 SuperTrend (青色虛線)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SUPERT_10_4.0'], name="SuperTrend 軌道", line=dict(color='cyan', dash='dot', width=1)), row=1, col=1)
        
        # 4. 強烈買入訊號 (綠色箭頭)
        buy_sig = df_plot[df_plot['AI_Rating'] == "Strong Buy"]
        fig.add_trace(go.Scatter(x=buy_sig.index, y=buy_sig['Low'] * 0.97, mode='markers', marker=dict(symbol='triangle-up', size=12, color='#00ff00'), name='🔥 強烈買入'), row=1, col=1)
        
        # 5. 強烈賣出訊號 (紅色箭頭)
        sell_sig = df_plot[df_processed['AI_Rating'] == "Strong Sell"] if 'df_processed' not in locals() else df_plot[df['AI_Rating'] == "Strong Sell"]
        fig.add_trace(go.Scatter(x=sell_sig.index, y=sell_sig['High'] * 1.03, mode='markers', marker=dict(symbol='triangle-down', size=12, color='#ff0000'), name='💀 強烈賣出'), row=1, col=1)

        # 6. 成交量圖
        vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df_plot['Close'], df_plot['Open'])]
        fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

        # 顯示歷史戰績 (最近 3 次)
        with st.expander("📈 查看前 3 次「強烈買入」至「賣出」漲幅統計", expanded=True):
            # (這裡放你剛才的回測邏輯函數)
            st.info("數據已更新，請向上滾動查看儀表板細節。")
    else:
        st.error("資料抓取失敗。")
