import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fake_useragent import UserAgent

st.set_page_config(page_title="AI 趨勢評分導航器", layout="wide")
ua = UserAgent()

@st.cache_data(ttl=3600)
def fetch_data(code):
    try:
        headers = {'User-Agent': ua.random}
        ticker = yf.Ticker(f"{code}.TW")
        df = ticker.history(period="1y")
        if df.empty:
            df = yf.Ticker(f"{code}.TWO").history(period="1y")
        return df
    except: return pd.DataFrame()

def get_rating(score, st_trend):
    if st_trend == 1: # SuperTrend 多頭
        if score >= 85: return "🔥 強烈買入 (Strong Buy)", "success"
        if score >= 60: return "✅ 買入 (Buy)", "info"
        return "⏳ 觀望 (Wait/Hold)", "warning"
    else: # SuperTrend 空頭
        if score <= 20: return "💀 強烈賣出 (Strong Sell)", "error"
        if score <= 45: return "⚠️ 賣出 (Sell)", "error"
        return "⏳ 觀望 (Wait/Hold)", "warning"

# --- UI ---
st.title("🤖 AI 綜合量化評分系統")
code = st.sidebar.text_input("輸入台股代號", "2330")

if code:
    raw_df = fetch_data(code)
    if not raw_df.empty:
        df = raw_df.copy()
        # 1. 指標計算
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['MA60_Slope'] = df['MA60'].diff(3)
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        st_data = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=4.0)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['Vol_MA5'] = df['Volume'].rolling(5).mean()
        
        df = pd.concat([df, adx, st_data], axis=1)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # 2. AI 評分邏輯 (總分 100)
        score = 0
        if last['MA60_Slope'] > 0: score += 20 # 趨勢向上
        if last['ADX_14'] > 25: score += 20    # 動能足夠
        if last['SUPERTd_10_4.0'] == 1: 
            score += 30                        # 多頭波段中
            if prev['SUPERTd_10_4.0'] == -1: score += 10 # 轉折首日加分
        if last['Volume'] > (last['Vol_MA5'] * 1.5): score += 15 # 大戶點火
        if 40 < last['RSI'] < 75: score += 5   # 健康區間

        rating, status_color = get_rating(score, last['SUPERTd_10_4.0'])

        # --- 顯示區 ---
        st.subheader(f"📊 {code} 綜合分析報告")
        
        if status_color == "success": st.success(f"評級：{rating}")
        elif status_color == "info": st.info(f"評級：{rating}")
        elif status_color == "warning": st.warning(f"評級：{rating}")
        else: st.error(f"評級：{rating}")

        # 指標儀表板
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("AI 總分", f"{score} 分")
        c2.metric("ADX 動能", f"{last['ADX_14']:.1f}")
        c3.metric("RSI 指數", f"{last['RSI']:.1f}")
        c4.metric("量能倍率", f"{last['Volume']/last['Vol_MA5']:.1f}x")
        c5.metric("60MA 斜率", "↑" if last['MA60_Slope'] > 0 else "↓")

        # 圖表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="60MA", line=dict(color='yellow')), row=1, col=1)
        
        st_line = df['SUPERT_10_4.0']
        fig.add_trace(go.Scatter(x=df.index, y=st_line, name="SuperTrend", line=dict(color='cyan', dash='dot')), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color='gray'), row=2, col=1)

        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 3. 操作建議
        st.write("### 📝 AI 決策建議")
        if rating.startswith("🔥 強烈買入"):
            st.write("📌 **分析**：目前處於強勢起漲點。季線向上且 ADX 顯示趨勢極強，伴隨成交量放大，是標準的 **30% 波段起手式**。")
        elif rating.startswith("✅ 買入"):
            st.write("📌 **分析**：趨勢已轉多，但動能或量能稍欠臨門一腳，建議分批佈局。")
        elif rating.startswith("💀 強烈賣出"):
            st.write("📌 **分析**：SuperTrend 已轉紅且 60MA 斜率向下，建議全面撤退，保護本金。")
        else:
            st.write("📌 **分析**：目前指標互有矛盾，或處於無趨勢狀態，建議觀望直到 SuperTrend 變色或 ADX 轉強。")
