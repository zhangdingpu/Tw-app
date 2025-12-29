import streamlit as st
import pandas as pd
import pandas_ta as ta

# --- 1. 終極自適應數據清洗函數 ---
def robust_data_cleaning(df):
    """
    自動偵測並修正 FinMind 欄位命名不統一的問題。
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # A. 欄位名稱標準化 (解決 KeyError: 'Volume' 或 'date')
    column_map = {
        'Trading_Volume': 'Volume',
        'vol': 'Volume',
        'Date': 'date',
        'close_price': 'close',
        'open_price': 'open',
        'high_price': 'high',
        'low_price': 'low'
    }
    df = df.rename(columns=column_map)

    # B. 強制轉換小寫，避免大小寫不一報錯
    df.columns = [c.lower() for c in df.columns]

    # C. 檢查關鍵欄位是否存在，若不存在則補 0 (防止崩潰)
    required_cols = ['close', 'open', 'high', 'low', 'volume']
    for col in required_cols:
        if col not in df.columns:
            st.warning(f"⚠️ 數據缺少欄位: {col}，已自動補齊。")
            df[col] = 0
            
    # D. 數值類型轉換 (確保 pandas_ta 計算時不會出錯)
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df

# --- 2. 更新後的數據抓取邏輯 ---
@st.cache_data(ttl=3600)
def fetch_safe_data_v2(stock_id, start_date):
    try:
        raw_df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        
        # 進入終極清洗模組
        df = robust_data_cleaning(raw_df)
        
        if df.empty or len(df) < 5:
            return None

        # 安全計算指標 (使用 df['volume'] 而非 'Volume')
        df['ma20'] = ta.sma(df['close'], length=20)
        df['vol_ma20'] = ta.sma(df['volume'], length=20)
        
        return {"price": df}
    except Exception as e:
        # 捕捉所有錯誤並顯示具體位置，方便你下次排除
        st.error(f"❌ 數據解析發生異常: {type(e).__name__} - {str(e)}")
        return None
