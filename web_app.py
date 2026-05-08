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

# --- X風UI再現CSS（ボトムナビ固定） ---
st.markdown(
    """
    <style>
    /* 全体フォント */
    html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

    /* ボトムナビゲーションのスタイル */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: white;
        border-top: 1px solid #EFF3F4;
        display: flex;
        justify-content: space-around;
        padding: 10px 0;
        z-index: 999999;
    }
    
    /* コンテンツがナビに被らないように余白を追加 */
    .main-content { margin-bottom: 80px; }

    /* 投稿カード */
    .tweet-card { display: flex; padding: 12px 16px; border-bottom: 1px solid #EFF3F4; }
    .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; margin-right: 12px; }
    
    /* サイドバー内のプロフィール */
    .sidebar-profile { padding: 20px 0; border-bottom: 1px solid #EFF3F4; margin-bottom: 20px; }
    .profile-img-large { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. Firebase初期化 (Secretsから) ---
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

# --- 2. セッション管理 ---
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

# --- 3. サイドドロワーメニュー (画像2枚目の再現) ---
with st.sidebar:
    # プロフィールヘッダー
    st.markdown('<div class="sidebar-profile">', unsafe_allow_html=True)
    st.image(st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png", width=64)
    st.markdown(f"### {st.session_state.user_name}")
    st.caption(f"@{st.session_state.user_id[:8]}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # メニュー項目
    if st.button("👤 プロフィール"): 
        st.session_state.current_page = "Profile"; st.rerun()
    if st.button("📑 ゼミ一覧"): 
        st.session_state.current_page = "Zemi"; st.rerun()
    if st.button("🚪 ログアウト"): 
        st.session_state.logged_in = False; st.rerun()

# --- 4. メインコンテンツエリア ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

if st.session_state.current_page == "Home":
    st.title("ホーム")
    # 投稿フォーム
    with st.container():
        txt = st.text_area("", placeholder="いまどうしてる？", label_visibility="collapsed")
        if st.button("ポストする"):
            if txt.strip():
                db.collection("tweets").add({
                    "text": txt, "user_name": st.session_state.user_name,
                    "user_id": st.session_state.user_id, "avatar": st.session_state.avatar,
                    "created_at": firestore.SERVER_TIMESTAMP
                }); st.rerun()
    
    # タイムライン
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
    for doc in tweets:
        d = doc.to_dict()
        st.markdown(f'<div class="tweet-card"><img src="{d.get("avatar") or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar"><div><b>{d.get("user_name")}</b><br>{d.get("text")}</div></div>', unsafe_allow_html=True)

elif st.session_state.current_page == "Search":
    st.title("検索")
    st.text_input("キーワード検索", placeholder="話題のゼミを検索...")

elif st.session_state.current_page == "Notifications":
    st.title("通知")
    st.info("新しい通知はありません")

elif st.session_state.current_page == "Profile":
    st.title("プロフィール編集")
    new_name = st.text_input("表示名", value=st.session_state.user_name)
    new_avatar = st.file_uploader("アイコン変更", type=["jpg", "png"])
    if st.button("保存"):
        upd = {"display_name": new_name}
        if new_avatar:
            img = Image.open(new_avatar)
            img.thumbnail((400, 400))
            buf = BytesIO(); img.save(buf, format="PNG")
            upd["avatar"] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        u_ref.update(upd); st.success("更新しました！"); st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- 5. ボトムナビゲーション (画像1枚目の再現) ---
# ※Streamlitのボタンを使って擬似的にページ遷移を発生させる
st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🏠"): st.session_state.current_page = "Home"; st.rerun()
with col2:
    if st.button("🔍"): st.session_state.current_page = "Search"; st.rerun()
with col3:
    if st.button("🔔"): st.session_state.current_page = "Notifications"; st.rerun()
with col4:
    if st.button("👤"): st.session_state.current_page = "Profile"; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)