import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import argrelextrema

def get_vcp_plot(df, code):
    df = df.tail(120).copy() # 取最近半年
    
    # 1. 尋找局部高點 (用來畫收縮趨勢線)
    # order=5 代表左右各 5 天內最高
    n = 5 
    df['Max'] = df['High'].iloc[argrelextrema(df['High'].values, np.greater_equal, order=n)[0]]
    df['Min'] = df['Low'].iloc[argrelextrema(df['Low'].values, np.less_equal, order=n)[0]]
    
    peaks = df.dropna(subset=['Max'])
    troughs = df.dropna(subset=['Min'])

    # 2. 建立繪圖
    fig = go.Figure()
    
    # K線圖
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"))
    
    # 均線 (VCP 必須是多頭排列)
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(50).mean(), name="50MA", line=dict(color='orange', width=1.5)))
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(200).mean(), name="200MA", line=dict(color='red', width=1.5)))

    # 3. 自動畫出收縮邊界 (VCP 趨勢線)
    if len(peaks) >= 2:
        # 連接最近兩個高點
        fig.add_trace(go.Scatter(x=peaks.index[-3:], y=peaks['Max'].iloc[-3:], 
                                 mode='lines+markers', name="收縮邊界", 
                                 line=dict(color='yellow', dash='dash')))
        
        # 4. 自動畫出 Pivot 突破線 (最近一個高點的水平線)
        pivot_price = peaks['Max'].iloc[-1]
        fig.add_hline(y=pivot_price, line_dash="dot", line_color="lime", line_width=2,
                      annotation_text=f"Pivot: {pivot_price:.1f}", annotation_position="top right")

    # 5. 成交量 (VCP 重視成交量縮小)
    vol_colors = ['green' if df['Close'].iloc[i] > df['Open'].iloc[i] else 'red' for i in range(len(df))]
    
    fig.update_layout(
        title=f"📊 {code} VCP 型態自動分析 (自動識別收縮區與突破點)",
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )
    
    return fig

# --- Streamlit UI ---
st.set_page_config(page_title="VCP 自動繪圖系統", layout="wide")
st.sidebar.title("🦅 VCP 形態導航")
code = st.sidebar.text_input("輸入台股代號", "2330")

if st.sidebar.button("分析並繪製 VCP"):
    hist = yf.Ticker(f"{code}.TW").history(period="1y")
    if not hist.empty:
        fig = get_vcp_plot(hist, code)
        st.plotly_chart(fig, use_container_width=True)
        
        # 顯示收縮資訊
        highs = hist['High'].tail(60)
        lows = hist['Low'].tail(60)
        total_range = (highs.max() - lows.min()) / lows.min()
        st.write(f"📈 **當前 60 日最大震幅**：{total_range:.2%}")
        if total_range < 0.15:
            st.success("✅ 波動已極度收縮，隨時準備迎接 30%+ 暴力突破！")
        else:
            st.info("⌛ 波動仍大，持續等待波段收縮...")
