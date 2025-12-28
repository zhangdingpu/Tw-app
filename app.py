import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import mplfinance as mpf
import matplotlib.pyplot as plt

# 頁面風格設定
st.set_page_config(page_title="台股全能選股雷達", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #00FFCC !important; }
    .stTextInput>div>div>input { background-color: #1a1a1a; color: white; border-color: #333333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 台股全能選股雷達：體質 + 趨勢 + K線圖")

# 核心分析函數：確保回傳格式統一，避免 ValueError
def run_full_analysis(code):
    try:
        # 1. 判斷代碼後綴
        ticker_str = f"{code}.TW"
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="1y")
        
        if hist.empty:
            ticker_str = f"{code}.TWO"
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period="1y")

        if hist.empty:
            return None, "查無此股票數據"

        # 2. 抓取基本面
        info = stock.info
        name = info.get('longName', code)
        price = info.get('currentPrice', hist['Close'].iloc[-1])
        roe = info.get('returnOnEquity', 0)
        margin = info.get('grossMargins', 0)
        fcf = info.get('freeCashflow', 0)
        payout = info.get('payoutRatio', 0)

        # 3. 計算技術指標
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        
        # 4. 產生買賣訊號
        buy_signals = []
        sell_signals = []
        for i in range(1, len(hist)):
            # 黃金交叉
            if hist['MA20'].iloc[i-1] <= hist['MA60'].iloc[i-1] and hist['MA20'].iloc[i] > hist['MA60'].iloc[i]:
                buy_signals.append((hist.index[i], hist['Low'].iloc[i] * 0.98))
            # 死亡交叉
            elif hist['MA20'].iloc[i-1] >= hist['MA60'].iloc[i-1] and hist['MA20'].iloc[i] < hist['MA60'].iloc[i]:
                sell_signals.append((hist.index[i], hist['High'].iloc[i] * 1.02))

        # 5. 整理報表
        trend = "🟢 強勢多頭" if price > hist['MA20'].iloc[-1] > hist['MA60'].iloc[-1] else \
                ("🔴 空頭排列" if price < hist['MA20'].iloc[-1] < hist['MA60'].iloc[-1] else "🟡 趨勢整理")

        report_df = pd.DataFrame({
            "指標": ["ROE (>15%)", "毛利率 (>20%)", "自由現金流", "股利發售", "趨勢訊號"],
            "數據": [f"{round(roe*100,2)}%", f"{round(margin*100,2)}%", f"{round(fcf/100000000,2)}億", f"{round(payout*100,2)}%", trend],
            "狀態": ["✅ 合格" if roe > 0.15 else "❌ 不足", "✅ 合格" if margin > 0.2 else "❌ 不足", 
                    "✅ 充沛" if fcf > 0 else "⚠️ 觀察", "✅ 穩定" if 0.3 < payout < 0.9 else "⚠️ 觀望", "圖表顯示"]
        })

        # 回傳一個包含所有資料的 Dictionary，避免解構賦值錯誤
        result = {
            "name": name, "price": price, "report": report_df, 
            "hist": hist, "buys": buy_signals, "sells": sell_signals
        }
        return result, None

    except Exception as e:
        return None, str(e)

# UI 介面
with st.sidebar:
    st.header("🔍 搜尋中心")
    stock_code = st.text_input("輸入台股代號", value="2330")
    analyze_btn = st.button("開始分析")

if analyze_btn:
    data, error = run_full_analysis(stock_code)
    
    if error:
        st.error(f"分析失敗：{error}")
    else:
        # 正確地從 Dictionary 取值
        st.subheader(f"📊 {data['name']} ({stock_code}) - 現價: {data['price']} TWD")
        
        # 顯示體質表
        st.table(data['report'].style.applymap(lambda x: 'color: #2ECC71' if '✅' in x or '🟢' in x else ('color: #E74C3C' if '❌' in x or '🔴' in x else 'color: white')))

        # 繪製 K 線圖
        st.write("### 📉 歷史趨勢與買賣訊號 (▲買入 ▼賣出)")
        ap = [mpf.make_addplot(data['hist']['MA20'], color='cyan'), mpf.make_addplot(data['hist']['MA60'], color='magenta')]
        
        fig, axlist = mpf.plot(data['hist'], type='candle', style='charles', addplot=ap, volume=True, figratio=(16,9), returnfig=True, tight_layout=True)

        for b in data['buys']: axlist[0].scatter(b[0], b[1], marker='^', color='lime', s=100)
        for s in data['sells']: axlist[0].scatter(s[0], s[1], marker='v', color='red', s=100)
            
        st.pyplot(fig)
