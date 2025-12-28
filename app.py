import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 頁面配置
st.set_page_config(page_title="專業個股分析系統", layout="wide")

st.title("🔍 全球個股即時分析系統")
st.markdown("輸入股票代碼（美股如 `AAPL`, 台股如 `2330.TW`）即可獲取深度報告")

# 1. 搜尋列
search_ticker = st.text_input("請輸入股票代碼", value="NVDA").upper()

if search_ticker:
    try:
        # 抓取數據
        stock = yf.Ticker(search_ticker)
        info = stock.info
        hist = stock.history(period="1y") # 抓取一年歷史數據

        if hist.empty:
            st.error("找不到該股票數據，請檢查代碼是否正確。")
        else:
            # 2. 顯示基本面資訊儀表板
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("現價", f"{info.get('currentPrice', 'N/A')} {info.get('currency')}")
            with col2:
                roe = info.get('returnOnEquity', 0) * 100
                st.metric("ROE", f"{roe:.2f}%")
            with col3:
                pe = info.get('trailingPE', 'N/A')
                st.metric("本益比 (P/E)", f"{pe}")
            with col4:
                rev_growth = info.get('revenueGrowth', 0) * 100
                st.metric("營收成長 (YoY)", f"{rev_growth:.2f}%")

            # 3. 繪製互動式 K 線圖 (Candlestick)
            st.subheader(f"📈 {info.get('shortName')} 股價走勢圖")
            fig = go.Figure(data=[go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name="K線"
            )])
            
            # 加入 200日均線 (MA200)
            hist['MA200'] = hist['Close'].rolling(window=200).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'], name="MA200", line=dict(color='orange', width=2)))
            
            fig.update_layout(xaxis_rangeslider_visible=False, height=600)
            st.plotly_chart(fig, use_container_width=True)

            # 4. 分析師觀點 (邏輯判斷)
            st.subheader("💡 系統綜合評估")
            advice = []
            if roe > 15: advice.append("✅ 高效獲利能力 (ROE > 15%)")
            if info.get('currentPrice', 0) > info.get('twoHundredDayAverage', 0): advice.append("✅ 趨勢偏多 (現價高於 MA200)")
            if rev_growth > 20: advice.append("✅ 強勁成長力道 (YoY > 20%)")
            
            if advice:
                for item in advice:
                    st.write(item)
            else:
                st.write("該標的目前未觸發任何核心選股邏輯，建議審慎觀察。")

    except Exception as e:
        st.error(f"發生錯誤: {e}")

st.sidebar.markdown("### 開發筆記\n1. 輸入 `2330.TW` 查詢台積電\n2. 數據由 yfinance 提供\n3. 圖表支援滾輪縮放")
