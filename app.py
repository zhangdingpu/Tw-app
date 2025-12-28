import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面基本設定
st.set_page_config(page_title="AI 權重選股系統", layout="wide")
st.title("🚀 專業加權選股判斷系統")

# 1. 輸入與數據抓取
ticker = st.text_input("輸入股票代碼 (例: NVDA, 2330.TW)", "NVDA").upper()

if ticker:
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        info = stock.info

        if not df.empty:
            # --- 指標計算 (這是那條線的靈魂) ---
            # 動能分 (40%)：收盤價高於 20日均線
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA200'] = df['Close'].rolling(200).mean()
            df['Momentum_Score'] = (df['Close'] > df['MA20']).astype(int) * 100
            
            # 品質與價值得分 (60%)：這部分來自財報，是固定加分
            roe = info.get('returnOnEquity', 0)
            pe = info.get('trailingPE', 50)
            quality_score = min(roe / 0.15, 1.0) * 100 if roe else 0
            value_score = max(0, (1 - (pe / 60))) * 100 if pe else 0
            
            # 總分計算
            df['Final_Score'] = (df['Momentum_Score'] * 0.4) + (quality_score * 0.3) + (value_score * 0.3)

            # --- 繪圖邏輯 (解決沒看見線的問題) ---
            # 強制建立兩個行，比例為 7:3
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.1, 
                subplot_titles=(f"{ticker} 股價走勢", "🔥 買入建議分數 (0-100)"),
                row_heights=[0.7, 0.3]
            )

            # A. 上方：K 線與 200日均線
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], 
                low=df['Low'], close=df['Close'], name="K線"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df.index, y=df['MA200'], name="MA200 (長期趨勢)", 
                line=dict(color='orange', width=2)
            ), row=1, col=1)

            # B. 下方：這就是你要的那條線
            fig.add_trace(go.Scatter(
                x=df.index, y=df['Final_Score'], 
                name="買入評分", 
                line=dict(color='red', width=3),
                fill='tozeroy', 
                fillcolor='rgba(255, 0, 0, 0.2)'
            ), row=2, col=1)

            # 設定下方圖表的 Y 軸範圍，確保線不會縮小
            fig.update_yaxes(range=[0, 110], title="分數", row=2, col=1)
            
            # 加入 70 分的紅綠分界線
            fig.add_hline(y=70, line_dash="dash", line_color="green", row=2, col=1)

            fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
            
            # 顯示圖表
            st.plotly_chart(fig, use_container_width=True)

            # --- 系統診斷文字 ---
            current_score = df['Final_Score'].iloc[-1]
            st.subheader(f"📊 當前評分：{current_score:.1f}")
            if current_score >= 70:
                st.success("🎯 買入訊號：各項指標完美符合，目前是強力買入區。")
            else:
                st.info("⌛ 觀望訊號：分數未達標，建議等待回調或趨勢確認。")

    except Exception as e:
        st.error(f"錯誤: {e}")
