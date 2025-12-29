import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import time

# 1. 頁面配置
st.set_page_config(page_title="AI 趨勢指標系統", layout="wide")

# 2. 抗封鎖抓取函數
@st.cache_data(ttl=3600)
def fetch_data_safe(code):
    time.sleep(random.uniform(0.5, 1.5))
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="2y", timeout=15) 
            if not df.empty: return df
        except: continue
    return pd.DataFrame()

# 3. 核心指標運算與評分邏輯
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
    
    # AI 評分與評級
    scores, ratings = [], []
    for i in range(len(df)):
        if i < 60:
            scores.append(0); ratings.append("None")
            continue
        s, curr, prev = 0, df.iloc[i], df.iloc[i-1]
        # 條件 1: 60MA 斜率向上
        if curr['MA60_Slope'] > 0: s += 20
        # 條件 2: ADX 動能 > 25
        if curr['ADX_14'] > 25: s += 20
        # 條件 3: SuperTrend 狀態
        if curr['SUPERTd_10_4.0'] == 1:
            s += 30
            if prev['SUPERTd_10_4.0'] == -1: s += 10 # 轉折加分
        # 條件 4: 成交量爆發
        if curr['Volume'] > (curr['Vol_MA5'] * 1.5): s += 15
        # 條件 5: RSI 安全區
        if 40 < curr['RSI'] < 75: s += 5
        
        scores.append(s)
        # 定義評級
        if curr['SUPERTd_10_4.0'] == 1:
            ratings.append("Strong Buy" if s >= 85 else "Buy" if s >= 65 else "Wait")
        else:
            ratings.append("Strong Sell" if s <= 25 else "Sell" if s <= 50 else "Wait")
            
    df['AI_Score'] = scores
    df['AI_Rating'] = ratings
    return df

# 4. 回測邏輯：前 3 次交易統計
def get_backtest_results(df):
    trades = []
    in_pos, buy_p, buy_d = False, 0, None
    for i in range(len(df)):
        row = df.iloc[i]
        if not in_pos and row['AI_Rating'] == "Strong Buy":
            in_pos, buy_p, buy_d = True, row['Close'], df.index[i]
        elif in_pos and row['AI_Rating'] in ["Sell", "Strong Sell"]:
            profit = (row['Close'] - buy_p) / buy_p
            trades.append({
                "買入日期": buy_d.strftime('%Y-%m-%d'),
                "賣出日期": df.index[i].strftime('%Y-%m-%d'),
                "漲幅%": f"{profit:.2%}",
                "val": profit
            })
            in_pos = False
    return trades[-3:]

# --- UI 介面 ---
st.title("🤖 AI 趨勢指標匯入系統")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

if stock_input:
    df_raw = fetch_data_safe(stock_input)
    if not df_raw.empty:
        df = calculate_all_signals(df_raw)
        last = df.iloc[-1]
        
        # 頂部評級儀表板
        st.subheader(f"📊 目前評級：{last['AI_Rating']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("AI 總分", f"{int(last['AI_Score'])}")
        c2.metric("ADX 動能", f"{last['ADX_14']:.1f}")
        c3.metric("RSI 熱度", f"{last['RSI']:.1f}")
        c4.metric("量能倍率", f"{last['Volume']/last['Vol_MA5']:.1f}x")

        # 圖表匯入指標
        df_plot = df.tail(150)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
        
        # 主圖: K線 + 60MA + SuperTrend
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA60'], name="60MA", line=dict(color='yellow', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SUPERT_10_4.0'], name="SuperTrend", line=dict(color='cyan', dash='dot', width=1)), row=1, col=1)
        
        # 標註訊號
        buy_sig = df_plot[df_plot['AI_Rating'] == "Strong Buy"]
        sell_sig = df_plot[df_plot['AI_Rating'] == "Strong Sell"]
        fig.add_trace(go.Scatter(x=buy_sig.index, y=buy_sig['Low']*0.97, mode='markers', marker=dict(symbol='triangle-up', size=12, color='#00ff00'), name='🔥 強烈買入'), row=1, col=1)
        fig.add_trace(go.Scatter(x=sell_sig.index, y=sell_sig['High']*1.03, mode='markers', marker=dict(symbol='triangle-down', size=12, color='#ff0000'), name='💀 強烈賣出'), row=1, col=1)

        # 副圖: 成交量
        vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df_plot['Close'], df_plot['Open'])]
        fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 戰績統計表格
        st.markdown("---")
        trades = get_backtest_results(df)
        if trades:
            avg_p = sum([t['val'] for t in trades]) / len(trades)
            st.subheader(f"💡 前 3 次平均表現：{avg_p:.2%}")
            st.table(pd.DataFrame(trades).drop(columns=['val']))
        else:
            st.info("歷史數據中尚未出現完整的 強烈買入 -> 賣出 交易循環。")
    else:
        st.error("資料抓取失敗。")
