import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt

# 1. 頁面風格設定
st.set_page_config(page_title="四維度量化選股終極版", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #00FFCC !important; }
    .stMetric { background-color: #111111; padding: 15px; border-radius: 10px; border: 1px solid #333333; }
    .stTable { background-color: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 四維度高報酬低風險系統 V1.5")

# 2. 核心計算函數：技術百分位檔位
def get_technical_percentile_score(hist):
    lookback = 252  # 參考過去一年的數據
    
    # --- 指標計算 ---
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    hist['RSI'] = 100 - (100 / (1 + gain/loss))
    
    # BIAS (乖離率)
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['BIAS'] = (hist['Close'] - hist['MA20']) / hist['MA20'] * 100
    
    # W%R (威廉指標)
    high_14 = hist['High'].rolling(window=14).max()
    low_14 = hist['Low'].rolling(window=14).min()
    hist['WR'] = (high_14 - hist['Close']) / (high_14 - low_14) * -100
    
    # ATR (波動率)
    hist['TR'] = np.maximum(hist['High'] - hist['Low'], 
                 np.maximum(abs(hist['High'] - hist['Close'].shift(1)), 
                 abs(hist['Low'] - hist['Close'].shift(1))))
    hist['ATR'] = hist['TR'].rolling(window=14).mean()

    # --- 百分位計算 ---
    def calc_p(series):
        if len(series.dropna()) < 10: return 50
        current = series.iloc[-1]
        window = series.dropna().tail(lookback)
        return (window < current).mean() * 100

    rsi_p = calc_p(hist['RSI'])
    bias_p = calc_p(hist['BIAS'])
    wr_p = calc_p(hist['WR'])
    atr_p = calc_p(hist['ATR'])
    
    # 綜合技術檔位分數 (越高代表相對越熱)
    tech_score = (rsi_p * 0.3) + (bias_p * 0.3) + (wr_p * 0.2) + (atr_p * 0.2)
    return round(tech_score, 2), rsi_p, bias_p, wr_p, atr_p

# 3. 主分析程式
def run_ultimate_analysis(code):
    try:
        # 資料抓取 (上市/上櫃自動判斷)
        ticker_str = f"{code}.TW"
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="1y")
        if hist.empty:
            ticker_str = f"{code}.TWO"
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period="1y")
        
        if hist.empty: return None, "找不到數據"

        info = stock.info
        price = info.get('currentPrice', hist['Close'].iloc[-1])
        
        # --- A. 基本面 (預估模型) ---
        eps_ttm = info.get('trailingEps', 0)
        growth_rate = 0.15 # 預設成長率 15% (方案B暫替)
        est_eps = eps_ttm * (1 + growth_rate)
        est_pe = price / est_eps if est_eps > 0 else 0
        peg = est_pe / (growth_rate * 100) if growth_rate > 0 else 0
        
        valuation = "💎 極低估" if peg < 0.75 else ("✅ 合理" if peg < 1.2 else "⚠️ 高估")
        val_color = "#2ECC71" if peg < 0.75 else ("#F1C40F" if peg < 1.2 else "#E74C3C")

        # --- B. 技術面 (百分位檔位) ---
        tech_idx, rsi_p, bias_p, wr_p, atr_p = get_technical_percentile_score(hist)
        
        # --- C. 買賣訊號與情緒 ---
        buy_sig = []
        sell_sig = []
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        for i in range(1, len(hist)):
            if hist['MA20'].iloc[i-1] <= hist['MA60'].iloc[i-1] and hist['MA20'].iloc[i] > hist['MA60'].iloc[i]:
                buy_sig.append((hist.index[i], hist['Low'].iloc[i]*0.97))
            elif hist['MA20'].iloc[i-1] >= hist['MA60'].iloc[i-1] and hist['MA20'].iloc[i] < hist['MA60'].iloc[i]:
                sell_sig.append((hist.index[i], hist['High'].iloc[i]*1.03))

        # --- D. 四維度綜合評分 (100分制) ---
        # 基本面分 (PEG越低分越高)
        f_score = 25 if peg < 1 else 15
        # 技術面分 (檔位越低分越高，代表便宜)
        t_score = 25 if tech_idx < 30 else (10 if tech_idx > 70 else 20)
        # 趨勢分
        trend_score = 25 if price > hist['MA20'].iloc[-1] else 0
        # 情緒分 (低波動且低乖離時分數高)
        s_score = 25 if bias_p < 40 else 10
        
        total_score = f_score + t_score + trend_score + s_score

        report_df = pd.DataFrame({
            "指標維度": ["前瞻估值 (PEG)", "技術檔位 (Percentile)", "情緒狀態 (方案B)", "趨勢動能"],
            "數據數值": [f"PEG: {round(peg, 2)}", f"{tech_idx} 分", "資減價穩 (模擬)" if bias_p < 40 else "散戶過熱", f"MA20斜率向上" if price > hist['MA20'].iloc[-1] else "盤整"],
            "評價評價": [valuation, "極低位" if tech_idx < 20 else ("極高位" if tech_idx > 80 else "中性"), "🟢 適合佈局" if bias_p < 30 else "🟡 觀望", "✅ 多頭" if price > hist['MA20'].iloc[-1] else "❌ 空頭"]
        })

        return {
            "name": info.get('longName', code), "price": price, "report": report_df, 
            "hist": hist, "buys": buy_sig, "sells": sell_sig,
            "score": total_score, "val_color": val_color
        }, None
    except Exception as e:
        return None, str(e)

# 4. UI 介面實作
with st.sidebar:
    st.header("🔍 系統核心")
    stock_input = st.text_input("輸入台股代號", value="2330")
    run_btn = st.button("執行全維度分析")

if run_btn:
    data, err = run_ultimate_analysis(stock_input)
    if err:
        st.error(f"分析出錯：{err}")
    else:
        # 第一排：核心數據
        c1, c2, c3 = st.columns(3)
        c1.metric("當前股價", f"{data['price']} TWD")
        c2.metric("系統綜合信心指數", f"{data['score']} 分")
        c3.markdown(f"### 預估評價：<span style='color:{data['val_color']}'>{data['report'].iloc[0, 2]}</span>", unsafe_allow_html=True)

        # 第二排：報表
        st.write("### 📊 四維度量化診斷報告")
        st.table(data['report'].style.applymap(lambda x: 'color: #2ECC71' if '✅' in x or '🟢' in x or '💎' in x else ('color: #E74C3C' if '❌' in x or '🔴' in x or '⚠️' in x else 'color: white')))

        # 第三排：圖表
        st.write(f"### 📉 買賣訊號視覺化 (技術檔位分數: {data['score']})")
        ap = [mpf.make_addplot(data['hist']['MA20'], color='cyan'), mpf.make_addplot(data['hist']['MA60'], color='magenta')]
        fig, ax = mpf.plot(data['hist'], type='candle', style='charles', addplot=ap, volume=True, figratio=(16,9), returnfig=True)
        for b in data['buys']: ax[0].scatter(b[0], b[1], marker='^', color='lime', s=150, zorder=5)
        for s in data['sells']: ax[0].scatter(s[0], s[1], marker='v', color='red', s=150, zorder=5)
        st.pyplot(fig)

st.caption("註：技術檔位分數 0-100，越低代表相對歷史價格越便宜。")
