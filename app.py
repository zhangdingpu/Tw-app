import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面設定
st.set_page_config(page_title="動能大戶導航器", layout="wide")
st.title("🚀 大戶動能起漲診斷系統 (60MA + ADX + SuperTrend)")

# 2. 抗封鎖抓取
@st.cache_data(ttl=3600)
def fetch_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            df = yf.Ticker(f"{code}{suffix}").history(period="1y")
            if not df.empty: return df
        except: continue
    return pd.DataFrame()

# 3. 核心邏輯運算
def calculate_advanced_signals(df):
    # --- 指標計算 ---
    # A. 方向判斷：60MA 及其斜率 (取 3 天的差值)
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['MA60_Slope'] = df['MA60'].diff(3) 
    
    # B. 動能過濾：ADX (14)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1) # 包含 ADX_14, DMP_14, DMN_14
    
    # C. 進場點：SuperTrend (10, 4.0)
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=4.0)
    df = pd.concat([df, st_df], axis=1) # 包含 SUPERT_10_4.0, SUPERTd_10_4.0
    
    # D. 安全檢查：RSI (14)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # E. 力道確認：成交量
    df['Vol_MA5'] = df['Volume'].rolling(5).mean()
    
    return df

# --- UI 查詢 ---
stock_code = st.sidebar.text_input("輸入台股代號", value="2330")

if stock_input := stock_code:
    raw_df = fetch_data(stock_input)
    if not raw_df.empty:
        df = calculate_advanced_signals(raw_df).tail(150)
        
        # --- 判斷 5 大核心過濾條件 (做多) ---
        c1 = df['MA60_Slope'].iloc[-1] > 0               # 60MA 斜率向上
        c2 = df['ADX_14'].iloc[-1] > 25                 # ADX 動能強勁
        c3 = (df['SUPERTd_10_4.0'].iloc[-1] == 1) and (df['SUPERTd_10_4.0'].iloc[-2] == -1) # SuperTrend 轉綠首日
        c4 = df['Volume'].iloc[-1] > (df['Vol_MA5'].iloc[-1] * 1.5) # 量增 1.5 倍
        c5 = df['RSI'].iloc[-1] < 75                    # 未過熱
        
        # --- 繪圖區 ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                           row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        
        # 主圖: K線 + 60MA + SuperTrend
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="60MA (趨勢線)", line=dict(color='yellow', width=2.5)), row=1, col=1)
        
        # SuperTrend 背景顏色或線條
        st_line = df['SUPERT_10_4.0']
        st_color = ['lime' if d == 1 else 'red' for d in df['SUPERTd_10_4.0']]
        fig.add_trace(go.Scatter(x=df.index, y=st_line, name="SuperTrend", line=dict(color='rgba(0,255,0,0.5)', dash='dot')), row=1, col=1)

        # ADX 能量圖
        fig.add_trace(go.Scatter(x=df.index, y=df['ADX_14'], name="ADX 動能", line=dict(color='cyan', width=2)), row=2, col=1)
        fig.add_hline(y=25, line_dash="dash", line_color="white", row=2, col=1)

        # 成交量與 RSI
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color='gray'), row=3, col=1)
        
        fig.update_layout(height=900, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # --- 儀表板診斷 ---
        st.subheader("📊 關鍵過濾清單 (做多建議)")
        cols = st.columns(5)
        cols[0].metric("60MA 斜率向上", "✅" if c1 else "❌")
        cols[1].metric("ADX > 25", f"{df['ADX_14'].iloc[-1]:.1f}", delta="動能足" if c2 else "低迷")
        cols[2].metric("SuperTrend 轉向", "🔥 轉綠" if c3 else "維持")
        cols[3].metric("量能爆發", f"{df['Volume'].iloc[-1]/df['Vol_MA5'].iloc[-1]:.1f}x", delta="有大戶" if c4 else "一般")
        cols[4].metric("RSI 安全區", f"{df['RSI'].iloc[-1]:.1f}", delta="未過熱" if c5 else "過熱")

        if c1 and c2 and c3 and c4 and c5:
            st.balloons()
            st.success("🎯 五星全亮！符合大戶點火起漲條件，預期波段獲利目標 30%！")
        elif c3:
            st.warning("⚠️ SuperTrend 雖轉向，但其他動能或趨勢條件未全數達成，建議分批佈局。")

    else:
        st.error("查無數據，請稍後再試。")
