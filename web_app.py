import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json
import base64
import pandas as pd
from io import BytesIO
from PIL import Image
import textwrap
import re

# --- 0. 基本設定 ---
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp"

st.set_page_config(page_title="Iwattar", page_icon=":bird:", layout="wide")

# --- CSS: 画面下部アイコンの完全固定 & スタイル調整 ---
st.markdown(
    """
    <style>
    /* 全体設定 */
    .stApp { background-color: #FFFFFF; }
    
    /* メインコンテンツ：ナビに絶対に被らないようにマージンを大きく確保 */
    .main-content { 
        margin-bottom: 120px !important; 
        max-width: 600px; 
        margin-left: auto; 
        margin-right: auto; 
        padding: 10px;
    }

    /* ボトムナビゲーション：画面最下部に強制固定 */
    .fixed-footer {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 75px !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px);
        border-top: 1px solid #EFF3F4 !important;
        z-index: 999999 !important; /* 他の要素より常に上 */
        display: flex;
        justify-content: space-around;
        align-items: center;
    }

    /* アイコンボタンの装飾をX（旧Twitter）風に */
    div[data-testid="column"] button {
        background-color: transparent !important;
        border: none !important;
        color: #0F1419 !important;
        font-size: 28px !important;
        padding: 10px !important;
        transition: transform 0.1s ease;
    }
    
    div[data-testid="column"] button:active {
        transform: scale(0.8);
        color: #1D9BF0 !important;
    }

    /* 不要な要素の非表示 */
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] { display: none; }
    
    /* タイムラインのデザイン */
    .tweet-container {
        padding: 15px;
        border-bottom: 1px solid #EFF3F4;
        display: flex;
        gap: 12px;
    }
    .profile-pic { border-radius: 50%; object-fit: cover; width: 48px; height: 48px; border: 1px solid #eee; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. Firebase初期化 ---
if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        parts = fb_sec["raw_data"].split(",")
        raw_key = fb_sec["private_key"].replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
        pure_key = re.sub(r"[^A-Za-z0-9+/=]", "", raw_key)
        formatted_content = "\n".join(textwrap.wrap(pure_key, 64))
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_content}\n-----END PRIVATE KEY-----\n"

        info_dict = {
            "type": "service_account", "project_id": parts[0], "private_key_id": parts[1],
            "private_key": fixed_key, "client_email": parts[2], "client_id": parts[3],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{parts[2]}",
            "universe_domain": "googleapis.com"
        }
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase初期化失敗: {e}"); st.stop()

db = firestore.client()

# --- 2. 共通関数 ---
def convert_image_to_base64(uploaded_file, size=(500, 500)):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            img.thumbnail(size)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
        except: return None
    return None

# --- 3. セッション管理 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_page" not in st.session_state: st.session_state.current_page = "home"

# --- 4. ログイン画面 ---
if not st.session_state.logged_in:
    st.title("Iwattar :bird:")
    with st.form("login"):
        email = st.text_input("メールアドレス")
        password = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン"):
            try:
                user = auth.get_user_by_email(email)
                st.session_state.logged_in = True
                st.session_state.user_id = user.uid
                st.rerun()
            except: st.error("ログインに失敗しました")
    st.stop()

# ユーザー情報取得
user_ref = db.collection('users').document(st.session_state.user_id)
user_data = user_ref.get().to_dict() or {}
name = user_data.get('display_name', "Guest")
avatar = user_data.get('avatar_data')

# --- 5. メイン表示 (ここがスクロールするエリア) ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

if st.session_state.current_page == "home":
    st.subheader("ホーム")
    with st.container(border=True):
        tweet_txt = st.text_area("いまどうしてる？", max_chars=140, label_visibility="collapsed")
        if st.button("ポスト", type="primary", use_container_width=True):
            if tweet_txt.strip():
                db.collection("tweets").add({
                    "text": tweet_txt, "user_name": name, "user_id": st.session_state.user_id,
                    "avatar_data": avatar, "created_at": firestore.SERVER_TIMESTAMP
                }); st.rerun()

    # タイムライン
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(30).stream()
    for t in tweets:
        d = t.to_dict()
        uid_short = (d.get('user_id') or "")[:5]
        st.markdown(f'''
            <div class="tweet-container">
                <img src="{d.get('avatar_data') or 'https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png'}" class="profile-pic">
                <div style="flex:1;">
                    <b>{d.get('user_name', 'User')}</b> <span style="color:#536471;">@{uid_short}</span>
                    <div style="margin-top:4px;">{d.get('text', '')}</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

elif st.session_state.current_page == "search":
    st.subheader("検索")
    st.text_input("キーワード検索", placeholder="ユーザーや単語を検索")

elif st.session_state.current_page == "news":
    st.subheader("お知らせ")
    st.info("新しいお知らせはありません。")

elif st.session_state.current_page == "profile":
    st.subheader("プロフィール")
    if avatar: st.image(avatar, width=100)
    st.write(f"名前: {name}")
    if st.button("ログアウト"):
        st.session_state.clear(); st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 完全固定ボトムナビゲーション (常に画面最下部に表示) ---
st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("🏠", key="home_btn"): 
        st.session_state.current_page = "home"; st.rerun()
with c2:
    if st.button("🔍", key="search_btn"): 
        st.session_state.current_page = "search"; st.rerun()
with c3:
    if st.button("🔔", key="news_btn"): 
        st.session_state.current_page = "news"; st.rerun()
with c4:
    if st.button("👤", key="prof_btn"): 
        st.session_state.current_page = "profile"; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)