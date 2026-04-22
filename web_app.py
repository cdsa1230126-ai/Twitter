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

# --- CSS: 空白削除 & ボトムナビの完全固定デザイン ---
st.markdown(
    """
    <style>
    /* 1. 画面上部の不要な余白を消す */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    header { visibility: hidden; height: 0px !important; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }

    /* 全体背景 */
    .stApp { background-color: #FFFFFF; }
    
    /* 2. メインコンテンツ：ナビに被らないように下に大きな余白を確保 */
    .main-content { 
        margin-top: 0px !important;
        margin-bottom: 100px !important; 
        max-width: 600px; 
        margin-left: auto; 
        margin-right: auto; 
        padding: 10px;
    }

    /* 3. ボトムナビゲーション：画面最下部に「常に最前面」で固定 */
    .fixed-footer {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 75px !important;
        background-color: rgba(255, 255, 255, 0.98) !important;
        border-top: 1px solid #EFF3F4 !important;
        z-index: 999999 !important; /* 他のどんな要素よりも手前に表示 */
        display: flex;
        justify-content: space-around;
        align-items: center;
        padding-bottom: env(safe-area-inset-bottom);
    }

    /* Streamlitボタンをナビゲーションアイコン化 */
    div[data-testid="column"] button {
        background-color: transparent !important;
        border: none !important;
        color: #0F1419 !important;
        font-size: 32px !important;
        width: 100% !important;
        height: 65px !important;
        transition: transform 0.1s ease;
    }
    
    div[data-testid="column"] button:active {
        transform: scale(0.8);
        color: #1D9BF0 !important;
    }

    /* タイムラインのデザイン */
    .tweet-container {
        padding: 12px 15px;
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

# --- 2. セッション管理 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_page" not in st.session_state: st.session_state.current_page = "home"

# --- 3. ログイン画面 ---
if not st.session_state.logged_in:
    st.title("Iwattar :bird:")
    with st.form("login_form"):
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

# ユーザーデータ
user_ref = db.collection('users').document(st.session_state.user_id)
user_data = user_ref.get().to_dict() or {}
display_name = user_data.get('display_name', "Guest")
avatar_data = user_data.get('avatar_data')

# --- 4. メイン表示エリア ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

if st.session_state.current_page == "home":
    st.subheader("ホーム")
    with st.container(border=True):
        tweet_txt = st.text_area("いまどうしてる？", max_chars=140, label_visibility="collapsed")
        if st.button("ポスト", type="primary", use_container_width=True):
            if tweet_txt.strip():
                db.collection("tweets").add({
                    "text": tweet_txt, "user_name": display_name, "user_id": st.session_state.user_id,
                    "avatar_data": avatar_data, "created_at": firestore.SERVER_TIMESTAMP
                }); st.rerun()

    # タイムライン
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(30).stream()
    for t in tweets:
        d = t.to_dict()
        st.markdown(f'''
            <div class="tweet-container">
                <img src="{d.get('avatar_data') or 'https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png'}" class="profile-pic">
                <div style="flex:1;">
                    <b>{d.get('user_name', 'User')}</b>
                    <div style="margin-top:4px;">{d.get('text', '')}</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

elif st.session_state.current_page == "profile":
    st.subheader("プロフィール")
    if avatar_data: st.image(avatar_data, width=100)
    st.write(f"名前: {display_name}")
    if st.button("ログアウト"):
        st.session_state.clear(); st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- 5. 完全固定ボトムナビゲーション ---
st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    if st.button("🏠", key="nav_h_fixed"):
        st.session_state.current_page = "home"
        st.rerun()
with col2:
    if st.button("👤", key="nav_p_fixed"):
        st.session_state.current_page = "profile"
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)