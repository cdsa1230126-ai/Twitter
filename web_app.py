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

# --- X風UI再現CSS（ボトムナビを最下部に強制固定） ---
st.markdown(
    """
    <style>
    /* 全体フォントと余白 */
    html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
    
    /* ボトムナビゲーションを画面の最下部に固定 */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: white;
        border-top: 1px solid #EFF3F4;
        padding: 10px 0;
        z-index: 999999;
        display: block;
    }
    
    /* ナビゲーションボタンのホバー効果 */
    div.stButton > button:hover {
        background-color: rgba(29, 155, 240, 0.1) !important;
        border-radius: 50%;
    }

    /* メインコンテンツがナビに被らないように下に余白（100px）を空ける */
    .main-container { margin-bottom: 100px; }

    /* 投稿カードのデザイン */
    .tweet-card { display: flex; padding: 12px 16px; border-bottom: 1px solid #EFF3F4; }
    .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; margin-right: 12px; }
    .display-name { font-weight: 700; color: #0F1419; font-size: 15px; }
    
    /* サイドバー内のプロフィール */
    .sidebar-profile { padding: 20px 0; border-bottom: 1px solid #EFF3F4; margin-bottom: 20px; }
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
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# ログインチェック
if not st.session_state.logged_in:
    st.title("Iwattar")
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
    st.stop()

# ユーザー情報取得
u_ref = db.collection('users').document(st.session_state.user_id)
u_data = u_ref.get().to_dict() or {}
st.session_state.user_name = u_data.get('display_name', "Guest")
st.session_state.avatar = u_data.get('avatar')

# --- 4. サイドドロワー（左上のメニュー） ---
with st.sidebar:
    st.markdown('<div class="sidebar-profile">', unsafe_allow_html=True)
    st.image(st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png", width=64)
    st.markdown(f"### {st.session_state.user_name}")
    st.caption(f"@{st.session_state.user_id[:8]}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🚪 ログアウト"): 
        st.session_state.logged_in = False; st.rerun()

# --- 5. メイン表示エリア (画面切り替え) ---
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 【Home画面】
if st.session_state.current_page == "Home":
    st.title("ホーム")
    # 投稿フォーム
    with st.container():
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown(f'<img src="{st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar">', unsafe_allow_html=True)
        with c2:
            txt = st.text_area("", placeholder="いまどうしてる？", key="tweet_input", label_visibility="collapsed")
            img_file = st.file_uploader("画像選択", type=["jpg", "png"], label_visibility="collapsed")
            if st.button("ポストする"):
                if txt.strip():
                    db.collection("tweets").add({
                        "text": txt, "user_name": st.session_state.user_name,
                        "user_id": st.session_state.user_id, "avatar": st.session_state.avatar,
                        "image": image_to_base64(img_file), "created_at": firestore.SERVER_TIMESTAMP
                    }); st.rerun()
    st.markdown("---")
    # タイムライン
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
    for doc in tweets:
        d = doc.to_dict()
        st.markdown(f"""
        <div class="tweet-card">
            <img src="{d.get('avatar') or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar">
            <div style="flex:1;">
                <div><span class="display-name">{d.get('user_name')}</span></div>
                <div style="color:#0F1419;">{d.get('text')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if d.get("image"): st.image(d.get("image"), use_container_width=True)

# 【Search画面】
elif st.session_state.current_page == "Search":
    st.title("検索")
    st.text_input("キーワード検索", placeholder="ゼミや話題を検索...")

# 【Notifications画面】
elif st.session_state.current_page == "Notifications":
    st.title("通知")
    st.info("新しい通知はありません。")

# 【Profile画面（アイコン変更専用）】
elif st.session_state.current_page == "Profile":
    st.title("プロフィール設定")
    st.image(st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png", width=120)
    new_name = st.text_input("名前", value=st.session_state.user_name)
    new_avatar_file = st.file_uploader("アイコン画像を変更", type=["jpg", "png"])
    if st.button("変更を保存"):
        upd = {"display_name": new_name}
        if new_avatar_file:
            upd["avatar"] = image_to_base64(new_avatar_file)
        u_ref.update(upd); st.success("保存完了！"); st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- 6. ボトムナビゲーション (最下部に固定) ---
# コンテナを作り、そこにボタンを配置
st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
with nav_col1:
    if st.button("🏠", key="nav_home"): st.session_state.current_page = "Home"; st.rerun()
with nav_col2:
    if st.button("🔍", key="nav_search"): st.session_state.current_page = "Search"; st.rerun()
with nav_col3:
    if st.button("🔔", key="nav_noti"): st.session_state.current_page = "Notifications"; st.rerun()
with nav_col4:
    if st.button("👤", key="nav_prof"): st.session_state.current_page = "Profile"; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)