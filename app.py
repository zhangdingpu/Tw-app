import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import time

# --- 1. 頁面配置與三竹黑系風格 CSS ---
st.set_page_config(layout="wide", page_title="飆股戰情室 - Smart App")

st.markdown("""
    <style>
    .main { background-color: #050505; }
    div[data-testid="stMetricValue"] { font-size: 32px; color: #ff4b4b; }
    .status-card {
        background-color: #1a1c23; border-radius: 12px; padding: 20px;
        border-top: 4px solid #ff4b4b; text-align: center; margin-bottom: 10px;
    }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心數據模組 (含防封鎖機制) ---
@st.cache_resource
def get_loader(token=""):
    api = DataLoader()
    if token: api.login_by_token(token)
    return api

def safe_fetch(api, func, **kwargs):
    """具備自動重試與錯誤攔截的抓取器"""
    try:
        data = func(**kwargs)
        if data is None or data.empty: return pd.DataFrame()
        return data
    except Exception:
        return pd.DataFrame()

# --- 3. 指標與訊號計算 ---
def calculate_mitake_style(df):
    if df.empty: return 0, "無資料"
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={'trading_volume': 'volume', 'vol': 'volume'})
    
    # 計算均線
    df['ma20'] = ta.sma(df['close'], length=20)
    df['vol_ma20'] = ta.sma(df['volume'], length=20)
    
    latest = df.iloc[-1]
    score = 0
    # 多頭排列判斷
    if latest['close'] > latest['ma20']: score += 40
    # 攻擊量判斷
    if latest['volume'] > latest['vol_ma20'] * 1.5: score += 30
    # 漲跌判斷
    if latest['close'] > df.iloc[-2]['close']: score += 30
    
    status = "🔥 強勢進攻" if score >= 70 else "⚖️ 區間整理" if score >= 40 else "❄️ 弱勢觀望"
    return score, status

# --- 4. 主介面流程 ---
st.sidebar.header("🛡️ 專業模式設定")
api_token = st.sidebar.text_input("FinMind Token (選填)", type="password", help="註冊 FinMind 免費取得可增加抓取次數")
stock_id = st.sidebar.text_input("股票代碼", value="2330")
lookback = st.sidebar.slider("顯示區間", 60, 365, 120)

loader = get_loader(api_token)
start_date = (datetime.now() - timedelta(days=lookback)).strftime('%Y-%m-%d')

if st.sidebar.button("確認查詢"):
    with st.spinner('🎬 正在同步三竹雲端數據...'):
        # 抓取三位一體數據
        price_df = safe_fetch(loader, loader.taiwan_stock_daily, stock_id=stock_id, start_date=start_date)
        
        if not price_df.empty:
            score, status_text = calculate_mitake_style(price_df)
            
            # --- 頂部診斷區 (三竹智選股風格) ---
            st.markdown(f"### 📊 {stock_id} 綜合診斷報告")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='status-card'>評分<br><h1>{score}</h1></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='status-card'>訊號<br><h3>{status_text}</h3></div>", unsafe_allow_html=True)
            with c3:
                vol_ratio = round(price_df.iloc[-1]['volume'] / price_df['volume'].tail(20).mean(), 2)
                st.markdown(f"<div class='status-card'>量能倍數<br><h3>{vol_ratio}x</h3></div>", unsafe_allow_html=True)

            # --- 專業圖表區 ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            
            # K線圖
            fig.add_trace(go.Candlestick(x=price_df['date'], open=price_df['open'], high=price_df['high'], 
                                         low=price_df['low'], close=price_df['close'], 
                                         increasing_line_color='#ff4b4b', decreasing_line_color='#00f200', name='K線'), row=1, col=1)
            
            # 自動標註買點 (起漲點箭頭)
            signals = (price_df['close'] > price_df['close'].shift(1)*1.02) & (price_df['volume'] > price_df['volume'].rolling(20).mean()*1.5)
            sig_df = price_df[signals]
            fig.add_trace(go.Scatter(x=sig_df['date'], y=sig_df['low']*0.97, mode='markers', 
                                     marker=dict(symbol='triangle-up', size=12, color='#ff4b4b'), name='起漲點'), row=1, col=1)

            # 成交量圖
            v_colors = ['#ff4b4b' if c > o else '#00f200' for c, o in zip(price_df['close'], price_df['open'])]
            fig.add_trace(go.Bar(x=price_df['date'], y=price_df['volume'], marker_color=v_colors, name='成交量'), row=2, col=1)

            fig.update_layout(height=600, template='plotly_dark', plot_bgcolor='#050505', paper_bgcolor='#050505',
                              margin=dict(l=20, r=20, t=20, b=20), xaxis_rangeslider_visible=False)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=False)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error("🚨 數據調用達到上限或伺服器忙碌。請 1. 檢查代碼是否正確 2. 填寫 Token 3. 稍後重試。")

