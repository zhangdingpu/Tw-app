import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎設定
st.set_page_config(page_title="五維策略：極限底部署終端", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.main { background-color: #0e1117; color: white; }</style>", unsafe_allow_html=True)

ASSET_LIST = {
    "市值前十大公司": {
        "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2308.TW": "台達電",
        "2881.TW": "富邦金", "2882.TW": "國泰金", "2382.TW": "廣達", "2891.TW": "中信金",
        "3711.TW": "日月光投控", "2412.TW": "中華電"
    },
    "熱門 ETF": {
        "0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00919.TW": "群益精選高息", "00929.TW": "復華台灣科技優息"
    }
}

@st.cache_data(ttl=300)
def get_extreme_data(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="max", auto_adjust=True)
    if df.empty: return df, None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # --- 1. 極限底指標計算 ---
    # 乖離率分位數：判斷價格是否跌到年度極端
    df['bias_20'] = ((df['Close'] - df['Close'].rolling(20).mean()) / df['Close'].rolling(20).mean())
    df['bias_rank'] = df['bias_20'].rolling(252).rank(pct=True) * 100
    
    # RSI 與 MACD 排名
    df['rsi_r'] = ta.rsi(df['Close'], length=14).rolling(252).rank(pct=True) * 100
    macd = ta.macd(df['Close'], fast=6, slow=13, signal=5)
    df['macd_r'] = macd['MACDh_6_13_5'].rolling(252).rank(pct=True) * 100
    
    # 量能衰竭指標：成交量是否萎縮（代表沒人要賣了）
    df['vol_ma'] = df['Volume'].rolling(20).mean()
    df['vol_exhaustion'] = df['Volume'] < (df['vol_ma'] * 0.8) # 量縮至均量80%以下
    
    # --- 2. 綜合檔位線 (HMA 平滑) ---
    # 權重分配：乖離率(50%) + RSI(30%) + MACD(20%) -> 側重於「超跌」
    raw_scores = (df['bias_rank'] * 0.5 + df['rsi_r'] * 0.3 + df['macd_r'] * 0.2)
    df['Final_Score'] = ta.hma(raw_scores, length=10)
    
    # --- 3. 訊號定義 ---
    # 定義 Lower Bound 為 10% (更嚴格的極限)
    df['Lower_Bound'] = df['Final_Score'].rolling(252).quantile(0.10)
    # 抄底訊號：分數低於邊界 且 出現量能衰竭
    df['is_bottom'] = (df['Final_Score'] <= df['Lower_Bound']) & df['vol_exhaustion']
    
    return df, ticker.info

# --- UI 介面 ---
tab1, tab2 = st.tabs(["📡 2025 極限排行榜", "🔍 深度轉折分析"])

with tab1:
    st.subheader("📊 2025 全資產超跌掃描 (量能衰竭引擎)")
    all_symbols = {}
    for cat in ASSET_LIST: all_symbols.update(ASSET_LIST[cat])
    
    radar_results = []
    for sym, name in all_symbols.items():
        scan_df, _ = get_extreme_data(sym)
        if not scan_df.empty:
            curr = scan_df.iloc[-1]
            # 2025 績效回測
            bt_df = scan_df[scan_df.index >= "2025-01-01"]
            y_days = bt_df[bt_df['is_bottom']]
            roi = (((1000000 / len(y_days) / y_days['Close']).sum() * curr['Close'] - 1000000) / 10000) if len(y_days) > 0 else 0
            
            status = "🟡 極限底" if curr['is_bottom'] else "⚪ 穩定"
            radar_results.append({
                "標的": name, "目前價格": round(curr['Close'], 1), 
                "2025回報": f"{roi:.2f}%", "狀態": status, "檔位": round(curr['Final_Score'], 1)
            })
    
    st.table(pd.DataFrame(radar_results).sort_values("2025回報", ascending=False))

with tab2:
    st.sidebar.header("🔍 標的選擇")
    cat = st.sidebar.selectbox("類別", list(ASSET_LIST.keys()))
    asset_name = st.sidebar.selectbox("標的", list(ASSET_LIST[cat].values()))
    sid = [k for k, v in ASSET_LIST[cat].items() if v == asset_name][0]
    
    df, info = get_extreme_data(sid)
    if not df.empty:
        st.subheader(f"📈 {asset_name} ({sid})：極限底監控")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 股價與檔位
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="價", line=dict(color="#FFFFFF", width=2)), secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['Final_Score'], name="檔", line=dict(color="#00BFFF", width=2.5)), secondary_y=True)
        fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Bound'], line=dict(color="rgba(255, 215, 0, 0.4)", dash='dot')), secondary_y=True)
        
        # 標記星星 (極限底)
        bottoms = df[df['is_bottom']]
        fig.add_trace(go.Scatter(x=bottoms.index, y=bottoms['Final_Score'], mode='markers', marker=dict(color="#FFD700", size=12, symbol="star"), name="極限買點"), secondary_y=True)
        
        fig.update_xaxes(range=[df.index[-1] - pd.Timedelta(days=60), df.index[-1]])
        fig.update_layout(height=450, template="plotly_dark", showlegend=False, margin=dict(l=50, r=50, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # --- 分頁紀錄查詢 ---
        st.markdown("---")
        st.subheader("🏛️ 歷史紀錄 (10筆/頁)")
        full_h = df.tail(252).copy()
        all_recs = []
        for i in range(len(full_h)-1, -1, -1):
            r = full_h.iloc[i]
            all_recs.append({
                "日期": full_h.index[i].strftime('%Y/%m/%d'),
                "訊號": "🟡 極限底" if r['is_bottom'] else "",
                "價格": f"{r['Close']:.2f}",
                "量能狀態": "量能衰竭" if r['vol_exhaustion'] else "量能活躍",
                "檔位分數": f"{r['Final_Score']:.1f}"
            })
        
        if 'pg_idx' not in st.session_state: st.session_state.pg_idx = 0
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1: 
            if st.button("⬅️ 上一頁"): st.session_state.pg_idx = max(0, st.session_state.pg_idx - 1)
        with c3: 
            if st.button("下一頁 ➡️"): st.session_state.pg_idx += 1
        
        st.table(pd.DataFrame(all_recs[st.session_state.pg_idx*10 : st.session_state.pg_idx*10+10]))

        st.info("💡 **操作核心**：\n1. **乖離率分位數**：幫你判斷目前股價是否處於一年來最超跌的 10% 區間。\n2. **量能衰竭**：確認沒人想賣了，通常這就是波段最低點。\n3. **HMA 檔位線**：線條轉平或向上轉折時，通常是反彈起點。")
