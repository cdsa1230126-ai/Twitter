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

# --- CSS (UIをさらに洗練) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
    
    /* サイドバーのボタンをリスト風にする */
    .stButton > button {
        text-align: left !important;
        border: none !important;
        background-color: transparent !important;
        color: #0F1419 !important;
        font-size: 18px !important;
        padding: 10px 20px !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background-color: rgba(15, 20, 25, 0.1) !important;
        border-radius: 9999px !important;
    }
    
    /* 投稿カードのデザイン */
    .tweet-card { display: flex; padding: 12px 16px; border-bottom: 1px solid #EFF3F4; }
    .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; margin-right: 12px; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. Firebase初期化 (Secrets利用) ---
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
        buf = BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    return None

# --- 3. 認証・セッション ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_page" not in st.session_state: st.session_state.current_page = "タイムライン"
if "view_user" not in st.session_state: st.session_state.view_user = None
if "is_admin" not in st.session_state: st.session_state.is_admin = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["ログイン", "アカウント作成"])
    with tab1:
        with st.form("login"):
            e = st.text_input("メールアドレス")
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    u = auth.get_user_by_email(e)
                    st.session_state.logged_in = True
                    st.session_state.user_id = u.uid
                    st.session_state.is_admin = (e.strip() == ADMIN_EMAIL.strip())
                    st.rerun()
                except: st.error("ログイン失敗")
    st.stop()

# ユーザーデータ
u_ref = db.collection('users').document(st.session_state.user_id)
u_data = u_ref.get().to_dict() or {}
st.session_state.user_name = u_data.get('display_name', "Guest")
st.session_state.avatar = u_data.get('avatar')

# --- 4. メインレイアウト ---

# 【修正ポイント】サイドバーを「ハンバーガーメニュー」として活用
with st.sidebar:
    st.title("Iwattar")
    
    # プロフィール簡易表示
    st.image(st.session_state.avatar or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png", width=60)
    st.markdown(f"**{st.session_state.user_name}**")
    
    st.markdown("---")
    
    # メニューをリスト形式で配置
    if st.button("🏠 ホーム"):
        st.session_state.current_page = "タイムライン"; st.session_state.view_user = None; st.rerun()
    
    if st.button("👤 プロフィール"):
        st.session_state.view_user = st.session_state.user_id; st.session_state.current_page = "タイムライン"; st.rerun()
    
    if st.button("📑 ゼミ一覧"):
        st.session_state.current_page = "ゼミ一覧"; st.rerun()
        
    if st.button("⚙️ 設定"):
        st.session_state.current_page = "設定"; st.rerun()
    
    st.markdown("---")
    
    # 管理者用スイッチ（管理者メールの場合のみ表示）
    if st.session_state.user_id:
        user_email = auth.get_user(st.session_state.user_id).email
        if user_email == ADMIN_EMAIL:
            mode = st.toggle("管理者モード", value=st.session_state.is_admin)
            if mode != st.session_state.is_admin:
                st.session_state.is_admin = mode
                st.rerun()

    if st.button("🚪 ログアウト"):
        st.session_state.logged_in = False; st.rerun()

# メインコンテンツエリア
main_col, trend_col = st.columns([2.5, 1], gap="large")

with main_col:
    if st.session_state.current_page == "タイムライン":
        if st.session_state.view_user:
            st.subheader("プロフィール投稿")
            if st.button("← 戻る"): st.session_state.view_user = None; st.rerun()
        else:
            st.subheader("ホーム")
            # 投稿フォーム
            with st.container():
                txt = st.text_area("", placeholder="いまどうしてる？", label_visibility="collapsed")
                img_file = st.file_uploader("画像アップロード", type=["jpg", "png"], label_visibility="collapsed")
                if st.button("ポストする", key="main_post_btn"):
                    if txt.strip():
                        db.collection("tweets").add({
                            "text": txt, "user_name": st.session_state.user_name,
                            "user_id": st.session_state.user_id, "avatar": st.session_state.avatar,
                            "image": image_to_base64(img_file), "created_at": firestore.SERVER_TIMESTAMP
                        })
                        st.rerun()
        
        st.markdown("---")
        
        # タイムライン表示
        q = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING)
        if st.session_state.view_user:
            q = q.where("user_id", "==", st.session_state.view_user)

        for doc in q.limit(20).stream():
            d = doc.to_dict()
            ts = d.get('created_at')
            dt = ts.strftime('%m/%d %H:%M') if ts else "now"
            
            st.markdown(f"""
            <div class="tweet-card">
                <img src="{d.get('avatar') or "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"}" class="avatar">
                <div style="flex:1;">
                    <div><span class="display-name">{d.get('user_name')}</span> <span style="color:#536471;">@{str(d.get('user_id'))[:5]} · {dt}</span></div>
                    <div class="tweet-content">{d.get('text')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if d.get('image'): st.image(d.get('image'), use_container_width=True)
            
            # 削除ボタン
            if st.session_state.is_admin or d.get('user_id') == st.session_state.user_id:
                if st.button("🗑 削除", key=f"del_{doc.id}"):
                    db.collection("tweets").document(doc.id).delete(); st.rerun()

    elif st.session_state.current_page == "設定":
        st.subheader("設定")
        new_name = st.text_input("表示名", value=st.session_state.user_name)
        new_avatar = st.file_uploader("アイコン変更", type=["jpg", "png"])
        if st.button("保存"):
            upd = {"display_name": new_name}
            if new_avatar: upd["avatar"] = image_to_base64(new_avatar)
            u_ref.update(upd); st.success("更新しました"); st.rerun()

with trend_col:
    st.markdown("### トレンド")
    st.info("ここにニュースやトレンドが表示されます")