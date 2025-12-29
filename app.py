import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 頁面風格配置 ---
st.set_page_config(layout="wide", page_title="飆股戰情室 Pro")

st.markdown("""
    <style>
    .stMetric { background-color: #1a1c23; padding: 15px; border-radius: 10px; border-top: 3px solid #ff4b4b; }
    .status-box { background-color: #1a1c23; padding: 20px; border-radius: 15px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 欄位標準化與清洗 (解決 KeyError 的核心) ---
def standardize_columns(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # 建立映射字典，解決 FinMind 欄位不統一問題
    mapping = {
        'Trading_Volume': 'volume', 'vol': 'volume', 'Volume': 'volume',
        'Date': 'date', 'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low'
    }
    df = df.rename(columns=mapping)
    df.columns = [c.lower() for c in df.columns] # 全部轉小寫
    
    # 確保數值欄位正確轉換
    for col in ['close', 'open', 'high', 'low', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# --- 3. 數據獲取與分析 ---
@st.cache_data(ttl=3600)
def get_clean_data(stock_id, start_date):
    dl = DataLoader()
    try:
        raw_df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        df = standardize_columns(raw_df)
        
        if df.empty: return None
        
        # 技術指標計算
        df['ma20'] = ta.sma(df['close'], length=20)
        df['vol_ma20'] = ta.sma(df['volume'], length=20)
        
        inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date)
        return {"price": df, "inst": inst}
    except:
        return None

# --- 4. 主程式 ---
st.title("🏹 飆股動能分析儀")

stock_id = st.sidebar.text_input("📍 股票代碼", value="2330")
lookback = st.sidebar.slider("回溯天數", 60, 365, 120)
start_dt = (datetime.now() - timedelta(days=lookback)).strftime('%Y-%m-%d')

data = get_clean_data(stock_id, start_dt)

if data:
    df = data['price']
    latest = df.iloc[-1]
    
    # 診斷得分邏輯
    score = 0
    if latest['close'] > latest['ma20']: score += 40
    if latest['volume'] > latest['vol_ma20'] * 1.5: score += 40
    if latest['close'] > df.iloc[-2]['close']: score += 20
    
    # --- 頂部摘要區 ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("當前得分", f"{score} 分", "強勢" if score >= 80 else "中性")
    with c2:
        # 修正原本報錯的 vol_ratio 位置，加入安全檢查
        v_ratio = round(latest['volume'] / df['volume'].tail(20).mean(), 2) if df['volume'].tail(20).mean() != 0 else 0
        st.metric("成交量倍數", f"{v_ratio} 倍")
    with c3:
        st.metric("收盤價", f"{latest['close']} 元")

    # --- 專業圖表呈現 ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # K線與起漲箭頭
    fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K線'), row=1, col=1)
    
    # 標記起漲點 (量增價揚且破20MA)
    sig = (df['close'] > df['ma20']) & (df['volume'] > df['vol_ma20'] * 1.5)
    sig_df = df[sig]
    fig.add_trace(go.Scatter(x=sig_df['date'], y=sig_df['low']*0.98, mode='markers', 
                             marker=dict(symbol='triangle-up', size=15, color='#ff4b4b'), name='起漲訊號'), row=1, col=1)

    # 成交量柱狀圖
    fig.add_trace(go.Bar(x=df['date'], y=df['volume'], name='成交量', marker_color='#333'), row=2, col=1)

    fig.update_layout(height=700, template='plotly_dark', xaxis_rangeslider_visible=False, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("❌ 數據解析失敗。原因可能是：1. 代碼錯誤 2. API 頻率限制 3. 該時段無交易。請稍後再試。")
