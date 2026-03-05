import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser # ニュース取得用
from datetime import datetime

# --- 設定とページ構成 ---
st.set_page_config(page_title="Gemini-Standard FX AI", layout="wide")
st.title("🛡️ Ultimate Safe-AI FX Analyzer")
st.caption("統計学とAI判断に基づいた年利50%目標モデル")

# --- サイドバー：ユーザー設定 ---
st.sidebar.header("⚙️ 運用設定")
pair_options = {"米ドル/円": "USDJPY=X", "ユーロ/米ドル": "EURUSD=X", "英ポンド/円": "GBPJPY=X"}
selected_pair = st.sidebar.selectbox("監視通貨ペア", list(pair_options.keys()))
risk_percent = st.sidebar.slider("1トレードの許容損失 (%)", 0.5, 2.0, 1.0)

# --- 1. リアルタイム・ニュース取得（AI分析の種） ---
def get_fx_news():
    # ロイターのビジネスニュース等をサンプルとして取得
    url = "https://news.google.com/rss/search?q=FX+Forex+Market+News&hl=ja&gl=JP&ceid=JP:ja"
    feed = feedparser.parse(url)
    news_items = feed.entries[:3] # 直近3件
    return news_items

# --- 2. データ取得とテクニカル計算 ---
@st.cache_data(ttl=600)
def fetch_data(ticker):
    df = yf.download(ticker, period="60d", interval="1h")
    # 安全運用のためのテクニカル指標
    df.ta.sma(length=20, append=True) # 短期
    df.ta.sma(length=50, append=True) # 長期
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=14, append=True) # ボラティリティ（損切り用）
    return df.dropna()

df = fetch_data(pair_options[selected_pair])
last_bar = df.iloc[-1]

# --- 3. AIセンチメント判定（シミュレーション・ロジック） ---
# 本来はここにOpenAI APIを接続し、news_itemsを解析させます
st.sidebar.subheader("🌐 AIニュース分析 (自動判定)")
news_list = get_fx_news()
for n in news_list:
    st.sidebar.write(f"・{n.title[:40]}...")

# デモ用：ニュースに特定の単語が含まれるかで簡易スコアリング
news_text = "".join([n.title for n in news_list]).lower()
ai_score = 0.0
if "上昇" in news_text or "strong" in news_text or "high" in news_text: ai_score += 0.3
if "下落" in news_text or "weak" in news_text or "low" in news_text: ai_score -= 0.3
ai_score = st.sidebar.slider("AI 補正スコア (自動+手動調整)", -1.0, 1.0, ai_score)

# --- 4. 安全・売買ロジック（年利50%への道） ---
# 条件A: トレンド一致
trend_up = last_bar['SMA_20'] > last_bar['SMA_50']
trend_down = last_bar['SMA_20'] < last_bar['SMA_50']

# 条件B: 過熱感なし
not_overbought = last_bar['RSI_14'] < 60
not_oversold = last_bar['RSI_14'] > 40

# 条件C: ボラティリティが安定（安全第一）
is_calm = last_bar['ATRr_14'] < df['ATRr_14'].mean() * 1.5

# 最終シグナル
signal = "📊 待機 (Neutral)"
color = "white"
if ai_score > 0.2 and trend_up and not_overbought and is_calm:
    signal = "🚀 安全な買いサイン (Strong Buy)"
    color = "#00ff00"
elif ai_score < -0.2 and trend_down and not_oversold and is_calm:
    signal = "📉 安全な売りサイン (Strong Sell)"
    color = "#ff4b4b"

# --- 5. メイン画面の構築 ---
c1, c2, c3 = st.columns(3)
c1.metric("現在値", f"{last_bar['Close']:.3f}")
c2.metric("RSI", f"{last_bar['RSI_14']:.1f}")
with c3:
    st.markdown(f"<div style='text-align:center; padding:10px; border-radius:10px; background-color:{color}; color:black; font-weight:bold;'>{signal}</div>", unsafe_allow_html=True)

# チャート表示
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="価格"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='yellow'), name="SMA20"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='cyan'), name="SMA50"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], line=dict(color='white'), name="RSI"), row=2, col=1)

fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- 6. 資金管理・実行プラン ---
st.subheader("📝 トレード実行プラン（年利50%目標値）")
if "サイン" in signal:
    atr = last_bar['ATRr_14']
    sl_dist = atr * 2.0 # ATRの2倍を損切りに設定
    tp_dist = sl_dist * 1.5 # リスクリワード1:1.5
    
    entry_p = last_bar['Close']
    sl_p = entry_p - sl_dist if "買い" in signal else entry_p + sl_dist
    tp_p = entry_p + tp_dist if "買い" in signal else entry_p - tp_dist
    
    col_a, col_b, col_c = st.columns(3)
    col_a.info(f"**推奨エントリー**\n\n{entry_p:.3f}")
    col_b.error(f"**損切り価格(SL)**\n\n{sl_p:.3f}")
    col_c.success(f"**利確価格(TP)**\n\n{tp_p:.3f}")
    
    st.write(f"💡 **アドバイス:** 現在のATRに基づき、1回あたりの損失を資金の{risk_percent}%に抑えるロットを計算して下さい。")
else:
    st.info("AIが「最も安全」と判断する条件が揃うまで待機中です。無理な取引を控えることが年利50%への最短ルートです。")

st.markdown("---")
st.caption("※本アプリは情報の提供を目的としており、利益を保証するものではありません。投資判断は自己責任でお願いします。")

