import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import time

# 1. 頁面配置與極簡 CSS
st.set_page_config(page_title="AI 決策導航", layout="wide")
st.markdown("""
    <style>
    .big-font { font-size:30px !important; font-weight: bold; text-align: center; }
    .decision-box { border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 抗封鎖抓取
@st.cache_data(ttl=3600)
def fetch_data_safe(code):
    time.sleep(random.uniform(0.5, 1.0))
    for suffix in [".TW", ".TWO"]:
        try:
            df = yf.Ticker(f"{code}{suffix}").history(period="2y", timeout=15)
            if not df.empty: return df
        except: continue
    return pd.DataFrame()

# 3. 邏輯運算
def calculate_all_signals(df):
    df = df.copy()
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['MA60_Slope'] = df['MA60'].diff(3)
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    st_data = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=4.0)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['Vol_MA5'] = df['Volume'].rolling(5).mean()
    df = pd.concat([df, adx, st_data], axis=1)
    
    scores, ratings = [], []
    for i in range(len(df)):
        if i < 60: scores.append(0); ratings.append("None"); continue
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
            ratings.append("強烈買入" if s >= 85 else "買入" if s >= 65 else "持股/觀望")
        else:
            ratings.append("強烈賣出" if s <= 25 else "賣出" if s <= 50 else "空手/觀望")
    df['AI_Score'], df['AI_Rating'] = scores, ratings
    return df

# --- UI 介面 ---
with st.sidebar:
    stock_input = st.text_input("輸入代號", value="2330")
    if st.button("🔄 刷新"): st.cache_data.clear(); st.rerun()

if stock_input:
    df_raw = fetch_data_safe(stock_input)
    if not df_raw.empty:
        df = calculate_all_signals(df_raw)
        last = df.iloc[-1]
        
        # 🟢 第一眼決策大燈
        rating = last['AI_Rating']
        if "買入" in rating:
            bg_color, icon = "#004d00", "🚀"
        elif "賣出" in rating:
            bg_color, icon = "#4d0000", "⚠️"
        else:
            bg_color, icon = "#333300", "⏳"
            
        st.markdown(f"""
            <div class="decision-box" style="background-color: {bg_color}; border: 2px solid white;">
                <p style="color: white; font-size: 20px; margin-bottom: 5px;">AI 綜合診斷建議</p>
                <h1 style="color: white; margin-top: 0px;">{icon} {rating}</h1>
                <p style="color: #cccccc;">AI 綜合評分：{int(last['AI_Score'])} 分</p>
            </div>
            """, unsafe_allow_html=True)

        # 📊 關鍵指標紅綠燈 (手機橫向排列)
        c1, c2, c3 = st.columns(3)
        c1.metric("動能 (ADX)", f"{last['ADX_14']:.1f}", delta="強" if last['ADX_14']>25 else "弱")
        c2.metric("熱度 (RSI)", f"{last['RSI']:.1f}", delta="過熱" if last['RSI']>75 else "正常", delta_color="inverse")
        c3.metric("趨勢 (60MA)", "向上" if last['MA60_Slope']>0 else "向下")

        # 📈 精簡圖表 (隱藏不必要的座標與縮放)
        df_plot = df.tail(100)
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="K線"))
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA60'], name="趨勢線", line=dict(color='yellow', width=2)))
        
        # 只顯示最近的買賣訊號，避免圖面太髒
        buy_sig = df_plot[df_plot['AI_Rating'] == "強烈買入"]
        sell_sig = df_plot[df_plot['AI_Rating'] == "強烈賣出"]
        fig.add_trace(go.Scatter(x=buy_sig.index, y=buy_sig['Low']*0.97, mode='markers', marker=dict(symbol='triangle-up', size=15, color='#00ff00'), name='買入'))
        fig.add_trace(go.Scatter(x=sell_sig.index, y=sell_sig['High']*1.03, mode='markers', marker=dict(symbol='triangle-down', size=15, color='#ff0000'), name='賣出'))

        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # 📝 歷史戰績回測 (縮小放置於下方)
        with st.expander("📊 點擊查看歷史勝率統計"):
            # ... (保留前述的回測邏輯與表格呈現)
            st.write("歷史回測僅供參考，不代表未來績效。")
