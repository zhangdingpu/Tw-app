import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面風格設定
st.set_page_config(page_title="互動式量化選股雷達 V3.0", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #00FFCC !important; }
    .stMetric { background-color: #111111; padding: 15px; border-radius: 10px; border: 1px solid #333333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 四維度量化選股 V3.0 (流暢優化版)")

# 2. 指標計算函數
def get_clean_indicators(hist):
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    hist['RSI'] = 100 - (100 / (1 + gain/loss))
    
    # BIAS & MA
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['MA60'] = hist['Close'].rolling(window=60).mean()
    hist['BIAS'] = (hist['Close'] - hist['MA20']) / hist['MA20'] * 100
    
    # 歷史百分位檔位計算
    def calc_p(series):
        return series.rolling(window=252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)

    hist['Tech_Score'] = (calc_p(hist['RSI']) * 0.5) + (calc_p(hist['BIAS']) * 0.5)
    
    # 買賣訊號
    hist['Buy_Sig'] = np.where((hist['MA20'].shift(1) <= hist['MA60'].shift(1)) & (hist['MA20'] > hist['MA60']), hist['Low'] * 0.98, np.nan)
    hist['Sell_Sig'] = np.where((hist['MA20'].shift(1) >= hist['MA60'].shift(1)) & (hist['MA20'] < hist['MA60']), hist['High'] * 1.02, np.nan)
    
    return hist

# 3. 分析程式
def run_analysis(code):
    try:
        ticker_str = f"{code}.TW"
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="3y") 
        if hist.empty:
            ticker_str = f"{code}.TWO"
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period="3y")
        
        if hist.empty: return None, "找不到數據"

        hist = get_clean_indicators(hist)
        plot_hist = hist.tail(400) # 保持足夠的歷史長度供滑動
        
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
        
        # --- [優化 1] 說明文字移至圖表上方 ---
        st.info("""
        📘 **圖表操作說明：**
        * **買賣訊號：** 綠色 ▲ 為黃金交叉(買入)，紅色 ▼ 為死亡交叉(賣出)。
        * **技術檔位分數 (0-100)：** 數值越低代表股價相對於歷史處於便宜區，越高則為過熱區。
        * **操作方式：** 下方滑桿可左右滑動看歷史，滑鼠滾輪可縮放時間區間。
        """)

        hist = data['hist']
        
        # 建立雙 Y 軸圖表
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 1. K 線圖
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
            name="K線", increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C',
            showlegend=True
        ), secondary_y=False)

        # 2. 均線
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name="MA20", line=dict(color='cyan', width=1.5), opacity=0.8), secondary_y=False)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA60'], name="MA60", line=dict(color='magenta', width=1.5), opacity=0.8), secondary_y=False)

        # 3. 買賣訊號
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Buy_Sig'], name="買入訊號 ▲", mode='markers', marker=dict(symbol='triangle-up', size=13, color='#00FF00', line=dict(width=1, color='white'))), secondary_y=False)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Sell_Sig'], name="賣出訊號 ▼", mode='markers', marker=dict(symbol='triangle-down', size=13, color='#FF0000', line=dict(width=1, color='white'))), secondary_y=False)

        # 4. 副軸：技術檔位分數
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist['Tech_Score'], name="技術檔位分數 (0-100)", 
            line=dict(color='rgba(0, 255, 204, 0.7)', width=2.5),
            fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.15)'
        ), secondary_y=True)

        # --- [優化 2] 滑動流暢度與佈局優化 ---
        fig.update_xaxes(
            rangebreaks=[dict(bounds=["sat", "mon"])], # 跳過週末
            rangeslider_visible=True, # 顯示下方滑桿
            rangeslider_thickness=0.08, # 稍微縮小滑桿高度增加主圖空間
            type='date'
        )
        
        fig.update_layout(
            height=750, # 固定高度防止縮放時變形
            template="plotly_dark",
            margin=dict(l=50, r=50, t=30, b=50), # 緊湊邊距
            yaxis_title="股價 (TWD)",
            yaxis2_title="技術檔位分數 (0-100)",
            yaxis2_range=[0, 105], # 稍微留白避免線頂到邊緣
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            autosize=True
        )

        # 預設視角顯示最近一個月
        last_date = hist.index[-1]
        start_view = last_date - pd.DateOffset(months=1)
        fig.update_xaxes(range=[start_view, last_date])

        # 使用 streamlit 容器渲染並停用切換按鈕以減少跳動
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True})

st.caption("🔍 提示：若手機版操作不順，請嘗試橫屏使用，滑動感會更佳。")
