import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 初始化與配置 ---
st.set_page_config(layout="wide", page_title="飆股戰情室 Pro")
dl = DataLoader()

# 自定義 CSS 讓介面更專業
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心數據處理函數 (加強版) ---
@st.cache_data(ttl=3600)
def fetch_full_data(stock_id, start_date):
    try:
        # A. 股價資料
        df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        if df.empty or len(df) < 20: return None
        
        # B. 法人資料
        inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date)
        
        # C. 大戶持股 (每週更新)
        holders = dl.taiwan_stock_holding_shares_per(stock_id=stock_id, start_date=start_date)
        
        # 資料清洗與計算
        df['MA20'] = ta.sma(df['close'], length=20)
        df['Vol_MA20'] = ta.sma(df['Volume'], length=20)
        
        return {"price": df, "inst": inst, "holders": holders}
    except Exception as e:
        return None

def analyze_strategy(data):
    df = data['price']
    inst = data['inst']
    
    if df.empty: return "觀望", 0
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 起漲邏輯：1. 收盤突破20MA 2. 漲幅 > 2% 3. 量增 1.5倍 4. 近三日法人買超
    price_cond = latest['close'] > latest['MA20'] and latest['close'] > prev['close'] * 1.02
    vol_cond = latest['Volume'] > latest['Vol_MA20'] * 1.5
    
    # 安全檢查法人資料
    inst_cond = False
    if not inst.empty:
        recent_inst = inst.tail(3)
        inst_cond = (recent_inst['buy'].sum() - recent_inst['sell'].sum()) > 0
    
    score = 0
    if price_cond: score += 40
    if vol_cond: score += 30
    if inst_cond: score += 30
    
    if score >= 70: return "🔴 強力買入", score
    elif latest['close'] < latest['MA20']: return "🟢 賣出觀望", score
    else: return "🟡 持有觀望", score

# --- 3. 側邊欄與導覽 ---
st.sidebar.title("🚀 飆股監控選單")
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330")
lookback_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

# --- 4. 主介面邏輯 ---
data = fetch_full_data(stock_id, lookback_date)

if data:
    status, score = analyze_strategy(data)
    
    # 頂部儀表板
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("當前訊號", status)
    col2.metric("起漲強度評分", f"{score} 分")
    
    # 回測邏輯：計算過去一年符合訊號後的 5 日漲幅勝率
    df_bt = data['price']
    signals = (df_bt['close'] > df_bt['MA20']) & (df_bt['Volume'] > df_bt['Vol_MA20'] * 1.5)
    total_signals = signals.sum()
    wins = 0
    if total_signals > 0:
        for i in df_bt[signals].index:
            if i + 5 < len(df_bt):
                if df_bt.iloc[i+5]['close'] > df_bt.iloc[i]['close']: wins += 1
        win_rate = round((wins / total_signals) * 100, 1)
        col3.metric("歷史起漲勝率 (5日)", f"{win_rate}%")
    else:
        col3.metric("歷史起漲勝率 (5日)", "N/A")
    
    col4.metric("法人近三日力道", "偏多" if score > 50 else "偏空")

    # --- 繪製專業圖表 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                        row_heights=[0.5, 0.25, 0.25],
                        subplot_titles=("K線與均線", "大戶持股比 (400張以上)", "法人買賣力道"))

    # 主圖
    fig.add_trace(go.Candlestick(x=df_bt['date'], open=df_bt['open'], high=df_bt['high'], 
                                 low=df_bt['low'], close=df_bt['close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_bt['date'], y=df_bt['MA20'], name='20MA', line=dict(color='yellow')), row=1, col=1)

    # 大戶圖 (安全檢查)
    if not data['holders'].empty:
        fig.add_trace(go.Scatter(x=data['holders']['date'], y=data['holders']['percent'], name='大戶持股%', line=dict(color='cyan')), row=2, col=1)
    
    # 法人圖
    if not data['inst'].empty:
        inst_df = data['inst']
        colors = ['red' if x > 0 else 'green' for x in (inst_df['buy'] - inst_df['sell'])]
        fig.add_trace(go.Bar(x=inst_df['date'], y=(inst_df['buy'] - inst_df['sell']), marker_color=colors, name='法人淨買'), row=3, col=1)

    fig.update_layout(height=800, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("⚠️ 無法取得資料，請確認 API 連線或股票代碼是否正確。")

# --- 5. 全市場掃描功能 (示範) ---
if st.sidebar.button("🔍 執行全市場起漲點掃描"):
    st.write("### 🎯 今日潛力起漲標的 (以熱門股為例)")
    sample_list = ['2330', '2317', '2454', '2303', '2603', '3037', '2382', '3231']
    hit_list = []
    
    progress_bar = st.progress(0)
    for idx, s_id in enumerate(sample_list):
        s_data = fetch_full_data(s_id, (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'))
        if s_data:
            s_status, _ = analyze_strategy(s_data)
            if "🔴" in s_status:
                hit_list.append(s_id)
        progress_bar.progress((idx + 1) / len(sample_list))
    
    if hit_list:
        st.success(f"掃描完成！符合起漲點標的：{', '.join(hit_list)}")
    else:
        st.info("今日暫無符合「強力起漲」之標的。")
