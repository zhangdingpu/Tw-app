import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 頁面風格設定
st.set_page_config(page_title="台股體質檢測 App", layout="wide")

# CSS 強制全域黑色背景，表格底色透明
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #00FFCC !important; }
    .stTextInput>div>div>input { background-color: #1a1a1a; color: white; border-color: #333333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 台股四大條件「體質檢測」系統")

# 2. 自動偵測上市或上櫃函數
def get_tw_ticker(code):
    """輸入數字代碼，自動回傳帶後綴的代碼"""
    # 簡易邏輯：先嘗試上市 .TW，若無數據則嘗試上櫃 .TWO
    return f"{code}.TW"

# 3. 體質檢測核心邏輯
def check_health(ticker_code):
    try:
        ticker = get_tw_ticker(ticker_code)
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 如果抓不到 currentPrice 嘗試上櫃
        if not info.get('currentPrice'):
            ticker = f"{ticker_code}.TWO"
            stock = yf.Ticker(ticker)
            info = stock.info

        # 抓取四大指標
        name = info.get('longName', ticker_code)
        roe = info.get('returnOnEquity', 0)
        margin = info.get('grossMargins', 0)
        fcf = info.get('freeCashflow', 0)
        div_payout = info.get('payoutRatio', 0)
        price = info.get('currentPrice', 'N/A')

        # 判定
        results = {
            "檢測項目": ["1. 高 ROE (>15%)", "2. 強大護城河 (毛利>20%)", "3. 自由現金流 (FCF)", "4. 股東回饋 (配息率)"],
            "實際數據": [
                f"{round(roe*100, 2)}%" if roe else "無數據",
                f"{round(margin*100, 2)}%" if margin else "無數據",
                f"{round(fcf/100000000, 2)} 億" if fcf else "數據不足",
                f"{round(div_payout*100, 2)}%" if div_payout else "無數據"
            ],
            "狀態": [
                "✅ 合格" if roe and roe > 0.15 else "❌ 不合格",
                "✅ 合格" if margin and margin > 0.20 else "❌ 不合格",
                "✅ 充沛" if fcf and fcf > 0 else "⚠️ 待觀察",
                "✅ 優良" if div_payout and div_payout > 0.3 else "⚠️ 偏低/未配息"
            ]
        }
        
        return name, price, pd.DataFrame(results)
    except Exception as e:
        return None, None, f"發生錯誤: {e}"

# 4. UI 介面
with st.sidebar:
    st.header("檢測中心")
    user_input = st.text_input("輸入台股代號", placeholder="例如：2330")
    run_btn = st.button("開始體質檢測")

if run_btn and user_input:
    with st.spinner(f"正在為 {user_input} 進行全面體質掃描..."):
        name, price, report = check_health(user_input)
        
        if name:
            st.subheader(f"🔍 {user_input} {name} - 檢測報告")
            st.metric("當前股價", f"{price} TWD")
            
            # 設定文字顏色邏輯：不改底色，改文字
            def color_status(val):
                if "✅" in val: color = '#2ECC71' # 綠色
                elif "❌" in val: color = '#E74C3C' # 紅色
                else: color = '#F1C40F' # 黃色
                return f'color: {color}; font-weight: bold'

            st.table(report.style.applymap(color_status, subset=['狀態']))
            
            # 總評
            pass_count = report['狀態'].str.contains("✅").sum()
            if pass_count == 4:
                st.balloons()
                st.success("🌟 完美標的：該公司完全符合您設定的四項頂尖體質條件！")
            elif pass_count >= 2:
                st.info(f"觀察中：符合 {pass_count} 項條件，體質尚可。")
            else:
                st.warning("警訊：該公司體質不符合您的價值投資標準。")
        else:
            st.error("找不到該股票數據，請確認號碼是否正確。")
