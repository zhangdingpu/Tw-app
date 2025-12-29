import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import time

st.set_page_config(page_title="AI 趨勢評分與回測系統", layout="wide")

@st.cache_data(ttl=3600)
def fetch_data_safe(code):
    time.sleep(random.uniform(0.5, 1.5))
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="2y", timeout=15) # 回測需要更長數據，改為 2y
            if not df.empty: return df
        except: continue
    return pd.DataFrame()

# --- 核心邏輯：計算所有日期的評分與評級 ---
def calculate_all_signals(df):
    df = df.copy()
    # 指標運算
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['MA60_Slope'] = df['MA60'].diff(3)
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    st_data = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=4.0)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['Vol_MA5'] = df['Volume'].rolling(5).mean()
    df = pd.concat([df, adx, st_data], axis=1)
    
    # 逐日計算評分
    scores = []
    ratings = []
    for i in range(len(df)):
        if i < 60: # 初始數據不足
            scores.append(0); ratings.append("None")
            continue
        
        s = 0
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        if curr['MA60_Slope'] > 0: s += 20
        if curr['ADX_14'] > 25: s += 20
        if curr['SUPERTd_10_4.0'] == 1:
            s += 30
            if prev['SUPERTd_10_4.0'] == -1: s += 10
        if curr['Volume'] > (curr['Vol_MA5'] * 1.5): s += 15
        if 40 < curr['RSI'] < 75: s += 5
        
        scores.append(s)
        # 評級分類
        if curr['SUPERTd_10_4.0'] == 1:
            ratings.append("Strong Buy" if s >= 85 else "Buy" if s >= 65 else "Wait")
        else:
            ratings.append("Strong Sell" if s <= 25 else "Sell" if s <= 50 else "Wait")
            
    df['AI_Score'] = scores
    df['AI_Rating'] = ratings
    return df

# --- 回測邏輯：抓取前 3 次交易紀錄 ---
def backtest_top_3(df):
    trades = []
    in_position = False
    buy_price = 0
    buy_date = None
    
    # 由舊到新掃描
    for i in range(len(df)):
        row = df.iloc[i]
        # 進場條件：出現第一次強烈買入 (且目前未持股)
        if not in_position and row['AI_Rating'] == "Strong Buy":
            in_position = True
            buy_price = row['Close']
            buy_date = df.index[i]
            
        # 出場條件：出現第一次賣出或強烈賣出 (且目前持股中)
        elif in_position and row['AI_Rating'] in ["Sell", "Strong Sell"]:
            sell_price = row['Close']
            sell_date = df.index[i]
            profit = (sell_price - buy_price) / buy_price
            trades.append({
                "買入日期": buy_date.strftime('%Y-%m-%d'),
                "賣出日期": sell_date.strftime('%Y-%m-%d'),
                "買入價": f"{buy_price:.2f}",
                "賣出價": f"{sell_price:.2f}",
                "漲幅%": f"{profit:.2%}"
            })
            in_position = False
            
    # 回傳最近的 3 次
    return trades[-3:] if trades else []

# --- UI 介面 ---
st.title("🤖 AI 趨勢評分 + 戰績回測系統")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

if stock_input:
    df_raw = fetch_data_safe(stock_input)
    if not df_raw.empty:
        df_processed = calculate_all_signals(df_raw)
        last = df_processed.iloc[-1]
        
        # 1. 顯示目前的診斷評級 (與之前相同)
        st.subheader(f"📊 目前診斷：{stock_input}")
        # (這裡可保留你之前的 st.metric 儀表板，為簡潔先省略)
        
        # 2. 顯示回測戰績
        st.markdown("---")
        st.subheader("🚩 歷史戰績回測 (最近 3 次完整交易)")
        history_trades = backtest_top_3(df_processed)
        
        if history_trades:
            # 用表格呈現
            st.table(pd.DataFrame(history_trades))
            
            # 計算平均漲幅
            total_p = sum([float(t['漲幅%'].replace('%','')) for t in history_trades]) / 100
            st.write(f"💡 **前 3 次平均表現：{total_p/len(history_trades):.2%}**")
        else:
            st.info("目前歷史數據中尚未捕捉到完整的「強烈買入至賣出」交易區間。")

        # 3. 繪圖 (縮小至 150 天方便觀察)
        df_plot = df_processed.tail(150)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA60'], name="60MA", line=dict(color='yellow')), row=1, col=1)
        
        # 標註強烈買入點 (地圖釘)
        buy_signals = df_plot[df_plot['AI_Rating'] == "Strong Buy"]
        fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.98, mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name='強烈買入訊號'), row=1, col=1)
        
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("資料抓取失敗。")
