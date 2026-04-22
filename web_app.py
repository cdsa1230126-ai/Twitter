import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import base64
import re
import textwrap
from io import BytesIO
from PIL import Image
from datetime import datetime

# --- 0. 基本設定 ---
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp"
st.set_page_config(page_title="Iwattar", page_icon=":bird:", layout="wide")

# --- X（旧Twitter）完全再現CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #EFF3F4; }
    .tweet-card {
        display: flex;
        padding: 12px 16px;
        border-bottom: 1px solid #EFF3F4;
        transition: 0.2s;
    }
    .tweet-card:hover { background-color: rgba(0, 0, 0, 0.03); cursor: pointer; }
    .avatar-container { margin-right: 12px; }
    .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; }
    .tweet-header { display: flex; align-items: center; gap: 4px; margin-bottom: 2px; }
    .display-name { font-weight: 700; color: #0F1419; font-size: 15px; }
    .user-handle { color: #536471; font-size: 15px; font-weight: 400; }
    .tweet-content { color: #0F1419; font-size: 15px; line-height: 1.5; white-space: pre-wrap; margin-bottom: 12px; }
    .tweet-media img {
        border-radius: 16px;
        border: 1px solid #EFF3F4;
        margin-top: 10px;
        width: 100%;
        max-height: 512px;
        object-fit: cover;
    }
    div.stButton > button {
        background-color: #1D9BF0;
        color: white;
        border: none;
        border-radius: 9999px;
        font-weight: 700;
        padding: 10px 24px;
        width: 100%;
    }
    div.stButton > button:hover { background-color: #1A8CD8; color: white; }
    .stTextArea textarea { border: none !important; font-size: 20px !important; }
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
            "type": "service_account",
            "project_id": parts[0], "private_key_id": parts[1],
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
        st.error(f"Firebase接続エラー: {e}"); st.stop()

db = firestore.client()

# --- 2. 共通関数 ---
def image_to_base64(file, size=(800, 800)):
    if file:
        img = Image.open(file)
        img.thumbnail(size)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    return None

# --- 3. セッション・認証 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_page" not in st.session_state: st.session_state.current_page = "タイムライン"
if "view_user" not in st.session_state: st.session_state.view_user = None

if not st.session_state.logged_in:
    st.title("Iwattar")
    tab1, tab2 = st.tabs(["ログイン", "アカウント作成"])
    with tab1:
        with st.form("login"):
            e = st.text_input("メールアドレス")
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    u = auth.get_user_by_email(e)
                    st.session_state.logged_in, st.session_state.user_id = True, u.uid
                    st.session_state.is_admin = (e.strip() == ADMIN_EMAIL.strip())
                    st.rerun()
                except: st.error("ログイン失敗")
    with tab2:
        with st.form("signup"):
            ne, np, nn = st.text_input("メール"), st.text_input("パスワード"), st.text_input("表示名")
            if st.form_submit_button("登録"):
                user = auth.create_user(email=ne, password=np, display_name=nn)
                db.collection('users').document(user.uid).set({"display_name": nn, "avatar": None})
                st.success("完了！")
    st.stop()

u_ref = db.collection('users').document(st.session_state.user_id)
u_data = u_ref.get().to_dict() or {}
st.session_state.user_name = u_data.get('display_name', "Guest")
st.session_state.avatar = u_data.get('avatar')

# --- 4. メインレイアウト ---
side, main, trend = st.columns([1, 2.5, 1.2], gap="medium")

with side:
    st.markdown("### Iwattar")
    if st.button(":house: ホーム"):
        st.session_state.current_page = "タイムライン"
        st.session_state.view_user = None
        st.rerun()
    if st.button(":bust_in_silhouette: プロフィール"):
        st.session_state.view_user = st.session_state.user_id
        st.rerun()
    if st.button(":bookmark_tabs: ゼミ一覧"):
        st.session_state.current_page = "ゼミ一覧"
        st.rerun()
    if st.button(":gear: 設定"):
        st.session_state.current_page = "設定"
        st.rerun()
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()

with main:
    if st.session_state.current_page == "タイムライン":
        if st.session_state.view_user:
            st.markdown(f"#### 投稿一覧")
            if st.button("← 戻る"):
                st.session_state.view_user = None
                st.rerun()
        else:
            st.markdown("#### ホーム")
            with st.container():
                c1, c2 = st.columns([1, 6])
                with c1:
                    st.markdown(f'<img src="{st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar">', unsafe_allow_html=True)
                with c2:
                    txt = st.text_area("", placeholder="いまどうしてる？", label_visibility="collapsed")
                    img_file = st.file_uploader(":frame_with_picture:", type=["jpg", "png"], label_visibility="collapsed")
                    if st.button("ポストする"):
                        if txt.strip():
                            db.collection("tweets").add({
                                "text": txt,
                                "user_name": st.session_state.user_name,
                                "user_id": st.session_state.user_id,
                                "avatar": st.session_state.avatar,
                                "image": image_to_base64(img_file) if img_file else None,
                                "created_at": firestore.SERVER_TIMESTAMP
                            })
                            st.rerun()
            st.markdown("---")

        tweets_query = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING)
        if st.session_state.view_user:
            tweets_query = tweets_query.where("user_id", "==", st.session_state.view_user)

        for doc in tweets_query.limit(20).stream():
            d = doc.to_dict()
            ts = d.get('created_at')
            dt = ts.strftime('%m月%d日 %H:%M') if ts else "なう"
            
            # --- 安全なID取得処理 (ここを修正) ---
            raw_uid = d.get('user_id', "unknown")
            uid_short = str(raw_uid)[:5] if raw_uid else "anon"

            st.markdown(f"""
            <div class="tweet-card">
                <div class="avatar-container">
                    <img src="{d.get('avatar') or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar">
                </div>
                <div style="flex:1;">
                    <div class="tweet-header">
                        <span class="display-name">{d.get('user_name', 'Guest')}</span>
                        <span class="user-handle">@{uid_short} · {dt}</span>
                    </div>
                    <div class="tweet-content">{d.get('text', '')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_space, col_main = st.columns([1, 6])
            with col_main:
                if d.get('image'):
                    st.markdown(f'<div class="tweet-media"><img src="{d.get("image")}"></div>', unsafe_allow_html=True)
                if st.session_state.get('is_admin') or d.get('user_id') == st.session_state.user_id:
                    if st.button(":wastebasket: 削除", key=f"del_{doc.id}"):
                        db.collection("tweets").document(doc.id).delete(); st.rerun()

    elif st.session_state.current_page == "設定":
        st.subheader("プロフィール編集")
        new_name = st.text_input("表示名", value=st.session_state.user_name)
        new_avatar = st.file_uploader("アイコン画像", type=["jpg", "png"])
        if st.button("更新"):
            upd = {"display_name": new_name}
            if new_avatar: upd["avatar"] = image_to_base64(new_avatar, (200, 200))
            u_ref.update(upd); st.success("更新しました"); st.rerun()

with trend:
    st.markdown("### いまどうしてる？")
    with st.container(border=True):
        st.markdown("**トレンド: 岩崎学園**")
        st.caption("2,430件のポスト")
        st.markdown("**トレンド: ゼミ選考**")
        st.caption("1,102件のポスト")
    st.markdown("---")
    st.caption("© 2026 Iwattar from Iwazaki Univ.")