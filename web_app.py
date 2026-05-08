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
st.set_page_config(page_title="Iwattar", page_icon=":bird:", layout="centered")

# --- UIレイアウト・ダークモード対応CSS ---
st.markdown(
    """
    <style>
    /* 標準ヘッダーと余白の調整 */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        max-width: 600px; /* スマホ風の幅に制限 */
    }
    header {visibility: hidden;} 

    /* 背景色と文字色の自動対応 */
    :root {
        --text-color: inherit;
    }

    /* ページヘッダー（画面上部に固定） */
    .page-header {
        font-size: 20px;
        font-weight: 800;
        padding: 15px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        position: sticky;
        top: 0;
        background-color: var(--background-color);
        z-index: 999;
        color: var(--text-color);
        display: flex;
        align-items: center;
    }

    /* メインスクロールエリア */
    .main-scroll-area {
        margin-top: 0px;
        padding-bottom: 120px; /* ボトムナビに被らないための余白 */
    }

    /* 投稿カード */
    .tweet-card { 
        display: flex; 
        padding: 12px 16px; 
        border-bottom: 1px solid rgba(128, 128, 128, 0.2); 
        color: var(--text-color);
    }
    
    .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; margin-right: 12px; }
    .display-name { font-weight: 700; font-size: 16px; color: var(--text-color); }
    .tweet-text { font-size: 15px; line-height: 1.4; color: var(--text-color); opacity: 0.9; }

    /* ボトムナビゲーション（画面最下部に固定） */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: var(--background-color);
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        padding: 10px 0;
        z-index: 999999;
    }
    
    /* ボタンの透明化とホバー設定 */
    div.stButton > button {
        background-color: transparent !important;
        border: none !important;
        color: var(--text-color) !important;
        font-size: 22px !important;
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. Firebase初期化 (Secrets利用) ---
if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        parts = fb_sec["raw_data"].split(",")
        # 秘密鍵の整形
        raw_key = fb_sec["private_key"].replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
        pure_key = re.sub(r"[^A-Za-z0-9+/=]", "", raw_key)
        formatted_content = "\n".join(textwrap.wrap(pure_key, 64))
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_content}\n-----END PRIVATE KEY-----\n"

        info_dict = {
            "type": "service_account", "project_id": parts[0], "private_key_id": parts[1],
            "private_key": fixed_key, "client_email": parts[2], "client_id": parts[3],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{parts[2]}",
            "universe_domain": "googleapis.com"
        }
        firebase_admin.initialize_app(credentials.Certificate(info_dict))
    except Exception as e:
        st.error(f"Firebase接続エラー: {e}"); st.stop()

db = firestore.client()

# --- 2. 共通関数 ---
def image_to_base64(file):
    if file:
        img = Image.open(file)
        img.thumbnail((800, 800))
        buf = BytesIO(); img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    return None

# --- 3. セッション管理 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_page" not in st.session_state: st.session_state.current_page = "Home"

# ログイン・会員登録
if not st.session_state.logged_in:
    st.title("Iwattar")
    tab_l, tab_s = st.tabs(["ログイン", "新規登録"])
    with tab_l:
        with st.form("login_f"):
            e = st.text_input("メール"); p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    u = auth.get_user_by_email(e)
                    st.session_state.logged_in, st.session_state.user_id = True, u.uid
                    st.rerun()
                except: st.error("失敗しました")
    with tab_s:
        with st.form("signup_f"):
            ne = st.text_input("メールアドレス"); np = st.text_input("パスワード"); nn = st.text_input("表示名")
            if st.form_submit_button("登録"):
                try:
                    user = auth.create_user(email=ne, password=np, display_name=nn)
                    db.collection('users').document(user.uid).set({"display_name": nn, "avatar": None})
                    st.success("完了！ログインしてください")
                except Exception as ex: st.error(f"エラー: {ex}")
    st.stop()

# ユーザーデータ取得
u_ref = db.collection('users').document(st.session_state.user_id)
u_data = u_ref.get().to_dict() or {}
st.session_state.user_name = u_data.get('display_name', "Guest")
st.session_state.avatar = u_data.get('avatar')

# --- 4. サイドドロワー ---
with st.sidebar:
    st.image(st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png", width=80)
    st.markdown(f"### {st.session_state.user_name}")
    st.caption(f"ID: {st.session_state.user_id[:8]}")
    st.markdown("---")
    if st.button("🚪 ログアウト"): st.session_state.logged_in = False; st.rerun()

# --- 5. メイン画面表示 ---
st.markdown('<div class="main-scroll-area">', unsafe_allow_html=True)

# 【ホーム画面】
if st.session_state.current_page == "Home":
    st.markdown('<div class="page-header">ホーム</div>', unsafe_allow_html=True)
    with st.container():
        c1, c2 = st.columns([1, 5])
        with c1: st.markdown(f'<img src="{st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar">', unsafe_allow_html=True)
        with c2:
            txt = st.text_area("", placeholder="いまどうしてる？", key="tw_in", label_visibility="collapsed")
            img_file = st.file_uploader("画像", type=["jpg", "png"], label_visibility="collapsed")
            if st.button("ポストする"):
                if txt.strip():
                    db.collection("tweets").add({
                        "text": txt, "user_name": st.session_state.user_name,
                        "user_id": st.session_state.user_id, "avatar": st.session_state.avatar,
                        "image": image_to_base64(img_file), "created_at": firestore.SERVER_TIMESTAMP
                    }); st.rerun()
    st.markdown("---")
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
    for doc in tweets:
        d = doc.to_dict()
        st.markdown(f"""
        <div class="tweet-card">
            <img src="{d.get('avatar') or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar">
            <div style="flex:1;">
                <div class="display-name">{d.get('user_name')}</div>
                <div class="tweet-text">{d.get('text')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if d.get("image"): st.image(d.get("image"), use_container_width=True)

# 【探索画面】
elif st.session_state.current_page == "Search":
    st.markdown('<div class="page-header">探索</div>', unsafe_allow_html=True)
    st.text_input("キーワード検索", placeholder="ゼミやキーワードを入力")
    st.info("トレンド機能は開発中です")

# 【通知画面】
elif st.session_state.current_page == "Notifications":
    st.markdown('<div class="page-header">通知</div>', unsafe_allow_html=True)
    st.info("現在、新しい通知はありません")

# 【プロフィール設定画面】
elif st.session_state.current_page == "Profile":
    st.markdown('<div class="page-header">プロフィール設定</div>', unsafe_allow_html=True)
    st.image(st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png", width=100)
    new_name = st.text_input("名前", value=st.session_state.user_name)
    new_avatar = st.file_uploader("アイコン画像をアップロード", type=["jpg", "png"])
    if st.button("設定を保存"):
        upd = {"display_name": new_name}
        if new_avatar: upd["avatar"] = image_to_base64(new_avatar)
        u_ref.update(upd)
        st.success("更新しました！")
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- 6. ボトムナビゲーション (画面最下部に固定) ---
st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
n_col1, n_col2, n_col3, n_col4 = st.columns(4)
with n_col1:
    if st.button("🏠", key="nav1"): st.session_state.current_page = "Home"; st.rerun()
with n_col2:
    if st.button("🔍", key="nav2"): st.session_state.current_page = "Search"; st.rerun()
with n_col3:
    if st.button("🔔", key="nav3"): st.session_state.current_page = "Notifications"; st.rerun()
with n_col4:
    if st.button("👤", key="nav4"): st.session_state.current_page = "Profile"; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)