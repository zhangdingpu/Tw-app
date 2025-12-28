import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import mplfinance as mpf # 引入 mplfinance

# 1. 頁面風格設定
st.set_page_config(page_title="台股全能選股雷達", layout="wide")

# CSS 強制黑魂介面
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    h1, h2, h3 { color: #00FFCC !important; }
    .stTextInput>div>div>input { background-color: #1a1a1a; color: white; border-color: #333333; }
    .stMetric { background-color: #111111; padding: 10px; border-radius: 10px; border: 1px solid #333333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 台股全能選股雷達：體質 + 趨勢 + K線圖")

# 2. 輔助函數：台股代碼處理與中文轉換
tw_name_map = {
    '2207': '和泰車', '2308': '台達電', '2317': '鴻海', '2330': '台積電',
    '2379': '瑞昱', '2382': '廣達', '2454': '聯發科', '2912': '統一超',
    '3008': '大立光', '3533': '嘉澤', '6239': '力成', '8464': '億豐',
    '9910': '豐泰'
}

def get_full_ticker(code):
    """偵測是上市(.TW)還是上櫃(.TWO)"""
    t_tw = yf.Ticker(f"{code}.TW")
    if not t_tw.history(period="1d", interval="1d").empty:
        return f"{code}.TW"
    t_two = yf.Ticker(f"{code}.TWO")
    if not t_two.history(period="1d", interval="1d").empty:
        return f"{code}.TWO"
    return None

# 3. 核心檢測與訊號運算
def run_full_analysis(code):
    try:
        ticker_str = get_full_ticker(code)
        if not ticker_str:
            return None, "找不到股票代碼，請確認輸入是否正確。"

        stock = yf.Ticker(ticker_str)
        info = stock.info
        
        # 抓取一年歷史數據繪製K線圖及計算均線
        hist = stock.history(period="1y", interval="1d") 
        if hist.empty:
            return None, "無法取得歷史數據。"

        # --- A. 基本面數據 ---
        name = tw_name_map.get(code, info.get('longName', code))
        price = info.get('currentPrice', hist['Close'].iloc[-1])
        roe = info.get('returnOnEquity', 0)
        margin = info.get('grossMargins', 0)
        fcf = info.get('freeCashflow', 0)
        payout = info.get('payoutRatio', 0)

        # --- B. 技術面訊號 (MA20, MA60, 買賣點標記) ---
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        
        # 買賣點邏輯 (簡單示範)
        # 買點: MA20 上穿 MA60 (黃金交叉) 且當天收盤價高於 MA20
        # 賣點: MA20 下穿 MA60 (死亡交叉) 且當天收盤價低於 MA20
        buy_signals = []
        sell_signals = []
        
        for i in range(1, len(hist)):
            if hist['MA20'].iloc[i-1] <= hist['MA60'].iloc[i-1] and \
               hist['MA20'].iloc[i] > hist['MA60'].iloc[i] and \
               hist['Close'].iloc[i] > hist['MA20'].iloc[i]: # 黃金交叉買點
                buy_signals.append(hist.index[i])
            elif hist['MA20'].iloc[i-1] >= hist['MA60'].iloc[i-1] and \
                 hist['MA20'].iloc[i] < hist['MA60'].iloc[i] and \
                 hist['Close'].iloc[i] < hist['MA20'].iloc[i]: # 死亡交叉賣點
                sell_signals.append(hist.index[i])

        curr_ma20 = hist['MA20'].iloc[-1]
        curr_ma60 = hist['MA60'].iloc[-1]
        
        if price > curr_ma20 and curr_ma20 > curr_ma60:
            trend_signal = "🟢 強勢多頭 (建議持有/加碼)"
        elif price < curr_ma20 and curr_ma20 < curr_ma60:
            trend_signal = "🔴 空頭排列 (建議觀望/減碼)"
        else:
            trend_signal = "🟡 趨勢整理 (區間操作)"

        # --- C. 整合表格數據 ---
        report_data = {
            "檢測指標": ["股東權益報酬率 (ROE)", "毛利率 (護城河)", "自由現金流 (FCF)", "股利配發率", "技術面趨勢"],
            "數值/狀態": [
                f"{round(roe*100, 2)}%" if roe else "數據不足",
                f"{round(margin*100, 2)}%" if margin else "數據不足",
                f"{round(fcf/100000000, 2)} 億" if fcf else "未揭露",
                f"{round(payout*100, 2)}%" if payout else "未配息",
                trend_signal
            ],
            "評斷": [
                "✅ 合格" if roe and roe > 0.15 else "❌ 不合格",
                "✅ 合格" if margin and margin > 0.20 else "❌ 不合格",
                "✅ 充沛" if fcf and fcf > 0 else "⚠️ 待觀察",
                "✅ 穩定" if payout and 0.3 < payout < 0.9 else "⚠️ 偏低或過高",
                "確認買賣時機"
            ]
        }
        
        return name, price, pd.DataFrame(report_data), hist, buy_signals, sell_signals
    except Exception as e:
        return None, f"分析失敗：{e}"

# 4. UI 介面佈局
with st.sidebar:
    st.header("🔍 股票搜尋")
    stock_code = st.text_input("請輸入台股代碼", placeholder="例如: 2330")
    analyze_btn = st.button("執行全方位分析")

if analyze_btn and stock_code:
    name, price, df_report, hist, buy_signals, sell_signals = run_full_analysis(stock_code)
    
    if name:
        # 顯示標題與現價
        st.subheader(f"📊 {name} ({stock_code}) 全方位分析")
        col1, col2 = st.columns(2)
        col1.metric("當前股價", f"{price} TWD")
        col2.write(f"數據更新至: {datetime.datetime.now().strftime('%Y-%m-%d')}")

        # 表格文字顏色邏輯
        def style_report(val):
            color = 'white'
            if "✅" in val or "🟢" in val: color = '#2ECC71' # 綠色
            elif "❌" in val or "🔴" in val: color = '#E74C3C' # 紅色
            elif "⚠️" in val or "🟡" in val: color = '#F1C40F' # 黃色
            return f'color: {color}; font-weight: bold'

        # 顯示基本面與趨勢報告
        st.write("### 📈 體質與訊號檢測表")
        st.table(df_report.style.applymap(style_report, subset=['數值/狀態', '評斷']))
        
        # 繪製 K 線圖
        st.write("### 📉 K 線圖與買賣訊號")
        
        # 處理買賣點為 mplfinance 可接受的格式
        buys = [ (d, hist.loc[d,'Low']*0.99) for d in buy_signals] # 買點標記在K線下方
        sells = [ (d, hist.loc[d,'High']*1.01) for d in sell_signals] # 賣點標記在K線上方

        add_plots = [
            mpf.make_addplot(hist['MA20'], color='cyan', panel=0), # MA20 顏色
            mpf.make_addplot(hist['MA60'], color='magenta', panel=0), # MA60 顏色
        ]

        # 創造一個圖形物件
        fig, axlist = mpf.plot(hist, 
                               type='candle', 
                               style='yahoo', # yahoo 風格較簡潔
                               title=f"{name} ({stock_code}) K線圖",
                               ylabel='股價',
                               addplot=add_plots,
                               volume=True,
                               ylabel_lower='成交量',
                               figscale=1.5, # 放大圖片
                               returnfig=True)
        
        # 在 K 線圖上標記買賣點 (使用 scatter)
        # 買點用綠色三角形，賣點用紅色三角形
        # 確保 buy_signals 和 sell_signals 裡面的日期是 datetime 物件
        for date, price_loc in buys:
            axlist[0].scatter(date, price_loc, marker='^', s=200, color='green', label='買點', zorder=5) # zorder確保在最上層

        for date, price_loc in sells:
            axlist[0].scatter(date, price_loc, marker='v', s=200, color='red', label='賣點', zorder=5)

        # 顯示 K 線圖
        st.pyplot(fig)

        # 最終投資建議
        st.markdown("---")
        st.write("### 📢 專業分析師總結")
        pass_count = df_report['評斷'].str.contains("✅").sum()
        if pass_count >= 3 and "🟢" in df_report.loc[4, "數值/狀態"]:
            st.success("💎 該股體質極佳且處於上升趨勢，K線圖顯示潛在買點，是高品質的投資機會。")
        elif pass_count >= 3:
            st.info("💡 體質優秀但趨勢尚未啟動，建議透過K線圖尋找適當分批佈局時機。")
        else:
            st.warning("⚠️ 體質未達頂尖標準，K線圖顯示風險，建議謹慎操作。")
            
    else:
        st.error(price) # price 現在包含錯誤訊息

# 5. 腳註
st.caption("數據來源: yfinance, mplfinance | 投資有風險，本程式僅供參考。")

