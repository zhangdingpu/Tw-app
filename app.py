import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎設定
st.set_page_config(page_title="五維策略：收盤價訊號終端", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.main { background-color: #0e1117; color: white; }</style>", unsafe_allow_html=True)

ASSET_LIST = {
    "市值前十大公司": {
        "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2308.TW": "台達電",
        "2881.TW": "富邦金", "2882.TW": "國泰金", "2382.TW": "廣達", "2891.TW": "中信金",
        "3711.TW": "日月光投控", "2412.TW": "中華電"
    },
    "熱門 ETF": {
        "0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00919.TW": "群益精選高息"
    }
}

@st.cache_data(ttl=300)
def get_signal_data(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="max", auto_adjust=True)
    if df.empty: return df, None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # --- 核心指標計算 ---
    df['rsi_r'] = ta.rsi(df['Close'], length=14).rolling(252).rank(pct=True) * 100
    df['bias_20'] = ((df['Close'] - df['Close'].rolling(20).mean()) / df['Close'].rolling(20).mean()).rolling(252).rank(pct=True) * 100
    macd = ta.macd(df['Close'], fast=6, slow=13, signal=5)
    df['macd_r'] = macd['MACDh_6_13_5'].rolling(252).rank(pct=True) * 100
    
    # 綜合檔位線 (HMA)
    df['Final_Score'] = ta.hma((df['bias_20'] * 0.5 + df['rsi_r'] * 0.3 + df['macd_r'] * 0.2), length=10)
    df['Lower_Bound'] = df['Final_Score'].rolling(252).quantile(0.12)
    df['Upper_Bound'] = df['Final_Score'].rolling(252).quantile(0.88)
    
    # --- 訊號邏輯 ---
    df['Signal'] = "HOLD"
    vol_ma = df['Volume'].rolling(20).mean()
    # 買入：分數低於下限 且 成交量萎縮
    df.loc[(df['Final_Score'] <= df['Lower_Bound']) & (df['Volume'] < vol_ma), 'Signal'] = "BUY"
    # 賣出：分數高於上限 且 轉折向下
    df.loc[(df['Final_Score'] >= df['Upper_Bound']) & (df['Final_Score'] < df['Final_Score'].shift(1)), 'Signal'] = "SELL"
    
    return df, ticker.info

# --- 分頁系統 ---
tab1, tab2 = st.tabs(["🎯 即時買賣指令", "📈 訊號圖表分析"])

with tab1:
    st.subheader("🚀 2025 全資產收盤價訊號總覽")
    all_symbols = {}
    for cat in ASSET_LIST: all_symbols.update(ASSET_LIST[cat])
    
    radar_results = []
    for sym, name in all_symbols.items():
        scan_df, _ = get_signal_data(sym)
        if not scan_df.empty:
            curr = scan_df.iloc[-1]
            prev = scan_df.iloc[-2]
            
            sig_text = "⚪ 觀望"
            if curr['Signal'] == "BUY": sig_text = "🟢 買入 (抄底)"
            elif curr['Signal'] == "SELL": sig_text = "🔴 賣出 (獲利)"
            elif curr['Final_Score'] < 15: sig_text = "🟡 準備買入"
            elif curr['Final_Score'] > 85: sig_text = "🟠 準備賣出"

            radar_results.append({
                "標的": name, 
                "收盤價": f"{curr['Close']:.2f}",
                "今日指令": sig_text,
                "檔位分數": round(curr['Final_Score'], 1),
                "昨日分數": round(prev['Final_Score'], 1)
            })
    st.table(pd.DataFrame(radar_results))

with tab2:
    st.sidebar.header("🔍 標的選擇")
    cat = st.sidebar.selectbox("類別", list(ASSET_LIST.keys()))
    asset_name = st.sidebar.selectbox("標的", list(ASSET_LIST[cat].values()))
    sid = [k for k, v in ASSET_LIST[cat].items() if v == asset_name][0]
    
    df, info = get_signal_data(sid)
    if not df.empty:
        st.subheader(f"📈 {asset_name} ({sid})：收盤價買賣訊號圖")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 1. 價格線
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="收盤價", line=dict(color="#FFFFFF", width=2)), secondary_y=False)
        
        # 2. 修正後的檔位線 (將 opacity 移出 line 字典)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Final_Score'], 
            name="檔位", 
            line=dict(color="#00BFFF", width=1.5),
            opacity=0.5 # 正確的設定位置
        ), secondary_y=True)
        
        # 3. 標記買賣點
        buys = df[df['Signal'] == "BUY"]
        sells = df[df['Signal'] == "SELL"]
        fig.add_trace(go.Scatter(x=buys.index, y=buys['Close'], mode='markers', marker=dict(color="#00FF00", size=12, symbol="triangle-up"), name="買"), secondary_y=False)
        fig.add_trace(go.Scatter(x=sells.index, y=sells['Close'], mode='markers', marker=dict(color="#FF0000", size=12, symbol="triangle-down"), name="賣"), secondary_y=False)
        
        fig.update_xaxes(range=[df.index[-1] - pd.Timedelta(days=90), df.index[-1]])
        fig.update_layout(height=450, template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- 歷史明細分頁 ---
        st.markdown("---")
        st.subheader("🏛️ 歷史買賣指令明細")
        full_h = df.tail(252).copy()
        recs = []
        for i in range(len(full_h)-1, -1, -1):
            r = full_h.iloc[i]
            if r['Signal'] != "HOLD":
                recs.append({
                    "日期": full_h.index[i].strftime('%Y/%m/%d'),
                    "執行動作": "🟢 買入" if r['Signal'] == "BUY" else "🔴 賣出",
                    "成交價": f"{r['Close']:.2f}",
                    "檔位分數": f"{r['Final_Score']:.1f}"
                })
        
        if 'p_sig_v5' not in st.session_state: st.session_state.p_sig_v5 = 0
        
        # 確保分頁不溢出
        total_recs = len(recs)
        max_p = max(0, (total_recs - 1) // 10)
        st.session_state.p_sig_v5 = min(st.session_state.p_sig_v5, max_p)

        c1, c2, c3 = st.columns([1, 2, 1])
        with c1: 
            if st.button("⬅️ 上一頁") and st.session_state.p_sig_v5 > 0: st.session_state.p_sig_v5 -= 1
        with c3: 
            if st.button("下一頁 ➡️") and st.session_state.p_sig_v5 < max_p: st.session_state.p_sig_v5 += 1
        
        start_idx = st.session_state.p_sig_v5 * 10
        st.table(pd.DataFrame(recs[start_idx : start_idx+10]))
