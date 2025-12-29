import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 頁面外觀大改造 (三竹風格 CSS) ---
st.set_page_config(layout="wide", page_title="飆股戰情室 - 三竹風")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c23; padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b4b; }
    .report-card { 
        background-color: #1a1c23; padding: 20px; border-radius: 15px; 
        text-align: center; border: 1px solid #333;
    }
    h1, h2, h3 { color: #ffffff; font-family: 'Microsoft JhengHei'; }
    </style>
    """, unsafe_allow_html=True)

dl = DataLoader()

# --- 2. 強固型數據清洗 (承襲之前的優點) ---
def clean_and_prepare(df):
    if df is None or df.empty: return pd.DataFrame()
    column_map = {'Trading_Volume': 'volume', 'vol': 'volume', 'Volume': 'volume', 'Close': 'close'}
    df = df.rename(columns=column_map)
    df.columns = [c.lower() for c in df.columns]
    for c in ['close', 'open', 'high', 'low', 'volume']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

# --- 3. 數據抓取 ---
@st.cache_data(ttl=3600)
def fetch_data(stock_id, start_date):
    try:
        raw = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        df = clean_and_prepare(raw)
        if df.empty: return None
        df['ma20'] = ta.sma(df['close'], length=20)
        df['vol_ma20'] = ta.sma(df['volume'], length=20)
        
        inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date)
        holders = dl.taiwan_stock_holding_shares_per(stock_id=stock_id, start_date=start_date)
        return {"price": df, "inst": inst, "holders": holders}
    except: return None

# --- 4. 主介面設計 ---
st.title("🏹 飆股智能選股系統")

stock_id = st.sidebar.text_input("輸入代碼", value="2330")
data = fetch_data(stock_id, (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d'))

if data:
    df = data['price']
    latest = df.iloc[-1]
    
    # 計算得分與訊號
    score = 0
    signal_text = "觀望"
    if latest['close'] > latest['ma20']: score += 40
    if latest['volume'] > latest['vol_ma20'] * 1.5: score += 30
    
    # 頂部視覺卡片 (仿三竹診斷)
    col1, col2, col3 = st.columns(3)
    with col1:
        color = "#ff4b4b" if score >= 70 else "#00ff00" if score < 40 else "#f63366"
        st.markdown(f"""<div class='report-card'><h3>戰力評分</h3><h1 style='color:{color};'>{score}</h1></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class='report-card'><h3>操作建議</h3><h1 style='color:white;'>{"🔴 強勢" if score >= 70 else "🟡 盤整"}</h1></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class='report-card'><h3>攻擊力道</h3><h1 style='color:white;'>{round(latest['volume']/latest['vol_ma20'],1)}x</h1></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # --- 5. 專業繪圖 (隱藏座標軸網格，強調紅綠柱) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.7, 0.3])

    # K線
    fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                                 increasing_line_color='#ff4b4b', decreasing_line_color='#00f200', name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['ma20'], name='20MA', line=dict(color='yellow', width=1.5)), row=1, col=1)

    # 籌碼 (法人買賣)
    if not data['inst'].empty:
        inst = data['inst'].groupby('date').sum(numeric_only=True).reset_index()
        inst['net'] = inst['buy'] - inst['sell']
        fig.add_trace(go.Bar(x=inst['date'], y=inst['net'], 
                             marker_color=['#ff4b4b' if x > 0 else '#00f200' for x in inst['net']], name='法人'), row=2, col=1)

    fig.update_layout(height=600, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False,
                      margin=dict(l=10, r=10, t=10, b=10),
                      plot_bgcolor='#0e1117', paper_bgcolor='#0e1117')
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

    # 底部快捷清單
    st.subheader("📋 籌碼關鍵數據")
    st.table(df[['date', 'close', 'volume']].tail(5))

else:
    st.error("⚠️ 資料抓取失敗，請確認代碼或 API 頻率限制。")
