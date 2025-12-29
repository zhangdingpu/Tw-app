import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 專業視覺配置 ---
st.set_page_config(layout="wide", page_title="飆股戰情室 Pro")
st.markdown("<style>.main {background-color: #000000;}</style>", unsafe_allow_html=True)

# --- 2. 鋼鐵防禦抓取模組 ---
@st.cache_data(ttl=3600)
def fetch_stock_data(stock_id):
    # 自動嘗試台股後綴
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{stock_id}{suffix}")
            df = ticker.history(period="1y")
            if not df.empty:
                df.index = df.index.tz_localize(None) # 修正 Plotly 時間軸空白問題
                return df
        except: continue
    return pd.DataFrame()

# --- 3. 核心買賣邏輯 (保留你要求的 20MA+量增邏輯) ---
def apply_strategy(df):
    df = df.copy()
    # 技術指標
    df['MA5'] = ta.sma(df['Close'], length=5)
    df['MA20'] = ta.sma(df['Close'], length=20)
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['Vol_MA20'] = ta.sma(df['Volume'], length=20)
    
    # 買賣訊號判斷
    # 邏輯：收盤 > 20MA 且 成交量 > 20MA均量1.5倍 且 當日收紅
    buy_logic = (df['Close'] > df['MA20']) & \
                (df['Volume'] > df['Vol_MA20'] * 1.5) & \
                (df['Close'] > df['Open'])
    
    # 賣出邏輯：跌破 20MA
    sell_logic = (df['Close'] < df['MA20'])
    
    return df, buy_logic, sell_logic

# --- 4. 主介面渲染 ---
st.title("🏹 專業級飆股監控系統")

with st.sidebar:
    stock_id = st.text_input("📍 輸入台股代號", value="2330")
    display_days = st.slider("🔍 顯示天數 (建議 80-100)", 40, 200, 90)
    st.info("買入邏輯：突破 20MA + 1.5倍攻擊量")

df_raw = fetch_stock_data(stock_id)

if not df_raw.empty:
    df, buy_sig, sell_sig = apply_strategy(df_raw)
    
    # 1. 頂部摘要資訊
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    diff = latest['Close'] - prev['Close']
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("當前股價", f"{latest['Close']:.1f}", f"{diff:+.1f}")
    c2.metric("攻擊力道", f"{latest['Volume']/latest['Vol_MA20']:.2f}x")
    status = "🔥 買入訊號" if buy_sig.iloc[-1] else "⚖️ 持有/觀望"
    c3.metric("診斷狀態", status)
    c4.metric("20MA 位置", f"{latest['MA20']:.1f}")

    # 2. 專業繪圖區 (參考你提供的 yfinance/plotly 繪圖結構)
    df_plot = df.tail(display_days)
    buy_plot = buy_sig.tail(display_days)
    sell_plot = sell_sig.tail(display_days)
    
    # 建立雙層圖表 (K線 + 成交量)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # [主圖] K線圖 - 仿三竹紅漲綠跌
    fig.add_trace(go.Candlestick(
        x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
        low=df_plot['Low'], close=df_plot['Close'], name="K線",
        increasing_line_color='#FF0000', increasing_fillcolor='#FF0000',
        decreasing_line_color='#00FF00', decreasing_fillcolor='#00FF00'
    ), row=1, col=1)

    # [主圖] 均線系統
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA5'], name="5MA", line=dict(color='#FFFFFF', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA20'], name="20MA", line=dict(color='#FF00FF', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA60'], name="60MA", line=dict(color='#FFD700', width=1)), row=1, col=1)

    # [主圖] 買賣標記
    buy_dates = df_plot[buy_plot].index
    fig.add_trace(go.Scatter(
        x=buy_dates, y=df_plot.loc[buy_dates, 'Low'] * 0.97,
        mode='markers', marker=dict(symbol='triangle-up', size=15, color='#FF0000'),
        name='起漲點'
    ), row=1, col=1)

    # [副圖] 成交量
    vol_colors = ['#FF0000' if c >= o else '#00FF00' for c, o in zip(df_plot['Close'], df_plot['Open'])]
    fig.add_trace(go.Bar(
        x=df_plot.index, y=df_plot['Volume'], 
        name="成交量", marker_color=vol_colors, opacity=0.8
    ), row=2, col=1)

    # 視覺外觀優化
    fig.update_layout(
        height=750, template="plotly_dark", plot_bgcolor='#000', paper_bgcolor='#000',
        xaxis_rangeslider_visible=False, showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    fig.update_xaxes(showgrid=True, gridcolor='#222', zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor='#222', zeroline=False)
    
    st.plotly_chart(fig, use_container_width=True)

    # 3. 數據表
    with st.expander("查看近 10 日詳細數據"):
        st.dataframe(df.tail(10)[['Close', 'Volume', 'MA20']].sort_index(ascending=False))

else:
    st.error("⚠️ 資料抓取失敗，請確認代碼是否正確 (例如 2330)。")
