import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面風格
st.set_page_config(page_title="互動式量化選股雷達 V2.5", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #00FFCC !important; }
    .stMetric { background-color: #111111; padding: 15px; border-radius: 10px; border: 1px solid #333333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 四維度量化選股 V2.5 (修復跳空與訊號版)")

# 2. 進階指標計算
def get_full_indicators(hist):
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    hist['RSI'] = 100 - (100 / (1 + gain/loss))
    
    # BIAS & MA
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['MA60'] = hist['Close'].rolling(window=60).mean()
    hist['BIAS'] = (hist['Close'] - hist['MA20']) / hist['MA20'] * 100
    
    # 歷史百分位檔位計算 (確保窗口為 252)
    def calc_p(series):
        return series.rolling(window=252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)

    hist['Tech_Score'] = (calc_p(hist['RSI']) * 0.5) + (calc_p(hist['BIAS']) * 0.5)
    
    # 買賣訊號邏輯
    hist['Buy_Sig'] = np.where((hist['MA20'].shift(1) <= hist['MA60'].shift(1)) & (hist['MA20'] > hist['MA60']), hist['Low'] * 0.98, np.nan)
    hist['Sell_Sig'] = np.where((hist['MA20'].shift(1) >= hist['MA60'].shift(1)) & (hist['MA20'] < hist['MA60']), hist['High'] * 1.02, np.nan)
    
    return hist

# 3. 主分析程式
def run_analysis(code):
    try:
        # 抓取較長數據以解決百分位計算初期空白問題
        ticker_str = f"{code}.TW"
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="3y") # 抓取 3 年確保百分位有足夠參考量
        if hist.empty:
            ticker_str = f"{code}.TWO"
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period="3y")
        
        if hist.empty: return None, "找不到數據"

        hist = get_full_indicators(hist)
        # 只取最近一年的數據進行圖表展示，但計算是基於更早的數據
        plot_hist = hist.tail(300) 
        
        return {
            "name": stock.info.get('longName', code),
            "price": stock.info.get('currentPrice', hist['Close'].iloc[-1]),
            "hist": plot_hist,
            "score": round(plot_hist['Tech_Score'].iloc[-1], 2)
        }, None
    except Exception as e:
        return None, str(e)

# UI 介面
with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    run_btn = st.button("啟動全維度分析")

if run_btn:
    data, err = run_analysis(stock_input)
    if err:
        st.error(f"分析失敗: {err}")
    else:
        st.subheader(f"📊 {data['name']} ({stock_input}) - 綜合檔位分數: {data['score']}")
        hist = data['hist']
        
        # 建立雙 Y 軸圖表
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 1. K 線圖
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
            name="K線", increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'
        ), secondary_y=False)

        # 2. 均線
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name="MA20", line=dict(color='cyan', width=1.5)), secondary_y=False)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA60'], name="MA60", line=dict(color='magenta', width=1.5)), secondary_y=False)

        # 3. 買賣訊號 (標記在圖表上)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Buy_Sig'], name="買入訊號", mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime')), secondary_y=False)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Sell_Sig'], name="賣出訊號", mode='markers', marker=dict(symbol='triangle-down', size=12, color='red')), secondary_y=False)

        # 4. 副軸：技術檔位分數
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist['Tech_Score'], name="技術檔位分數", 
            line=dict(color='rgba(0, 255, 204, 0.6)', width=2),
            fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.1)'
        ), secondary_y=True)

        # 圖表設定
        fig.update_xaxes(
            rangebreaks=[dict(bounds=["sat", "mon"])], # 跳過週末
            rangeslider_visible=True,
            title="時間 (已排除非交易日)"
        )
        
        fig.update_layout(
            height=700, template="plotly_dark",
            yaxis_title="股價 (TWD)", yaxis2_title="技術檔位分數 (0-100)",
            yaxis2_range=[0, 100], hovermode="x unified"
        )

        # 預設顯示最近一個月
        last_date = hist.index[-1]
        start_view = last_date - pd.DateOffset(months=1)
        fig.update_xaxes(range=[start_view, last_date])

        st.plotly_chart(fig, use_container_width=True)
