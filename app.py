import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 介面樣式 ---
st.set_page_config(layout="wide", page_title="飆股戰情室 Pro")
st.markdown("<style>.main {background-color: #000000;}</style>", unsafe_allow_html=True)

# --- 2. 強化版資料抓取 ---
@st.cache_data(ttl=600)
def fetch_data_robust(stock_id):
    # 三竹風格通常需要較長歷史來算均線
    for suffix in [".TW", ".TWO"]:
        ticker_str = f"{stock_id}{suffix}"
        try:
            df = yf.download(ticker_str, period="1y", progress=False)
            if not df.empty:
                # 確保索引是日期格式且移除時區
                df.index = pd.to_datetime(df.index).tz_localize(None)
                # 處理 yfinance 可能回傳的多層索引
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df
        except:
            continue
    return pd.DataFrame()

# --- 3. 買賣邏輯運算 ---
def get_signals(df):
    df = df.copy()
    # 計算均線
    df['MA5'] = ta.sma(df['Close'], length=5)
    df['MA20'] = ta.sma(df['Close'], length=20)
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['Vol_MA20'] = ta.sma(df['Volume'], length=20)
    
    # 策略：突破 20MA + 成交量 > 20MA均量1.5倍
    buy_sig = (df['Close'] > df['MA20']) & (df['Volume'] > df['Vol_MA20'] * 1.5)
    return df, buy_sig

# --- 4. UI 渲染 ---
st.title("🏹 專業級飆股監控")

stock_id = st.sidebar.text_input("📍 輸入台股代號", value="2330")
display_days = st.sidebar.slider("🔍 顯示天數", 40, 150, 80)

df_raw = fetch_data_robust(stock_id)

if not df_raw.empty:
    df, buy_sig = get_signals(df_raw)
    df_plot = df.tail(display_days)
    buy_plot = buy_sig.tail(display_days)
    
    # 頂部儀表板
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    change = latest['Close'] - prev['Close']
    c1, c2, c3 = st.columns(3)
    c1.metric("最新股價", f"{latest['Close']:.1f}", f"{change:+.1f}")
    c2.metric("攻擊量能", f"{latest['Volume']/latest['Vol_MA20']:.2f}x")
    c3.metric("趨勢狀態", "🔥 起漲訊號" if buy_sig.iloc[-1] else "⚖️ 盤整觀望")

    # --- 三竹風格 K 線圖 ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # K線
    fig.add_trace(go.Candlestick(
        x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
        low=df_plot['Low'], close=df_plot['Close'], name="K線",
        increasing_line_color='#FF0000', increasing_fillcolor='#FF0000',
        decreasing_line_color='#00FF00', decreasing_fillcolor='#00FF00'
    ), row=1, col=1)

    # 均線 (5/20/60)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA5'], name="5MA", line=dict(color='#FFFFFF', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA20'], name="20MA", line=dict(color='#FF00FF', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA60'], name="60MA", line=dict(color='#FFD700', width=1)), row=1, col=1)

    # 買入標記 (三角形)
    buy_dates = df_plot[buy_plot].index
    fig.add_trace(go.Scatter(
        x=buy_dates, y=df_plot.loc[buy_dates, 'Low'] * 0.96,
        mode='markers', marker=dict(symbol='triangle-up', size=15, color='#FF0000'),
        name='買點'
    ), row=1, col=1)

    # 成交量
    v_colors = ['#FF0000' if c >= o else '#00FF00' for c, o in zip(df_plot['Close'], df_plot['Open'])]
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=v_colors, name='成交量'), row=2, col=1)

    # 圖表外觀
    fig.update_layout(height=700, template="plotly_dark", plot_bgcolor='#000', paper_bgcolor='#000',
                      xaxis_rangeslider_visible=False, showlegend=False,
                      margin=dict(l=10, r=10, t=10, b=10))
    fig.update_xaxes(showgrid=True, gridcolor='#222')
    fig.update_yaxes(showgrid=True, gridcolor='#222')
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("⚠️ 資料抓取失敗。請嘗試：1. 檢查代號是否正確 2. 稍後重新整理 (yfinance 有時會暫時拒絕連線)。")
