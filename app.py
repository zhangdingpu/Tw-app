import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 系統配置與防崩潰模組 ---
st.set_page_config(layout="wide", page_title="飆股戰情室 Pro")
dl = DataLoader()

def robust_cleaning(df):
    """
    自適應數據清洗：解決不同股票回傳欄位名稱不一的問題
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    # 建立欄位映射表 (解決 KeyError: 'Volume' 等問題)
    column_map = {
        'Trading_Volume': 'volume', 'vol': 'volume', 'Volume': 'volume',
        'Date': 'date', 'Date_Time': 'date',
        'close_price': 'close', 'Close': 'close',
        'open_price': 'open', 'Open': 'open',
        'high_price': 'high', 'High': 'high',
        'low_price': 'low', 'Low': 'low'
    }
    df = df.rename(columns=column_map)
    df.columns = [c.lower() for c in df.columns] # 全轉小寫預防萬一
    
    # 強制數值轉換與缺失值補齊
    cols = ['close', 'open', 'high', 'low', 'volume']
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        else:
            df[c] = 0
            
    return df

# --- 2. 數據抓取邏輯 ---
@st.cache_data(ttl=3600)
def fetch_all_data(stock_id, start_date):
    try:
        # A. 股價
        raw_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        df = robust_cleaning(raw_price)
        if df.empty: return None
        
        # B. 法人 (失敗則回傳空表不報錯)
        try:
            inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date)
        except: inst = pd.DataFrame()
            
        # C. 大戶 (向前推一個月確保資料連續)
        try:
            h_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
            holders = dl.taiwan_stock_holding_shares_per(stock_id=stock_id, start_date=h_start)
        except: holders = pd.DataFrame()
            
        return {"price": df, "inst": inst, "holders": holders}
    except Exception as e:
        st.error(f"⚠️ 數據抓取致命錯誤: {e}")
        return None

# --- 3. 買點偵測算法 ---
def detect_signals(df):
    """
    核心指標：20MA突破 + 1.5倍攻擊量
    """
    df['ma20'] = ta.sma(df['close'], length=20)
    df['vol_ma20'] = ta.sma(df['volume'], length=20)
    
    # 產生訊號：收盤大於MA20 且 量大於均量1.5倍 且 當日收紅
    signals = (df['close'] > df['ma20']) & \
              (df['volume'] > df['vol_ma20'] * 1.5) & \
              (df['close'] > df['open'])
    return signals

# --- 4. UI 介面 ---
st.title("🚀 飆股起漲監控 (終極專業版)")
st.markdown("---")

stock_id = st.sidebar.text_input("📍 輸入股票代碼", value="2330")
lookback = st.sidebar.slider("歷史回溯天數", 60, 500, 200)
start_date = (datetime.now() - timedelta(days=lookback)).strftime('%Y-%m-%d')

if st.sidebar.button("分析籌碼與起漲點"):
    with st.spinner("正在解析數據..."):
        data = fetch_all_data(stock_id, start_date)
        
        if data:
            df = data['price']
            inst = data['inst']
            holders = data['holders']
            
            # 偵測買點
            buy_signals = detect_signals(df)
            
            # --- 儀表板顯示 ---
            latest = df.iloc[-1]
            status = "🔴 起漲訊號發現" if buy_signals.iloc[-1] else "🟡 盤整觀望中"
            
            c1, c2, c3 = st.columns(3)
            c1.metric("診斷結論", status)
            c2.metric("最新股價", f"{latest['close']} 元")
            c3.metric("攻擊量倍數", f"{round(latest['volume']/latest['vol_ma20'], 2)} 倍")

            # --- 繪製專業三層圖表 ---
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25],
                                subplot_titles=("技術面：K線與起漲點箭頭", "籌碼面：400張大戶持股比例", "動力面：法人買賣淨額"))

            # [1] K線與買點標註
            fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], 
                                         low=df['low'], close=df['close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['date'], y=df['ma20'], name='20MA', line=dict(color='yellow', width=1)), row=1, col=1)
            
            # 關鍵：標註紅色起漲箭頭
            signal_df = df[buy_signals]
            fig.add_trace(go.Scatter(x=signal_df['date'], y=signal_df['low'] * 0.98, 
                                     mode='markers', marker=dict(symbol='triangle-up', size=15, color='red'),
                                     name='起漲點'), row=1, col=1)

            # [2] 大戶圖
            if not holders.empty:
                big_holders = holders[holders['level'] >= 10].groupby('date')['percent'].sum().reset_index()
                fig.add_trace(go.Scatter(x=big_holders['date'], y=big_holders['percent'], name='大戶%', line=dict(color='cyan')), row=2, col=1)

            # [3] 法人圖
            if not inst.empty:
                inst_sum = inst.groupby('date').sum(numeric_only=True).reset_index()
                inst_sum['net'] = inst_sum['buy'] - inst_sum['sell']
                colors = ['#ff4b4b' if x > 0 else '#00ff00' for x in inst_sum['net']]
                fig.add_trace(go.Bar(x=inst_sum['date'], y=inst_sum['net'], marker_color=colors, name='法人淨買'), row=3, col=1)

            fig.update_layout(height=850, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # 歷史起漲紀錄表
            st.subheader("📋 近期起漲訊號紀錄")
            st.dataframe(signal_df[['date', 'close', 'volume']].sort_values(by='date', ascending=False))

        else:
            st.error("❌ 無法取得該股票資料，請檢查代碼或日期。")
