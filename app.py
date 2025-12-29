import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import time

# --- 1. 初始化與配置 ---
st.set_page_config(layout="wide", page_title="飆股戰情室 Pro")

# 建議：在此處填入你的 FinMind Token 以獲取更穩定的數據
# dl = DataLoader()
# dl.login_by_token("YOUR_TOKEN_HERE") 
dl = DataLoader() 

# --- 2. 強健型數據抓取函數 ---
@st.cache_data(ttl=3600)
def fetch_safe_data(stock_id, start_date):
    try:
        # A. 抓取日股價 (基礎)
        df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        if df is None or df.empty:
            return None
        
        # B. 抓取法人資料 (防禦處理)
        try:
            inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date)
        except:
            inst = pd.DataFrame()
            
        # C. 抓取大戶持股 (時間補償邏輯)
        try:
            # 大戶資料通常每週末更新，往前多抓一個月確保有舊資料可以對比
            h_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
            holders = dl.taiwan_stock_holding_shares_per(stock_id=stock_id, start_date=h_start)
        except:
            holders = pd.DataFrame()

        # D. 計算技術指標 (確保不因空值報錯)
        df['MA20'] = ta.sma(df['close'], length=20)
        df['Vol_MA20'] = ta.sma(df['Volume'], length=20)
        
        return {"price": df, "inst": inst, "holders": holders}
    except Exception as e:
        st.error(f"⚠️ 數據解析發生錯誤: {e}")
        return None

# --- 3. 判斷邏輯與 UI ---
st.title("🚀 飆股個股監控 (專業防禦版)")

stock_id = st.sidebar.text_input("輸入股票代碼 (例: 2330)", value="2330")
lookback_days = st.sidebar.slider("回溯天數", 60, 365, 180)
start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

if st.sidebar.button("獲取分析報告"):
    with st.spinner(f"正在分析 {stock_id} 籌碼結構..."):
        data = fetch_safe_data(stock_id, start_date)
        
        if data:
            df = data['price']
            inst = data['inst']
            holders = data['holders']
            
            # 儀表板
            latest = df.iloc[-1]
            c1, c2, c3 = st.columns(3)
            
            # 起漲判斷邏輯
            is_ma_up = latest['close'] > latest['MA20']
            vol_up = latest['Volume'] > latest['Vol_MA20'] * 1.5
            
            status = "🔴 起漲點確認" if (is_ma_up and vol_up) else "🟡 盤整觀望"
            c1.metric("診斷結果", status)
            c2.metric("最新收盤價", f"{latest['close']} 元")
            c3.metric("今日成交量", f"{int(latest['Volume']):,}")

            # --- 繪圖區 ---
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25],
                                subplot_titles=("技術面 (均線)", "籌碼面 (大戶持股%)", "法人力道 (買賣超)"))

            # K線圖
            fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], 
                                         low=df['low'], close=df['close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['date'], y=df['MA20'], name='20MA', line=dict(color='yellow')), row=1, col=1)

            # 大戶持股% (僅在有資料時顯示)
            if not holders.empty:
                # 篩選 400 張以上的大戶類別 (通常是 level 10-15)
                big_holders = holders[holders['level'] >= 10] 
                fig.add_trace(go.Scatter(x=big_holders['date'], y=big_holders['percent'], name='大戶%'), row=2, col=1)

            # 法人買賣超 (僅在有資料時顯示)
            if not inst.empty:
                # 這裡統一計算每日三大法人淨買賣
                inst_sum = inst.groupby('date').sum(numeric_only=True).reset_index()
                inst_sum['net'] = inst_sum['buy'] - inst_sum['sell']
                colors = ['red' if x > 0 else 'green' for x in inst_sum['net']]
                fig.add_trace(go.Bar(x=inst_sum['date'], y=inst_sum['net'], marker_color=colors, name='法人淨額'), row=3, col=1)

            fig.update_layout(height=800, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error("❌ 無法抓取資料，可能是代碼錯誤或 API 限制，請稍後再試。")
