import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面配置
st.set_page_config(page_title="台股波段全能導航 V13.0", layout="wide")
st.title("🛡️ 台股優質成長股 - 波段導航系統")

# 2. 定義優質清單 (已排除循環股與國防股)
MASTER_LIST = {
    "核心半導體/IC設計": ["2330", "2454", "3034", "3035", "3661", "3443", "6415", "2379", "3374", "6147"],
    "AI伺服器與組裝": ["2317", "2308", "2382", "3231", "6669", "2357", "2377", "2353", "2324"],
    "中小型設備/材料": ["3131", "3583", "6187", "6640", "1560", "3680", "1773", "4768"],
    "AI散熱/零組件": ["3017", "3324", "3653", "2313", "2368", "3044", "8210", "3013"],
    "優質金融/穩定內需": ["2881", "2882", "2886", "2891", "2884", "5880", "2912", "5904", "9941"]
}

# 3. 核心運算函數
def calculate_indicators(df, mult=4.0):
    df = df.copy()
    # SuperTrend
    hl2 = (df['High'] + df['Low']) / 2
    tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    atr = tr.rolling(12).mean()
    df['UpBand'] = hl2 + (mult * atr)
    df['DnBand'] = hl2 - (mult * atr)
    df['Trend'] = True
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['UpBand'].iloc[i-1]: df.iat[i, df.columns.get_loc('Trend')] = True
        elif df['Close'].iloc[i] < df['DnBand'].iloc[i-1]: df.iat[i, df.columns.get_loc('Trend')] = False
        else:
            df.iat[i, df.columns.get_loc('Trend')] = df['Trend'].iloc[i-1]
            if df['Trend'].iloc[i] and df['DnBand'].iloc[i] < df['DnBand'].iloc[i-1]: df.iat[i, df.columns.get_loc('DnBand')] = df['DnBand'].iloc[i-1]
            if not df['Trend'].iloc[i] and df['UpBand'].iloc[i] > df['UpBand'].iloc[i-1]: df.iat[i, df.columns.get_loc('UpBand')] = df['UpBand'].iloc[i-1]
    df['ST_Line'] = np.where(df['Trend'], df['DnBand'], df['UpBand'])
    # Score
    df['Score'] = (df['Close'].rolling(252).apply(lambda x: (x < x[-1]).mean() * 100))
    return df

# --- 側邊欄：功能切換 ---
mode = st.sidebar.radio("選擇功能", ["📊 全市場掃描", "🔍 個股深度診斷"])

if mode == "📊 全市場掃描":
    if st.button("啟動全方位掃描"):
        all_hits = []
        st.write("🔍 正在分析優質標的...")
        progress = st.progress(0)
        total = sum(len(v) for v in MASTER_LIST.values())
        curr = 0
        for group, codes in MASTER_LIST.items():
            for code in codes:
                try:
                    df = yf.Ticker(f"{code}.TW").history(period="1y")
                    df = calculate_indicators(df)
                    # 買入訊號條件
                    hit = (df['Trend'].iloc[-1] and not df['Trend'].iloc[-2] and df['Score'].iloc[-1] < 75)
                    if hit:
                        all_hits.append({"族群": group, "代號": code, "股價": round(df['Close'].iloc[-1], 1), "位階": round(df['Score'].iloc[-1], 1)})
                except: pass
                curr += 1
                progress.progress(curr/total)
        if all_hits:
            st.success(f"發現 {len(all_hits)} 檔種子標的")
            st.table(pd.DataFrame(all_hits))
        else:
            st.info("目前尚無符合起漲條件標的。")

else:
    stock_code = st.sidebar.text_input("輸入台股代號 (如: 2330)", value="2330")
    if st.sidebar.button("開始診斷"):
        data = yf.Ticker(f"{stock_code}.TW").history(period="2y")
        if not data.empty:
            df = calculate_indicators(data).tail(250)
            
            # 建立圖表
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
            # K線
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
            # SuperTrend 線 (變色處理)
            line_color = ['#00FFCC' if t else '#FF4444' for t in df['Trend']]
            fig.add_trace(go.Scatter(x=df.index, y=df['ST_Line'], name="波段防禦線", line=dict(color='cyan', width=2, dash='dot')), row=1, col=1)
            
            # 成交量
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color='rgba(100,100,100,0.5)'), row=2, col=1)
            
            fig.update_layout(height=800, template="plotly_dark", hovermode="x unified")
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            st.plotly_chart(fig, use_container_width=True)
            
            # 診斷文字
            status = "🚀 多頭波段中" if df['Trend'].iloc[-1] else "🛑 空頭整理中"
            st.metric("趨勢狀態", status)
            st.write(f"💡 **操作建議**：只要收盤沒跌破 **{df['ST_Line'].iloc[-1]:.1f}**，30% 的波段目標就繼續持有。")
