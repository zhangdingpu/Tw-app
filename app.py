import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 抓取台積電數據
ticker = "2330.TW"
df = yf.download(ticker, start="2024-07-01")

# 2. 建立子圖：第一列放 K線，第二列放成交量
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    row_heights=[0.7, 0.3])

# 3. 繪製 K線圖 (Candlestick)
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name="TSMC",
    increasing_line_color='#ef5350',  # 漲：亮紅
    decreasing_line_color='#26a69a',  # 跌：亮綠
    increasing_fillcolor='#ef5350',
    decreasing_fillcolor='#26a69a'
), row=1, col=1)

# 4. 繪製成交量 (Volume)
# 根據漲跌設定成交量顏色
colors = ['#ef5350' if close >= open else '#26a69a' 
          for open, close in zip(df['Open'], df['Close'])]

fig.add_trace(go.Bar(
    x=df.index,
    y=df['Volume'],
    marker_color=colors,
    name="Volume"
), row=2, col=1)

# 5. 比照你截圖的黑色主題美化
fig.update_layout(
    title=f"2330 台積電 專業技術分析圖",
    template='plotly_dark', # 深色背景
    xaxis_rangeslider_visible=False, # 隱藏下方滑桿以更像截圖
    showlegend=False,
    height=800,
    paper_bgcolor='#131722', # 深藍黑背景色
    plot_bgcolor='#131722',
    yaxis=dict(gridcolor='#2a2e39'),
    xaxis=dict(gridcolor='#2a2e39')
)

fig.show()
