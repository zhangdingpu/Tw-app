import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(layout="wide", page_title="飆股戰情室 Pro")

# --- 2. 絕對防禦資料清洗模組 ---
def absolute_clean(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # 標準化所有可能的欄位名稱
    col_maps = {
        'date': ['date', 'Date', 'Date_Time'],
        'open': ['open', 'Open', 'open_price', 'Open_Price'],
        'high': ['high', 'High', 'high_price', 'High_Price'],
        'low': ['low', 'Low', 'low_price', 'Low_Price'],
        'close': ['close', 'Close', 'close_price', 'Close_Price'],
        'volume': ['volume', 'Volume', 'Trading_Volume', 'vol']
    }
    
    new_df = pd.DataFrame()
    # 針對每個標準欄位進行搜索
    for std_name, alt_names in col_maps.items():
        found = False
        for alt in alt_names:
            if alt in df.columns:
                new_df[std_name] = df[alt]
                found = True
                break
        if not found:
            # 如果真的找不到，補 0 避免 KeyError 導致當機
            new_df[std_name] = 0.0

    # 強制轉換格式
    new_df['date'] = pd.to_datetime(new_df['date']).dt.strftime('%Y-%m-%d')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        new_df[c] = pd.to_numeric(new_df[c], errors='coerce').fillna(0.0)
        
    return new_df

# --- 3. 核心抓取函數 ---
@st.cache_data(ttl=3600)
def fetch_stock_report(stock_id, start_date):
    dl = DataLoader()
    try:
        raw = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        df = absolute_clean(raw)
        if df.empty or df['close'].sum() == 0: return None
        
        # 指標計算
        df['ma20'] = ta.sma(df['close'], length=20)
        df['vol_ma20'] = ta.sma(df['volume'], length=20)
        
        return df
    except:
        return None

# --- 4. 主介面渲染 ---
st.title("🏹 飆股動能分析儀 Pro")

stock_id = st.sidebar.text_input("📍 股票代碼", value="2330")
lookback = st.sidebar.slider("回溯天數", 60, 365, 120)
start_dt = (datetime.now() - timedelta(days=lookback)).strftime('%Y-%m-%d')

df = fetch_stock_report(stock_id, start_dt)

if df is not None:
    latest = df.iloc[-1]
    prev_close = df.iloc[-2]['close'] if len(df) > 1 else latest['close']
    
    # 儀表板資料計算
    score = 0
    if latest['close'] > latest['ma20']: score += 40
    if latest['volume'] > latest['vol_ma20'] * 1.5: score += 40
    if latest['close'] > prev_close: score += 20

    # --- 頂部摘要區 ---
    c1, c2, c3 = st.columns(3)
    c1.metric("當前得分", f"{score} 分", "強勢" if score >= 80 else "中性")
    v_ratio = round(latest['volume'] / df['volume'].tail(20).mean(), 2) if df['volume'].tail(20).mean() != 0 else 0
    c2.metric("成交量倍數", f"{v_ratio} 倍")
    c3.metric("最新收盤價", f"{latest['close']} 元", f"{round(latest['close']-prev_close, 2)}")

    # --- 繪圖區 ---
    # 確保資料格式正確才繪圖
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # K線
    fig.add_trace(go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#FF4B4B', decreasing_line_color='#00F200', name='K線'
    ), row=1, col=1)
    
    # 20MA
    fig.add_trace(go.Scatter(x=df['date'], y=df['ma20'], name='20MA', line=dict(color='yellow', width=1.5)), row=1, col=1)

    # 起漲訊號標籤
    sig = (df['close'] > df['ma20']) & (df['volume'] > df['vol_ma20'] * 1.5)
    sig_df = df[sig]
    fig.add_trace(go.Scatter(
        x=sig_df['date'], y=sig_df['low'] * 0.98, mode='markers',
        marker=dict(symbol='triangle-up', size=15, color='#FF4B4B'), name='起漲點'
    ), row=1, col=1)

    # 成交量
    v_colors = ['#FF4B4B' if c > o else '#00F200' for c, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(x=df['date'], y=df['volume'], marker_color=v_colors, name='成交量'), row=2, col=1)

    fig.update_layout(height=700, template='plotly_dark', xaxis_rangeslider_visible=False, showlegend=False, 
                      margin=dict(l=10, r=10, t=10, b=10))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ 無法獲取有效資料。請確認代碼是否正確，或嘗試將回溯天數拉長。")
