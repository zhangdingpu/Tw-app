import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 獲取台積電數據
ticker = "2330.TW"
df = yf.download(ticker, start="2025-07-01")

# 2. 建立包含兩個子圖的畫布 (上圖: K線, 下圖: 成交量)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, subplot_titles=(f'{ticker} 日K線圖', '成交量'), 
                    row_width=[0.2, 0.7])

# 3. 繪製 K線圖
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name="K線",
    increasing_line_color='#ef5350', # 漲（紅）
    decreasing_line_color='#26a69a'  # 跌（綠）
), row=1, col=1)

# 4. 繪製成交量
fig.add_trace(go.Bar(
    x=df.index,
    y=df['Volume'],
    name="成交量",
    marker_color='gray'
), row=2, col=1)

# 5. 圖表格式美化
fig.update_layout(
    xaxis_rangeslider_visible=False,
    template='plotly_dark', # 使用深色主題，貼近你提供的截圖
    height=800,
    showlegend=False
)

fig.show()
