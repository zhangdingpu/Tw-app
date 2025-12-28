import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="頂尖選股評分系統", layout="wide")
st.title("⚖️ 權重化投資決策指標系統")

ticker = st.text_input("輸入股票代碼", "NVDA").upper()

if ticker:
    stock = yf.Ticker(ticker)
    # 抓取較長時間數據以計算均線
    df = stock.history(period="2y")
    info = stock.info

    if not df.empty:
        # --- 數據計算層 ---
        # 1. 動能指標：股價與 MA20 的距離 (20-day Moving Average)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        # 動能得分：現價高於 MA20 且 MA20 > MA60 得分高
        df['Momentum_Score'] = ((df['Close'] > df['MA20']).astype(int) * 50 + 
                                (df['MA20'] > df['MA60']).astype(int) * 50)

        # 2. 價值與品質得分 (固定值，來自財報)
        roe = info.get('returnOnEquity', 0)
        pe = info.get('trailingPE', 50)
        
        # 品質得分 (ROE > 0.15 為滿分)
        quality_score = min(roe / 0.15, 1.0) * 100
        # 價值得分 (PE < 20 為滿分)
        value_score = max(0, (1 - (pe / 60))) * 100

        # 3. 權重計算 (40% 動能 + 30% 品質 + 30% 價值)
        df['Final_Score'] = (df['Momentum_Score'] * 0.4 + 
                             quality_score * 0.3 + 
                             value_score * 0.3)

        # --- 繪圖層 ---
        # 建立兩個子圖：上方 K 線，下方評分線
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.1, subplot_titles=(f'{ticker} 股價', '綜合買入建議分數 (0-100)'),
                           row_heights=[0.7, 0.3])

        # 子圖 1：K 線與均線
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="股價"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20", line=dict(color='blue', width=1)), row=1, col=1)

        # 子圖 2：買入判斷線 (這就是你要求的那條線)
        fig.add_trace(go.Scatter(x=df.index, y=df['Final_Score'], name="投資價值分", line=dict(color='red', width=2), fill='tozeroy'), row=2, col=1)
        
        # 加入門檻基準線 (70分以上為強力建議區)
        fig.add_hline(y=70, line_dash="dash", line_color="green", annotation_text="強烈買入區", row=2, col=1)
        fig.add_hline(y=40, line_dash="dash", line_color="orange", annotation_text="觀望區", row=2, col=1)

        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- 即時診斷 ---
        current_score = df['Final_Score'].iloc[-1]
        st.subheader(f"🚩 當前評分：{current_score:.1f} / 100")
        
        if current_score >= 70:
            st.success("🔥 現在是理想的買入時機：指標顯示基本面強勁且技術面處於多頭。")
        elif current_score >= 40:
            st.warning("⚠️ 建議觀望：目前分數處於中性區間，等待趨勢明朗。")
        else:
            st.error("❄️ 暫不建議介入：指標顯示估值過高、獲利平庸或趨勢已轉弱。")
