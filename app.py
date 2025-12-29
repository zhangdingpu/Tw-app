import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import time

# 1. 頁面配置
st.set_page_config(page_title="AI 趨勢評分導航器 V15.0", layout="wide")

# 2. 抗封鎖抓取函數 (Cache 提高到 1 小時以節省請求次數)
@st.cache_data(ttl=3600)
def fetch_data_safe(code):
    # 模擬隨機等待，降低被偵測機率
    time.sleep(random.uniform(0.5, 1.5))
    
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            # 增加 timeout 避免伺服器卡死
            df = ticker.history(period="1y", timeout=15)
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()

# 3. AI 評級邏輯
def get_ai_rating(score, st_trend):
    if st_trend == 1: # SuperTrend 多頭區
        if score >= 85: return "🔥 強烈買入 (Strong Buy)", "success"
        if score >= 65: return "✅ 買入 (Buy)", "info"
        return "⏳ 觀望 (Wait/Hold)", "warning"
    else: # SuperTrend 空頭區
        if score <= 25: return "💀 強烈賣出 (Strong Sell)", "error"
        if score <= 50: return "⚠️ 賣出 (Sell)", "error"
        return "⏳ 觀望 (Wait/Hold)", "warning"

# --- UI 介面 ---
st.title("🤖 AI 綜合量化評分系統")
st.markdown("本系統整合：**60MA 斜率、ADX 動能、SuperTrend 趨勢、成交量爆發、RSI 避險**。")

# 側邊欄設定
with st.sidebar:
    st.header("🔍 個股診斷選單")
    stock_input = st.text_input("輸入台股代號 (如: 2330, 3131)", value="2330")
    st.write("---")
    if st.button("🔄 強制刷新數據"):
        st.cache_data.clear()
        st.rerun()

if stock_input:
    with st.spinner(f'正在分析 {stock_input} ...'):
        df_raw = fetch_data_safe(stock_input)
        
        if not df_raw.empty:
            df = df_raw.copy()
            
            # --- 指標運算 (pandas-ta) ---
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['MA60_Slope'] = df['MA60'].diff(3) # 三日斜率
            
            # ADX (14)
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            # SuperTrend (10, 4.0) - 此參數較穩定，適合大波段
            st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=4.0)
            # RSI (14)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            # 成交量均線
            df['Vol_MA5'] = df['Volume'].rolling(5).mean()
            
            df = pd.concat([df, adx_df, st_df], axis=1)
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # --- AI 評分邏輯 (滿分 100) ---
            score = 0
            # 1. 趨勢分 (20%): 60MA 斜率向上
            if last['MA60_Slope'] > 0: score += 20
            # 2. 動能分 (20%): ADX > 25
            if last['ADX_14'] > 25: score += 20
            # 3. 轉折分 (40%): SuperTrend 狀態
            if last['SUPERTd_10_4.0'] == 1:
                score += 30 # 在多頭軌道上
                if prev['SUPERTd_10_4.0'] == -1: score += 10 # 轉折第一天加分
            # 4. 力道分 (15%): 成交量爆發
            if last['Volume'] > (last['Vol_MA5'] * 1.5): score += 15
            # 5. 安全分 (5%): RSI 未過熱 (40-75)
            if 40 < last['RSI'] < 75: score += 5

            # 取得評級與顏色
            rating_text, status_type = get_ai_rating(score, last['SUPERTd_10_4.0'])

            # --- 畫面呈現 ---
            # 評級看板
            if status_type == "success": st.success(f"### 綜合評級：{rating_text}")
            elif status_type == "info": st.info(f"### 綜合評級：{rating_text}")
            elif status_type == "warning": st.warning(f"### 綜合評級：{rating_text}")
            else: st.error(f"### 綜合評級：{rating_text}")

            # 數據儀表板 (手機適應版)
            c1, c2, c3 = st.columns(3)
            c1.metric("AI 總分", f"{score} 分")
            c2.metric("ADX (動能)", f"{last['ADX_14']:.1f}")
            c3.metric("RSI (熱度)", f"{last['RSI']:.1f}")
            
            c4, c5 = st.columns(2)
            c4.metric("成交量倍率", f"{last['Volume']/last['Vol_MA5']:.1f}x")
            c5.metric("60MA 斜率", "向上 ↑" if last['MA60_Slope'] > 0 else "向下 ↓")

            # 圖表展示
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
            # K線與 60MA
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="60MA", line=dict(color='yellow', width=2)), row=1, col=1)
            # SuperTrend 線
            fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_10_4.0'], name="SuperTrend", line=dict(color='cyan', dash='dot')), row=1, col=1)
            # 成交量
            vol_color = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_color), row=2, col=1)

            fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # 操作具體建議
            st.markdown("---")
            st.subheader("📝 AI 決策指導")
            if score >= 85:
                st.write("🎯 **當前機會**：五大指標高度共振，大戶進場且趨勢極強。這是標準的**起漲第一棒**，目標波段 30%。")
            elif score >= 60:
                st.write("👍 **當前機會**：趨勢多頭，但量能或動能稍弱。適合分批佈局，不建議一次性滿倉。")
            elif last['SUPERTd_10_4.0'] == -1:
                st.write("❌ **警訊**：目前處於空頭波段。即使有反彈，在 60MA 斜率轉正與 SuperTrend 變綠前，不宜做多。")
            else:
                st.write("⏳ **警訊**：目前處於無趨勢盤整區，買入容易面臨漫長的等待，建議換股操作。")
        else:
            st.error("😭 請求過於頻繁 (Rate Limit) 或代號輸入錯誤。")
            st.info("請等待 10 分鐘讓 Yahoo 伺服器冷卻，或點擊側邊欄的「強制刷新數據」。")
