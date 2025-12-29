import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面風格設定
st.set_page_config(page_title="互動式量化選股雷達", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #00FFCC !important; }
    .stMetric { background-color: #111111; padding: 15px; border-radius: 10px; border: 1px solid #333333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 四維度量化選股 V2.0 (互動版)")

# 2. 技術檔位計算函數 (保留先前的量化邏輯)
def get_tech_data(hist):
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    hist['RSI'] = 100 - (100 / (1 + gain/loss))
    
    # BIAS
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['MA60'] = hist['Close'].rolling(window=60).mean()
    hist['BIAS'] = (hist['Close'] - hist['MA20']) / hist['MA20'] * 100
    
    # 歷史百分位檔位計算
    def calc_p(series):
        return series.rolling(window=252).apply(lambda x: (x < x[-1]).mean() * 100)

    # 綜合技術檔位分數 (0-100)
    hist['Tech_Score'] = (calc_p(hist['RSI']) * 0.5) + (calc_p(hist['BIAS']) * 0.5)
    return hist

# 3. 主分析程式
def run_interactive_analysis(code):
    try:
        ticker_str = f"{code}.TW"
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="2y") # 抓兩年數據以便滑動看歷史
        if hist.empty:
            ticker_str = f"{code}.TWO"
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period="2y")
        
        if hist.empty: return None, "找不到數據"

        hist = get_tech_data(hist)
        info = stock.info
        
        return {
            "name": info.get('longName', code),
            "price": info.get('currentPrice', hist['Close'].iloc[-1]),
            "hist": hist,
            "score": round(hist['Tech_Score'].iloc[-1], 2)
        }, None
    except Exception as e:
        return None, str(e)

# UI 介面
with st.sidebar:
    st.header("🔍 搜尋中心")
    stock_input = st.text_input("輸入台股代號", value="2330")
    run_btn = st.button("啟動全維度分析")

if run_btn:
    data, err = run_interactive_analysis(stock_input)
    if err:
        st.error(f"分析失敗: {err}")
    else:
        st.subheader(f"📊 {data['name']} ({stock_input}) - 綜合檔位: {data['score']}")
        
        hist = data['hist']
        
        # --- 建立 Plotly 互動圖表 ---
        # 建立雙 Y 軸圖表
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 1. 主 Y 軸: K 線圖 (Candlestick)
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name="K線",
            increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'
        ), secondary_y=False)

        # 2. 主 Y 軸: 均線
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name="MA20", line=dict(color='cyan', width=1.5)), secondary_y=False)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA60'], name="MA60", line=dict(color='magenta', width=1.5)), secondary_y=False)

        # 3. 副 Y 軸: 技術檔位分數 (Area Chart)
        fig.add_trace(go.Scatter(
            x=hist.index, 
            y=hist['Tech_Score'], 
            name="技術檔位分數", 
            line=dict(color='rgba(0, 255, 204, 0.5)', width=2),
            fill='tozeroy', # 填滿下方
            fillcolor='rgba(0, 255, 204, 0.1)'
        ), secondary_y=True)

        # 設定配置
        fig.update_layout(
            height=600,
            template="plotly_dark",
            xaxis_rangeslider_visible=True, # 開啟下方滑動條
            xaxis_title="時間 (可滑動看歷史)",
            yaxis_title="股價 (TWD)",
            yaxis2_title="技術檔位分數 (0-100)",
            yaxis2_range=[0, 100], # 固定副軸範圍
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # 設定初始顯示範圍 (最後一個月)
        last_date = hist.index[-1]
        start_date = last_date - pd.DateOffset(months=1)
        fig.update_xaxes(range=[start_date, last_date])

        st.plotly_chart(fig, use_container_width=True)

st.caption("💡 提示：你可以使用下方的滑桿左右滑動查看歷史數據，或用滑鼠滾輪縮放時間區間。")
