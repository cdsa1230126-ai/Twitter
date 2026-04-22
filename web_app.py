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

# --- CSS: X風デザイン & モバイル特化ボトムナビ ---
st.markdown(
    """
    <style>
    /* 全体背景 */
    .stApp { background-color: #FFFFFF; }
    
    /* メインコンテンツの余白（ナビに被らないように） */
    .main-content { margin-bottom: 80px; max-width: 600px; margin-left: auto; margin-right: auto; }

    /* ボトムナビゲーションのコンテナ */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: white;
        border-top: 1px solid #EFF3F4;
        padding: 12px 0;
        z-index: 9999;
    }

    /* ボタンのスタイルをアイコンっぽく上書き */
    div[data-testid="column"] button {
        background-color: transparent !important;
        border: none !important;
        color: #0F1419 !important;
        font-size: 24px !important;
        height: auto !important;
        padding: 0 !important;
        margin: 0 auto !important;
        display: block !important;
    }
    
    div[data-testid="column"] button:hover {
        color: #1D9BF0 !important;
        background-color: #E7F3FE !important;
        border-radius: 50% !important;
    }

    /* 投稿のデザイン */
    .tweet-container {
        padding: 15px;
        border-bottom: 1px solid #EFF3F4;
        display: flex;
        gap: 12px;
    }
    .profile-pic { border-radius: 50%; object-fit: cover; width: 48px; height: 48px; }
    
    /* 不要な要素を消す */
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] { display: none; }
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
if "viewing_user_id" not in st.session_state: st.session_state.viewing_user_id = None

# --- 4. ログイン（簡易版） ---
if not st.session_state.logged_in:
    st.title("Iwattar :bird:")
    with st.form("login"):
        e = st.text_input("メールアドレス")
        p = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン"):
            try:
                u = auth.get_user_by_email(e)
                st.session_state.logged_in = True
                st.session_state.user_id = u.uid
                st.session_state.is_admin_user = (e.strip() == ADMIN_EMAIL.strip())
                st.rerun()
            except: st.error("ログイン失敗")
    st.stop()

# ユーザー情報
user_ref = db.collection('users').document(st.session_state.user_id)
user_data = user_ref.get().to_dict() or {}
st.session_state.user_name = user_data.get('display_name', "Guest")
st.session_state.avatar = user_data.get('avatar_data')

# --- 5. メイン表示エリア ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
page = st.session_state.current_page

# ページ：ホーム
if page == "home":
    st.subheader("ホーム")
    with st.container(border=True):
        txt = st.text_area("いまどうしてる？", max_chars=140, label_visibility="collapsed")
        if st.button("ポスト", type="primary"):
            if txt.strip():
                db.collection("tweets").add({
                    "text": txt, "user_name": st.session_state.user_name,
                    "user_id": st.session_state.user_id, "avatar_data": st.session_state.avatar,
                    "created_at": firestore.SERVER_TIMESTAMP
                }); st.rerun()

    q = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20)
    for t in q.stream():
        d = t.to_dict()
        uid = d.get('user_id', "")[:5]
        st.markdown(f'''
            <div class="tweet-container">
                <img src="{d.get('avatar_data') or 'https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png'}" class="profile-pic">
                <div>
                    <b>{d.get('user_name', 'User')}</b> <span style="color:#536471;">@{uid}</span><br>
                    {d.get('text', '')}
                </div>
            </div>
        ''', unsafe_allow_html=True)

# ページ：検索
elif page == "search":
    st.subheader("検索")
    s_query = st.text_input("キーワード検索", placeholder="検索ワードを入力...")
    if s_query:
        st.write(f"「{s_query}」の検索結果（シミュレーション）")

# ページ：マイページ
elif page == "profile":
    st.subheader("マイページ")
    if st.session_state.avatar:
        st.image(st.session_state.avatar, width=100)
    st.write(f"名前: {st.session_state.user_name}")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 固定ボトムナビゲーション（画像のデザインを再現） ---
st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
# Xのボトムバーと同じ並び：ホーム、検索、通知（お知らせ）、DM（今回は設定）
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🏠", key="nav_home"):
        st.session_state.current_page = "home"
        st.rerun()
with col2:
    if st.button("🔍", key="nav_search"):
        st.session_state.current_page = "search"
        st.rerun()
with col3:
    if st.button("🔔", key="nav_news"): # 通知アイコン
        st.session_state.current_page = "news"
        st.rerun()
with col4:
    if st.button("👤", key="nav_prof"): # プロフィール
        st.session_state.current_page = "profile"
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)