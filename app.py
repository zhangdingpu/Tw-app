import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面風格
st.set_page_config(page_title="量化選股 V5.0 - 大波段趨勢版", layout="wide")

# 2. 超級趨勢計算 (SuperTrend)
def pandas_supertrend(df, period=10, multiplier=3):
    hl2 = (df['High'] + df['Low']) / 2
    # 計算 ATR
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['Close'].shift(1)), 
               abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(period).mean()
    
    # 計算上軌與下軌
    df['upperband'] = hl2 + (multiplier * df['ATR'])
    df['lowerband'] = hl2 - (multiplier * df['ATR'])
    df['in_trend'] = True

    for i in range(1, len(df.index)):
        curr, prev = i, i-1
        if df['Close'].iloc[curr] > df['upperband'].iloc[prev]:
            df.iat[curr, df.columns.get_loc('in_trend')] = True
        elif df['Close'].iloc[curr] < df['lowerband'].iloc[prev]:
            df.iat[curr, df.columns.get_loc('in_trend')] = False
        else:
            df.iat[curr, df.columns.get_loc('in_trend')] = df['in_trend'].iloc[prev]
            if df['in_trend'].iloc[curr] and df['lowerband'].iloc[curr] < df['lowerband'].iloc[prev]:
                df.iat[curr, df.columns.get_loc('lowerband')] = df['lowerband'].iloc[prev]
            if not df['in_trend'].iloc[curr] and df['upperband'].iloc[curr] > df['upperband'].iloc[prev]:
                df.iat[curr, df.columns.get_loc('upperband')] = df['upperband'].iloc[prev]
    return df

# 3. 核心指標計算
def calculate_trend_metrics(hist):
    df = hist.copy()
    
    # 技術檔位百分位 (0-100)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + gain/loss))
    def p(s): return s.rolling(252, min_periods=10).apply(lambda x: (x < x[-1]).mean() * 100)
    df['Score'] = (p(df['RSI']) * 0.5) + (p(df['Close'].rolling(20).apply(lambda x: (x[-1]-x.mean())/x.std() if x.std() != 0 else 0)) * 0.5)
    
    # 計算 SuperTrend
    df = pandas_supertrend(df)
    
    # 大波段買賣訊號
    # 買入：趨勢轉多 且 檔位在低位區(<50)
    df['Buy'] = np.where(
        (df['in_trend'] == True) & (df['in_trend'].shift(1) == False) & (df['Score'] < 50),
        df['Low'] * 0.95, np.nan
    )
    
    # 賣出：趨勢轉空 (不論檔位，趨勢斷了就走)
    df['Sell'] = np.where(
        (df['in_trend'] == False) & (df['in_trend'].shift(1) == True),
        df['High'] * 1.05, np.nan
    )
    return df

# --- UI 介面實作 (略，結構同 V4.0 但改用 calculate_trend_metrics) ---
