import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from groq import Groq
from datetime import datetime

# ページ設定
st.set_page_config(page_title="学内共有SNS & AI Assistant", layout="wide")

# --- 1. 接続設定 ---
# Googleスプレッドシートへの接続（読み込み用）
conn = st.connection("gsheets", type=GSheetsConnection)

# Groq AIの初期化
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. データの管理（セッション状態） ---
# 複数人でアクセスした際に、投稿を保持するための入れ物
if "timeline_data" not in st.session_state:
    try:
        # 起動時にスプレッドシートからこれまでの投稿を読み込む
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        st.session_state.timeline_data = conn.read(spreadsheet=url, ttl="0s")
    except:
        # 読み込めない場合は空のデータフレームを作成
        st.session_state.timeline_data = pd.DataFrame(columns=["user", "text", "time"])

# --- 3. サイドバー：AIアシスタント ---
with st.sidebar:
    st.header("🤖 AIアシスタント")
    
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if ai_prompt := st.chat_input("AIに相談する..."):
        st.session_state.ai_messages.append({"role": "user", "content": ai_prompt})
        with st.chat_message("user"):
            st.markdown(ai_prompt)
            
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "あなたは学内SNSの優秀な助手です。"},
                    *st.session_state.ai_messages
                ]
            )
            ans = response.choices[0].message.content
            st.markdown(ans)
        st.session_state.ai_messages.append({"role": "assistant", "content": ans})

# --- 4. メイン画面：SNSタイムライン ---
st.title("𝕏 学内共有タイムライン")

with st.expander("いまどうしてる？", expanded=True):
    user_name = st.text_input("名前", value="ゲストユーザー")
    tweet_text = st.text_area("内容を入力...")
    
    if st.button("投稿する"):
        if tweet_text:
            # 新しい投稿を作成
            new_post = pd.DataFrame([{
                "user": user_name,
                "text": tweet_text,
                "time": datetime.now().strftime("%m/%d %H:%M")
            }])
            
            # 画面上のデータに追加（エラーが出るconn.updateは使わない）
            st.session_state.timeline_data = pd.concat(
                [st.session_state.timeline_data, new_post], ignore_index=True
            )
            
            st.success("投稿されました！")
            st.rerun()

st.divider()

# タイムラインの表示
df = st.session_state.timeline_data
if not df.empty:
    # 新しい投稿が上に来るように逆順でループ
    for index, row in df.iloc[::-1].iterrows():
        st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px; background-color: white;">
                <span style="font-weight:bold; color:#1DA1F2;">{row['user']}</span> 
                <span style="color:gray; font-size:0.8em;">@{row['user']} · {row['time']}</span><br>
                <div style="margin-top:5px; color: black;">{row['text']}</div>
            </div>
        """, unsafe_allow_html=True)