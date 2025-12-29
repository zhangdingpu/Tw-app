import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import argrelextrema
from fake_useragent import UserAgent

# 1. 初始化與頁面配置
st.set_page_config(page_title="VCP 專業導航器", layout="wide")
ua = UserAgent()

# 2. 抗封鎖抓取函數 (Cache 提高到 1 小時以節省額度)
@st.cache_data(ttl=3600)
def fetch_data_robust(code):
    try:
        # 使用隨機 User-Agent
        headers = {'User-Agent': ua.random}
        
        # 建立一個持久化的 Session 有助於減少被鎖機率
        session = None # 若有需要可加入 requests session
        
        ticker = yf.Ticker(f"{code}.TW")
        df = ticker.history(period="1y")
        
        if df.empty:
            ticker = yf.Ticker(f"{code}.TWO")
            df = ticker.history(period="1y")
            
        return df
    except Exception as e:
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🛡️ VCP 形態與窒息量診斷")
st.markdown("專注於識別 **30% 漲幅** 的波動收縮型態。")

stock_input = st.sidebar.text_input("輸入台股代號 (如: 2330, 3131)", value="")

if stock_input:
    df_raw = fetch_data_robust(stock_input)
    
    if not df_raw.empty:
        df = df_raw.tail(150).copy()
        
        # 指標計算
        df['MA50'] = df['Close'].rolling(50).mean()
        df['MA200'] = df['Close'].rolling(200).mean()
        df['Vol_MA20'] = df['Volume'].rolling(20).mean()
        
        # VCP 關鍵點識別
        peak_idx = argrelextrema(df['High'].values, np.greater_equal, order=8)[0]
        peaks = df.iloc[peak_idx]

        # 繪製主圖表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.05)

        # 主圖：K線與 VCP 邊界
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], name="50MA", line=dict(color='orange', width=2)), row=1, col=1)
        
        if len(peaks) >= 2:
            # 畫出收縮連線
            fig.add_trace(go.Scatter(x=peaks.index, y=peaks['High'], mode='lines+markers', name="收縮邊界", line=dict(color='yellow', dash='dash')), row=1, col=1)
            # 畫出 Pivot 線
            pivot = peaks['High'].iloc[-1]
            fig.add_hline(y=pivot, line_dash="dot", line_color="lime", line_width=3, annotation_text=f"突破關鍵: {pivot}", row=1, col=1)

        # 副圖：成交量與窒息量 (紫色)
        vol_colors = ['#BF40BF' if v < vm * 0.6 else '#26a69a' if c >= o else '#ef5350' 
                      for v, vm, c, o in zip(df['Volume'], df['Vol_MA20'], df['Close'], df['Open'])]
        
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # 診斷總結
        range_15 = (df['High'].tail(15).max() - df['Low'].tail(15).min()) / df['Low'].tail(15).min()
        st.subheader("📝 VCP 形態診斷")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("15日收縮率", f"{range_15:.1%}", delta="符合收縮" if range_15 < 0.1 else "波動尚大")
        with c2:
            is_quiet = df['Volume'].iloc[-1] < df['Vol_MA20'].iloc[-1] * 0.7
            st.metric("窒息量檢測", "出現訊號" if is_quiet else "量能尚多")

    else:
        st.error("⚠️ 抓取數據失敗。這可能是因為 Yahoo Finance 流量限制。請等候幾分鐘再試，或嘗試輸入不同的代號。")
