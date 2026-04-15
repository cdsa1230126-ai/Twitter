import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from groq import Groq
from datetime import datetime

# ページ設定
st.set_page_config(page_title="本格SNS & AI Assistant", layout="wide")

# --- 1. 接続設定 ---
# Googleスプレッドシートへの接続
conn = st.connection("gsheets", type=GSheetsConnection)

# Groq AIの初期化 (Secretsに保存したAPIキーを使用)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. データの読み込み ---
def fetch_data():
    return conn.read(ttl="0s") # 常に最新を取得

df = fetch_data()

# --- 3. サイドバー：AIアシスタント (Groq版) ---
with st.sidebar:
    st.header("🤖 AIアシスタント")
    if ai_prompt := st.chat_input("AIに質問..."):
        with st.chat_message("user"):
            st.markdown(ai_prompt)
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": ai_prompt}]
            )
            st.markdown(response.choices[0].message.content)

# --- 4. メイン画面：SNSタイムライン ---
st.title("𝕏 学内共有タイムライン")

with st.expander("いまどうしてる？"):
    tweet_text = st.text_area("内容を入力...", label_visibility="collapsed")
    if st.button("投稿"):
        if tweet_text:
            # 新しい行を作成
            new_data = pd.DataFrame([{
                "user": "ゲストユーザー",
                "text": tweet_text,
                "time": datetime.now().strftime("%m/%d %H:%M")
            }])
            # 既存のデータに追加
            updated_df = pd.concat([df, new_data], ignore_index=True)
            # スプレッドシートを更新
            conn.update(data=updated_df)
            st.success("投稿されました！")
            st.rerun()

st.divider()

# タイムライン表示（新しい順）
for index, row in df.iloc[::-1].iterrows():
    st.markdown(f"""
        <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px;">
            <span style="font-weight:bold; color:#1DA1F2;">{row['user']}</span> 
            <span style="color:gray; font-size:0.8em;">{row['time']}</span><br>
            <div style="margin-top:5px;">{row['text']}</div>
        </div>
    """, unsafe_allow_html=True)