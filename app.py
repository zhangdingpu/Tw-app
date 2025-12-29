import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面配置
st.set_page_config(page_title="台股波段全能掃描器 V12.0", layout="wide")
st.title("🎯 台股優質成長股 - 大波段掃描系統")

# 2. 定義優質清單 (已排除循環股與國防股)
MASTER_LIST = {
    "核心半導體/IC設計": ["2330", "2454", "3034", "3035", "3661", "3443", "6415", "2379", "3374", "6147"],
    "AI伺服器與組裝": ["2317", "2308", "2382", "3231", "6669", "2357", "2377", "2353", "2324"],
    "中小型設備/材料": ["3131", "3583", "6187", "6640", "1560", "3680", "1773", "4768"],
    "AI散熱/零組件": ["3017", "3324", "3653", "2313", "2368", "3044", "8210", "3013"],
    "優質金融/穩定內需": ["2881", "2882", "2886", "2891", "2884", "5880", "2912", "5904", "9941"]
}

# 3. 核心邏輯 (大波段抓取 + 族群性判定)
def analyze_stock(df):
    if len(df) < 100: return False, 0, 0
    # SuperTrend 參數 (4.0 倍 ATR 以抓取 30%+ 漲幅)
    multiplier = 4.0
    hl2 = (df['High'] + df['Low']) / 2
    tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    atr = tr.rolling(12).mean()
    up_band = hl2 + (multiplier * atr)
    
    # 判斷趨勢轉強 (今日站上，昨日在下)
    is_breakout = (df['Close'].iloc[-1] > up_band.iloc[-2]) and (df['Close'].iloc[-2] <= up_band.iloc[-3])
    # 位階分數
    score = (df['Close'].rolling(252).apply(lambda x: (x < x[-1]).mean() * 100)).iloc[-1]
    # 量能與動能
    vol_confirm = df['Volume'].iloc[-1] > (df['Volume'].rolling(10).mean().iloc[-1] * 1.1)
    ma5_up = df['Close'].iloc[-1] > df['Close'].rolling(5).mean().iloc[-1]
    
    return (is_breakout and score < 75 and vol_confirm and ma5_up), score, df['Close'].iloc[-1]

# 4. 掃描介面
if st.button("🚀 執行全方位波段掃描"):
    all_hits = []
    group_hits_count = {g: 0 for g in MASTER_LIST.keys()}
    st.write("🔍 正在掃描全市場優質標的...")
    progress = st.progress(0)
    
    total_len = sum(len(v) for v in MASTER_LIST.values())
    counter = 0
    
    for group, codes in MASTER_LIST.items():
        for code in codes:
            try:
                df = yf.Ticker(f"{code}.TW").history(period="1y")
                hit, score, price = analyze_stock(df)
                if hit:
                    all_hits.append({"族群": group, "代號": code, "股價": price, "位階分數": round(score, 1)})
                    group_hits_count[group] += 1
                counter += 1
                progress.progress(counter / total_len)
                time.sleep(0.1) # 略微等待，避免被封鎖
            except: continue
            
    if all_hits:
        st.success(f"✅ 掃描完成！發現 {len(all_hits)} 檔正要起漲的波段種子。")
        res_df = pd.DataFrame(all_hits)
        st.table(res_df)
        
        # 族群共振警告
        for g, count in group_hits_count.items():
            if count >= 2:
                st.warning(f"🔥 【{g}】出現集體轉強訊號！這是抓到 30% 以上漲幅的關鍵時機。")
    else:
        st.info("目前清單標的尚未出現符合『低位階 + 剛站上趨勢線』的買點。")

st.markdown("---")
st.subheader("💡 使用者指南")
st.write("1. **耐心**：本系統設計初衷是抓 30% 以上漲幅，因此訊號不會天天有。")
st.write("2. **防守**：買入後，若收盤跌破 SuperTrend 防禦線（約 $4.0 \times ATR$ 距離）則嚴格出場。")
st.write("3. **過濾**：已為您過濾掉景氣循環股，降低因報價波動導致波段腰斬的風險。")
