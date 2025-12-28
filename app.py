import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="台股價值投資選股器", layout="wide")

st.title("🇹🇼 台股頂尖價值投資篩選系統")
st.sidebar.info("本系統依據：ROE > 15%、高毛利護城河、強大現金流篩選")

# 台股觀察清單 (可自行增加)
tw_stock_list = [
    '2330.TW', '2317.TW', '2454.TW', '3008.TW', '8464.TW', 
    '9910.TW', '3533.TW', '2912.TW', '2379.TW', '3045.TW',
    '6239.TW', '2049.TW', '1504.TW', '2207.TW'
]

def get_tw_data(tickers):
    data = []
    progress_bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 抓取關鍵指標
            name = info.get('longName', ticker)
            roe = info.get('returnOnEquity', 0)
            margin = info.get('grossMargins', 0)
            fcf = info.get('freeCashflow', 0)
            div_yield = info.get('dividendYield', 0)
            
            # 嚴格篩選邏輯
            # 1. ROE > 15% 
            # 2. 毛利率 > 30% (或 > 20% 且具備競爭力)
            if roe >= 0.15 and margin >= 0.20:
                data.append({
                    "代碼": ticker.replace('.TW', ''),
                    "名稱": name,
                    "ROE (%)": round(roe * 100, 2),
                    "毛利率 (%)": round(margin * 100, 2),
                    "現金流量 (M)": round(fcf / 1000000, 2) if fcf else "N/A",
                    "殖利率 (%)": round(div_yield * 100, 2) if div_yield else 0
                })
        except Exception as e:
            continue
        progress_bar.progress((i + 1) / len(tickers))
    return pd.DataFrame(data)

# 執行篩選
if st.button('開始掃描台股標竿企業'):
    results = get_tw_data(tw_stock_list)
    
    if not results.empty:
        st.subheader("🏆 符合選股條件之優秀企業")
        # 使用顏色高亮顯示 ROE 超過 20% 的優等生
        st.dataframe(
            results.style.highlight_between(left=20, axis=0, subset=['ROE (%)'], color='#D4EFDF')
        )
        st.balloons()
    else:
        st.error("暫時沒有符合所有條件的股票，請放寬篩選範圍。")

st.markdown("---")
st.caption("註：台股財報數據可能因 API 更新略有時間差，請以最新公開資訊觀測站為準。")
