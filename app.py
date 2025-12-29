import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 頁面配置與三竹黑系風格 ---
st.set_page_config(layout="wide", page_title="飆股專業版 - 三竹介面")

st.markdown("""
    <style>
    .main { background-color: #000000; }
    .price-header { background-color: #111; padding: 10px; border-radius: 5px; border: 1px solid #333; }
    .stMetric { background-color: #000 !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 防禦性數據清洗 ---
def standardize_data(df):
    if df is None or df.empty: return pd.DataFrame()
    col_map = {'Trading_Volume': 'volume', 'vol': 'volume', 'Volume': 'volume', 'Close': 'close'}
    df = df.rename(columns=col_map)
    df.columns = [c.lower() for c in df.columns]
    for c in ['close', 'open', 'high', 'low', 'volume']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

# --- 3. 指標計算 (5/10/20/60 MA) ---
def add_indicators(df):
    df['ma5'] = ta.sma(df['close'], length=5)
    df['ma10'] = ta.sma(df['close'], length=10)
    df['ma20'] = ta.sma(df['close'], length=20)
    df['ma60'] = ta.sma(df['close'], length=60)
    # 增加 KD 指標模擬三竹下方區塊
    kd = ta.stoch(df['high'], df['low'], df['close'])
    df = pd.concat([df, kd], axis=1)
    return df

# --- 4. 主程式邏輯 ---
st.sidebar.title("🛠️ 看板設定")
stock_id = st.sidebar.text_input("股票代碼", value="2330")
days = st.sidebar.slider("顯示天數", 30, 200, 80) # 預設 80 天讓 K 線看起來夠粗

dl = DataLoader()
start_dt = (datetime.now() - timedelta(days=days + 100)).strftime('%Y-%m-%d')

try:
    raw = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_dt)
    df = standardize_data(raw)
    
    if not df.empty:
        df = add_indicators(df)
        df = df.tail(days) # 只擷取要顯示的天數
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        diff = round(latest['close'] - prev['close'], 2)
        pct = round((diff / prev['close']) * 100, 2)
        color = "#ff0000" if diff > 0 else "#00ff00"

        # --- 頂部報價區 (三竹風格) ---
        st.markdown(f"""
            <div class="price-header">
                <span style="color:#ccc; font-size:14px;">{stock_id} 最新收盤</span><br>
                <span style="color:{color}; font-size:42px; font-weight:bold;">{latest['close']}</span>
                <span style="color:{color}; font-size:18px;"> {'▲' if diff>0 else '▼'} {abs(diff)} ({pct}%)</span>
            </div>
        """, unsafe_allow_html=True)

        # --- 專業三層 K 線圖 (K線/成交量/KD) ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.02, 
                            row_heights=[0.5, 0.2, 0.3])

        # A. K 線圖
        fig.add_trace(go.Candlestick(
            x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#ff0000', increasing_fillcolor='#ff0000',
            decreasing_line_color='#00ff00', decreasing_fillcolor='#00ff00',
            name='K線'
        ), row=1, col=1)

        # B. 四大均線 (5/10/20/60)
        ma_colors = {'ma5': '#ffffff', 'ma10': '#ffd700', 'ma20': '#ff00ff', 'ma60': '#00ffff'}
        for ma, clr in ma_colors.items():
            fig.add_trace(go.Scatter(x=df['date'], y=df[ma], name=ma, line=dict(color=clr, width=1)), row=1, col=1)

        # C. 成交量
        v_colors = ['#ff0000' if c >= o else '#00ff00' for c, o in zip(df['close'], df['open'])]
        fig.add_trace(go.Bar(x=df['date'], y=df['volume'], marker_color=v_colors, name='成交量'), row=2, col=1)

        # D. KD 指標 (三竹下方區塊)
        fig.add_trace(go.Scatter(x=df['date'], y=df['STOCHk_14_3_3'], name='K', line=dict(color='#ffd700', width=1)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['STOCHd_14_3_3'], name='D', line=dict(color='#00ffff', width=1)), row=3, col=1)

        # 圖表樣式優化
        fig.update_layout(
            height=850, template='plotly_dark',
            plot_bgcolor='#000', paper_bgcolor='#000',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_rangeslider_visible=False, showlegend=False
        )
        fig.update_xaxes(showgrid=True, gridcolor='#222', zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor='#222', zeroline=False)
        
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("暫無數據，請確認 API 狀態或代碼。")
except Exception as e:
    st.error(f"系統異常: {e}")
