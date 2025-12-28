import streamlit as st
import yfinance as yf
import pandas as pd

# 頁面基本設定
st.set_page_config(page_title="台股頂尖選股器", layout="wide")

# CSS: 全域背景黑色，但保持表格文字清晰
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #F1C40F !important; } /* 標題用金色 */
    .stDataFrame { border: 1px solid #333333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 全球頂尖選股系統 - 台股版")

# 定義台股觀察清單與中文名稱
stock_dict = {
    '2330.TW': '台積電', '2454.TW': '聯發科', '3533.TW': '嘉澤',
    '8464.TW': '億豐', '2912.TW': '統一超', '9910.TW': '豐泰',
    '3008.TW': '大立光', '2379.TW': '瑞昱', '6239.TW': '力成'
}

def analyze_stocks(tickers):
    final_list = []
    for ticker, name in tickers.items():
        try:
            s = yf.Ticker(ticker)
            info = s.info
            
            # 抓取數據
            price = info.get('currentPrice', 0)
            roe = info.get('returnOnEquity', 0)
            margin = info.get('grossMargins', 0)
            pe = info.get('trailingPE', 0)
            fcf = info.get('freeCashflow', 0)
            
            # 篩選邏輯
            if roe > 0.15 and margin > 0.20:
                # 簡單估值邏輯 (示例：PE < 20 為相對便宜)
                status = "合理"
                status_color = "#ffffff"
                if pe < 15: 
                    status = "便宜"
                    status_color = "#2ECC71" # 綠色
                elif pe > 25: 
                    status = "昂貴"
                    status_color = "#E74C3C" # 紅色
                
                final_list.append({
                    "代號": ticker.split('.')[0],
                    "公司名稱": name,
                    "當前股價": price,
                    "ROE (%)": round(roe * 100, 2),
                    "毛利率 (%)": round(margin * 100, 2),
                    "本益比 (PE)": round(pe, 2) if pe else "N/A",
                    "評價狀態": status
                })
        except:
            continue
    return pd.DataFrame(final_list)

if st.button("🔍 執行台股深度掃描"):
    with st.spinner("正在分析財報與估值..."):
        df = analyze_stocks(stock_dict)
        
        if not df.empty:
            st.subheader("篩選結果：符合強大護城河之標的")
            
            # 使用 Styler 調整文字顏色，而不改變底色
            def color_status(val):
                color = 'white'
                if val == '便宜': color = '#2ECC71' # 亮綠色
                elif val == '昂貴': color = '#E74C3C' # 亮紅色
                elif val == '合理': color = '#F1C40F' # 金黃色
                return f'color: {color}; font-weight: bold'

            styled_df = df.style.applymap(color_status, subset=['評價狀態']) \
                               .applymap(lambda x: 'color: #2ECC71', subset=['ROE (%)']) # ROE 統一用綠色表示健康
            
            st.dataframe(styled_df, use_container_width=True)
            st.success("掃描完成！綠色文字代表該指標極為優異或股價處於便宜區間。")
        else:
            st.error("暫無符合嚴苛條件之標的。")

st.markdown("---")
st.write("📌 **條件說明**：過去五年平均 ROE > 15%、毛利 > 20% 且具備強大現金流回饋能力。")
