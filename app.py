import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from fake_useragent import UserAgent

# 1. 頁面配置
st.set_page_config(page_title="VCP 個股導航系統", layout="wide")
ua = UserAgent()

# 2. 抗封鎖抓取函數 (加入快取與隨機 Header)
@st.cache_data(ttl=600) # 快取 10 分鐘，兼顧準確度與防封鎖
def fetch_stock_data(code):
    try:
        headers = {'User-Agent': ua.random}
        # 嘗試上市代號
        ticker = yf.Ticker(f"{code}.TW")
        df = ticker.history(period="1y")
        # 若上市查無資料，嘗試上櫃代號
        if df.empty:
            ticker = yf.Ticker(f"{code}.TWO")
            df = ticker.history(period="1y")
        return df
    except:
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🦅 VCP 專業型態診斷儀表板")
st.markdown("針對 **30% 以上大波段** 設計，自動識別波動收縮與窒息量。")

# 側邊欄輸入
with st.sidebar:
    st.header("個股查詢")
    stock_code = st.text_input("輸入台股代號 (如: 2330, 3131)", value="2330")
    st.info("💡 提示：VCP 適合找尋橫盤收縮後的突破點。")

if stock_code:
    df_raw = fetch_stock_data(stock_code)
    
    if not df_raw.empty:
        # 取最近 150 天進行分析
        df = df_raw.tail(150).copy()
        
        # 1. 計算均線
        df['MA50'] = df['Close'].rolling(50).mean()
        df['MA200'] = df['Close'].rolling(200).mean()
        df['Vol_MA20'] = df['Volume'].rolling(20).mean()
        
        # 2. 尋找 VCP 收縮高點 (Pivot)
        # order 越大越能抓出大波段的轉折高點
        peak_idx = argrelextrema(df['High'].values, np.greater_equal, order=10)[0]
        peaks = df.iloc[peak_idx]

        # 3. 繪製主圖表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           row_heights=[0.75, 0.25], vertical_spacing=0.05)

        # K線與均線
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                     low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], name="50MA", line=dict(color='orange', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="200MA", line=dict(color='red', width=2)), row=1, col=1)

        # 繪製 VCP 收縮趨勢線
        if len(peaks) >= 2:
            fig.add_trace(go.Scatter(x=peaks.index, y=peaks['High'], mode='lines+markers',
                                     name="收縮邊界", line=dict(color='yellow', dash='dash', width=2)), row=1, col=1)
            
            # Pivot 突破線 (最近一個收縮高點)
            pivot_price = peaks['High'].iloc[-1]
            fig.add_hline(y=pivot_price, line_dash="dot", line_color="lime", line_width=3,
                          annotation_text=f"VCP 突破臨界點: {pivot_price}", annotation_position="top right", row=1, col=1)

        # 4. 成交量圖表 (紫色窒息量提醒)
        # 窒息量定義：今日成交量 < 20日均量 * 0.6
        vol_colors = []
        for i in range(len(df)):
            v = df['Volume'].iloc[i]
            vm = df['Vol_MA20'].iloc[i]
            if v < vm * 0.6:
                vol_colors.append('#BF40BF') # 紫色：窒息量 (V-Stop)
            elif df['Close'].iloc[i] >= df['Open'].iloc[i]:
                vol_colors.append('#26a69a') # 綠色
            else:
                vol_colors.append('#ef5350') # 紅色

        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # 5. 形態強度診斷
        st.subheader("📝 形態診斷報告")
        col1, col2, col3 = st.columns(3)
        
        # 波動收縮率
        recent_h = df['High'].tail(15).max()
        recent_l = df['Low'].tail(15).min()
        narrowness = (recent_h - recent_l) / recent_l
        
        with col1:
            st.metric("15日波動幅度", f"{narrowness:.1%}", delta="符合收縮" if narrowness < 0.1 else "波動尚大")
        with col2:
            trend_ok = df['Close'].iloc[-1] > df['MA50'].iloc[-1] > df['MA200'].iloc[-1]
            st.metric("趨勢模板", "強勢多頭" if trend_ok else "整理中")
        with col3:
            last_vol_quiet = df['Volume'].iloc[-1] < df['Vol_MA20'].iloc[-1] * 0.7
            st.metric("量能狀態", "出現窒息量" if last_vol_quiet else "量能正常")

        if narrowness < 0.1 and trend_ok:
            st.balloons()
            st.success("🔥 警告：該股已具備 VCP 起漲特徵，隨時注意帶量突破 Pivot 線！")

    else:
        st.error("無法取得數據，請檢查代號是否正確。")

from plotly.subplots import make_subplots
