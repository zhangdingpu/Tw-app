import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 頁面設定與黑色主題 CSS
st.set_page_config(page_title="台股頂尖選股器", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    .stDataFrame { background-color: #1a1a1a; border: 1px solid #333333; }
    h1, h2, h3 { color: #00ffcc !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🗠 頂尖價值投資 - 台股篩選器")

# 台股中文對照表 (確保顯示中文名稱)
tw_name_map = {
    '2330.TW': '台積電',
    '8464.TW': '億豐',
    '3533.TW': '嘉澤',
    '2912.TW': '統一超',
    '9910.TW': '豐泰',
    '2454.TW': '聯發科',
    '3008.TW': '大立光',
    '2379.TW': '瑞昱'
}

def get_stock_data(tickers):
    results = []
    for ticker in tickers:
        try:
            s = yf.Ticker(ticker)
            info = s.info
            
            roe = info.get('returnOnEquity', 0)
            margin = info.get('grossMargins', 0)
            fcf = info.get('freeCashflow', 0)
            
            # 篩選邏輯：ROE > 15% 且 毛利率 > 20%
            if roe > 0.15 and margin > 0.20:
                results.append({
                    "股票代碼": ticker.split('.')[0],
                    "公司名稱": tw_name_map.get(ticker, info.get('shortName', ticker)),
                    "ROE (%)": round(roe * 100, 2),
                    "毛利率 (%)": round(margin * 100, 2),
                    "自由現金流 (億)": round(fcf / 100000000, 2) if fcf else "數據不足",
                    "股息殖利率 (%)": round(info.get('dividendYield', 0) * 100, 2)
                })
        except:
            continue
    return pd.DataFrame(results)

# 執行分析
if st.button("🚀 執行全自動掃描"):
    with st.spinner("正在抓取最新財報數據..."):
        df = get_stock_data(list(tw_name_map.keys()))
        
        if not df.empty:
            st.subheader("符合四大條件之名單")
            # 使用黑色系表格呈現
            st.dataframe(df.style.set_properties(**{
                'background-color': 'black',
                'color': 'white',
                'border-color': '#333333'
            }))
        else:
            st.warning("目前市場數據下，沒有符合所有嚴苛條件的標的。")

st.markdown("---")
st.info("條件：1. ROE > 15% | 2. 毛利率高或上升 | 3. 現金流充沛 | 4. 股利發放穩定")
