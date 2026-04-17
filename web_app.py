import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq
from datetime import datetime
import pytz

# ページ設定
st.set_page_config(page_title="iwitter - Firebase Edition", layout="wide")

# --- 1. Firebase初期化 ---
if not firebase_admin._apps:
    try:
        fb_credentials = dict(st.secrets["firebase"])
        cred = credentials.Certificate(fb_credentials)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebaseの初期化に失敗しました: {e}")
        st.stop()

db = firestore.client()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
tokyo_tz = pytz.timezone('Asia/Tokyo')

# --- 2. タイムライン表示エリア ---
st.title("𝕏 iwitter (Firebase)")

with st.sidebar:
    st.header("🤖 AI Assistant")
    ai_query = st.text_input("AIに質問")
    if st.button("聞く") and ai_query:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": ai_query}],
            model="llama-3.3-70b-versatile",
        )
        st.write(chat_completion.choices[0].message.content)

# 投稿フォーム
with st.expander("いまどうしてる？", expanded=True):
    name = st.text_input("名前", value="ゲスト")
    content = st.text_area("内容")
    if st.button("投稿"):
        if content:
            # Firestoreにデータを追加
            doc_ref = db.collection("posts").document()
            doc_ref.set({
                "user": name,
                "text": content,
                "time": datetime.now(tokyo_tz)
            })
            st.success("投稿しました！")
            st.rerun()

st.divider()

# 投稿の取得と表示
posts_ref = db.collection("posts").order_by("time", direction=firestore.Query.DESCENDING).limit(20)
posts = posts_ref.stream()

for post in posts:
    p = post.to_dict()
    time_str = p['time'].astimezone(tokyo_tz).strftime('%m/%d %H:%M') if 'time' in p else "不明"
    st.markdown(f"""
        <div style="border-bottom:1px solid #eee; padding:10px;">
            <b style="color:#1DA1F2;">{p.get('user', '名無し')}</b> 
            <small style="color:gray;">{time_str}</small><br>
            <div style="margin-top:5px;">{p.get('text', '')}</div>
        </div>
    """, unsafe_allow_html=True)