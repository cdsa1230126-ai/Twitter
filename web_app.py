import streamlit as st
import ollama
import os
from datetime import datetime

# ページの設定
st.set_page_config(page_title="SNS & Grok-like AI", layout="wide")

# --- 1. 知識の準備 (RAG) ---
def load_knowledge():
    if os.path.exists("knowledge.txt"):
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "学内知識：現在、特になし"

knowledge = load_knowledge()

# --- 2. データ管理（タイムライン用とAIチャット用を分ける） ---
if "timeline" not in st.session_state:
    st.session_state.timeline = [] # SNSの投稿
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = [] # AIとのチャット履歴

# ---------------------------------------------------------
# 【左側：サイドバー】Grok風AIアシスタント
# ---------------------------------------------------------
with st.sidebar:
    st.header("🤖 AIアシスタント")
    st.caption("授業や履修の相談はこちらへ")
    
    # チャット履歴を表示
    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # AIへの入力
    if ai_prompt := st.chat_input("AIに質問する..."):
        st.session_state.ai_messages.append({"role": "user", "content": ai_prompt})
        with st.chat_message("user"):
            st.markdown(ai_prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = ollama.chat(model='qwen2.5:1.5b', messages=[
                    {'role': 'system', 'content': f"あなたは学内SNSの横に常駐する優秀な助手です。知識：{knowledge}"},
                    *st.session_state.ai_messages
                ])
                ans = response['message']['content']
                st.markdown(ans)
        st.session_state.ai_messages.append({"role": "assistant", "content": ans})

# ---------------------------------------------------------
# 【右側：メイン画面】SNSタイムライン
# ---------------------------------------------------------
st.title("𝕏 学内タイムライン")

# 投稿フォーム
with st.expander("いまどうしてる？（投稿する）", expanded=True):
    tweet_text = st.text_area("内容を入力...", label_visibility="collapsed")
    if st.button("投稿"):
        if tweet_text:
            new_post = {
                "user": "あなた",
                "text": tweet_text,
                "time": datetime.now().strftime("%H:%M")
            }
            st.session_state.timeline.insert(0, new_post)
            st.rerun()

st.divider()

# タイムライン表示
for post in st.session_state.timeline:
    st.markdown(f"""
        <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px;">
            <span style="font-weight:bold; color:#1DA1F2;">{post['user']}</span> 
            <span style="color:gray; font-size:0.8em;">@{post['user']} · {post['time']}</span><br>
            <div style="margin-top:5px;">{post['text']}</div>
        </div>
    """, unsafe_allow_html=True)