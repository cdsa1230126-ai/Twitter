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

# --- CSS: ボトムナビゲーションとデザインの固定 ---
st.markdown(
    """
    <style>
    /* 全体の背景と余白 */
    .stApp { background-color: #F7F9F9; }
    .main-content { margin-bottom: 100px; } /* メニューに被らないための余白 */

    /* ボトムナビゲーションの固定設定 */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: white;
        border-top: 1px solid #EFF3F4;
        padding: 10px 0;
        z-index: 9999;
        display: flex;
        justify-content: space-around;
    }

    /* 投稿のデザイン */
    .tweet-container {
        background-color: white;
        padding: 15px;
        border-bottom: 1px solid #EFF3F4;
    }
    .profile-pic { border-radius: 50%; object-fit: cover; border: 1px solid #ddd; }
    .tweet-img img { border-radius: 16px !important; margin-top: 10px; }

    /* Streamlitの標準ヘッダー/フッターを非表示 */
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ボトムバー内のボタンを横並びに配置するための調整 */
    div[data-testid="stHorizontalBlock"] {
        background: white;
    }
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
        img = Image.open(uploaded_file)
        img.thumbnail(size)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return None

# --- 3. セッション管理 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_page" not in st.session_state: st.session_state.current_page = "🏠 ホーム"
if "saved_email" not in st.session_state: st.session_state.saved_email = ""
if "viewing_user_id" not in st.session_state: st.session_state.viewing_user_id = None

# --- 4. ログイン・アカウント作成 ---
if not st.session_state.logged_in:
    st.title("Iwattar :bird:")
    t1, t2 = st.tabs(["ログイン", "アカウント作成"])
    with t1:
        with st.form("login"):
            e = st.text_input("メールアドレス", value=st.session_state.saved_email)
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    u = auth.get_user_by_email(e)
                    st.session_state.logged_in = True
                    st.session_state.user_id = u.uid
                    st.session_state.saved_email = e
                    st.session_state.is_admin_user = (e.strip() == ADMIN_EMAIL.strip())
                    st.session_state.admin_mode_on = st.session_state.is_admin_user
                    st.rerun()
                except: st.error("ログイン失敗")
    with t2:
        with st.form("signup"):
            ne = st.text_input("新規メールアドレス")
            np = st.text_input("パスワード(6文字以上)", type="password")
            nn = st.text_input("表示名")
            if st.form_submit_button("新規登録"):
                if len(np) < 6: st.error("パスワードが短すぎます")
                else:
                    try:
                        user = auth.create_user(email=ne, password=np, display_name=nn)
                        db.collection('users').document(user.uid).set({"display_name": nn, "email": ne, "avatar_data": None})
                        st.success("作成完了！ログインしてください"); st.session_state.saved_email = ne
                    except Exception as ex: st.error(f"作成失敗: {ex}")
    st.stop()

# ユーザー情報
user_ref = db.collection('users').document(st.session_state.user_id)
user_data = user_ref.get().to_dict() or {}
st.session_state.user_name = user_data.get('display_name', "Guest")
st.session_state.avatar = user_data.get('avatar_data')

# --- 5. メイン画面の構築 ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
page = st.session_state.current_page
st.header(page)

if page == "🏠 ホーム" or page == "👤 マイページ":
    if page == "🏠 ホーム":
        with st.container(border=True):
            txt = st.text_area("いまどうしてる？", max_chars=140, placeholder="メッセージを入力...")
            img = st.file_uploader("画像を添付", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
            if st.button("ポスト"):
                if txt.strip():
                    db.collection("tweets").add({
                        "text": txt, "user_name": st.session_state.user_name,
                        "user_id": st.session_state.user_id, "avatar_data": st.session_state.avatar,
                        "post_image": convert_image_to_base64(img) if img else None,
                        "created_at": firestore.SERVER_TIMESTAMP
                    }); st.rerun()

    q = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING)
    if st.session_state.viewing_user_id:
        q = q.where("user_id", "==", st.session_state.viewing_user_id)
        if st.button("← タイムラインに戻る"): 
            st.session_state.viewing_user_id = None
            st.session_state.current_page = "🏠 ホーム"; st.rerun()

    for t in q.limit(20).stream():
        d = t.to_dict()
        st.markdown('<div class="tweet-container">', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 8])
        with c1:
            av = d.get('avatar_data') or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"
            st.markdown(f'<img src="{av}" class="profile-pic" width="50">', unsafe_allow_html=True)
        with c2:
            st.markdown(f"**{d.get('user_name')}** <span style='color:#536471;'>@{d.get('user_id')[:5]}</span>", unsafe_allow_html=True)
            st.write(d.get('text'))
            if d.get('post_image'): st.image(d.get('post_image'))
            if st.session_state.admin_mode_on or d.get('user_id') == st.session_state.user_id:
                if st.button("🗑️", key=f"del_{t.id}"): db.collection("tweets").document(t.id).delete(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "🔍 検索":
    search = st.text_input("ユーザー名やキーワードを入力", placeholder="検索...")
    if search:
        tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(50).stream()
        for t in tweets:
            d = t.to_dict()
            if search.lower() in d.get('text', "").lower() or search.lower() in d.get('user_name', "").lower():
                with st.container(border=True):
                    st.write(f"**{d.get('user_name')}**: {d.get('text')}")
                    if st.button("プロフィールを見る", key=f"view_{t.id}"):
                        st.session_state.viewing_user_id = d.get('user_id')
                        st.session_state.current_page = "👤 マイページ"; st.rerun()

elif page == "📢 お知らせ":
    if st.session_state.admin_mode_on:
        with st.form("news_form"):
            new_news = st.text_input("お知らせ内容")
            if st.form_submit_button("配信"):
                db.collection("news").add({"title": new_news, "date": firestore.SERVER_TIMESTAMP}); st.rerun()
    
    for n in db.collection("news").order_by("date", direction=firestore.Query.DESCENDING).stream():
        st.info(n.to_dict().get('title'))

elif page == "📝 プロフィール":
    with st.form("prof"):
        n_name = st.text_input("表示名", value=st.session_state.user_name)
        n_img = st.file_uploader("アイコン画像", type=["jpg", "png", "jpeg"])
        if st.form_submit_button("保存"):
            upd = {"display_name": n_name}
            if n_img: upd["avatar_data"] = convert_image_to_base64(n_img, size=(200,200))
            user_ref.update(upd); st.success("更新しました！"); st.rerun()
    if st.button("ログアウト"): st.session_state.clear(); st.rerun()

st.markdown('</div>', unsafe_allow_html=True) # メインコンテンツ終了

# --- 6. ボトムナビゲーションバーのボタン配置 ---
st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
with f_col1:
    if st.button("🏠"): st.session_state.current_page = "🏠 ホーム"; st.session_state.viewing_user_id = None; st.rerun()
with f_col2:
    if st.button("🔍"): st.session_state.current_page = "🔍 検索"; st.rerun()
with f_col3:
    if st.button("👤"): 
        st.session_state.viewing_user_id = st.session_state.user_id
        st.session_state.current_page = "👤 マイページ"; st.rerun()
with f_col4:
    if st.button("📢"): st.session_state.current_page = "📢 お知らせ"; st.rerun()
with f_col5:
    if st.button("📝"): st.session_state.current_page = "📝 プロフィール"; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)