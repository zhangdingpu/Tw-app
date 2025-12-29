import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# 1. 頁面設定
st.set_page_config(page_title="台股波段成長掃描器", layout="wide")
st.title("🎯 台股大波段起漲掃描器 (避開景氣循環/國防)")

# 2. 核心掃描與大波段邏輯 (30%+ 潛力版本)
def analyze_wave(df):
    if len(df) < 100: return False, 0, 0
    
    # SuperTrend 大波段設定
    multiplier = 4.0
    period = 12
    hl2 = (df['High'] + df['Low']) / 2
    df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(period).mean()
    df['UpBand'] = hl2 + (multiplier * df['ATR'])
    
    # 判斷趨勢轉強 (站上防禦線)
    is_breakout = (df['Close'].iloc[-1] > df['UpBand'].iloc[-2]) and (df['Close'].iloc[-2] <= df['UpBand'].iloc[-3])
    
    # 位階分數 (低於 60 分確保利潤空間)
    score = (df['Close'].rolling(252).apply(lambda x: (x < x[-1]).mean() * 100)).iloc[-1]
    
    # 量能確認 (量增 1.1 倍即可)
    vol_confirm = df['Volume'].iloc[-1] > (df['Volume'].rolling(10).mean().iloc[-1] * 1.1)
    
    # 價格位置 (距離低點不能漲超過 15%，否則不算起漲)
    low_20 = df['Low'].tail(20).min()
    too_high = df['Close'].iloc[-1] > (low_20 * 1.15)
    
    return (is_breakout and score < 60 and vol_confirm and not too_high), score, df['Close'].iloc[-1]

# 3. 掃描清單 (已剔除景氣循環與國防)
# 聚焦：半導體、AI伺服器、IC設計、優質金融
SCAN_LIST = [
    "2330", "2317", "2454", "2308", "2382", "3231", "6669", "2357", "2412", # 電子/權值
    "2881", "2882", "2886", "2891", "2884", "5880", "2892", # 金融
    "3034", "3035", "3661", "3443", "6415", # 高價/IC設計
    "2379", "3008", "2377", "2353", "2324"  # 電子週邊
]

if st.button("開始篩選起漲波段股"):
    results = []
    st.write("🔍 正在分析優質成長標的...")
    progress = st.progress(0)
    
    for i, code in enumerate(SCAN_LIST):
        try:
            df = yf.Ticker(f"{code}.TW").history(period="1y")
            hit, score, price = analyze_wave(df)
            if hit:
                results.append({"代號": code, "目前股價": price, "位階分數": round(score, 1), "建議": "🔥 剛起漲 (30%+ 潛力)"})
            time.sleep(0.3) # 避免 Rate Limit
            progress.progress((i + 1) / len(SCAN_LIST))
        except: continue
        
    if results:
        st.success(f"找到 {len(results)} 檔符合條件標的")
        st.table(pd.DataFrame(results))
    else:
        st.warning("目前市場位階較高，暫無符合『底部剛放量起漲』的標的。請耐心等待回檔訊號。")

st.info("💡 為什麼不選景氣循環股？\n因為航運、鋼鐵容易因為報價見頂就暴跌。我們選的標的有產業護城河，波段一旦發動，漲勢較能持續。")
