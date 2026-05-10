# ============================================================
# import
# ============================================================
import streamlit as st
import firebase_admin
import hashlib
import base64
import re
import textwrap
import html

from io import BytesIO
from PIL import Image

from firebase_admin import (
    credentials,
    firestore
)

# ============================================================
# 基本設定
# ============================================================
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp"

DEFAULT_AVATAR = (
    "https://abs.twimg.com/sticky/"
    "default_profile_images/default_profile_normal.png"
)

st.set_page_config(
    page_title="Iwattar",
    page_icon="🐦",
    layout="centered"
)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>

/* 全体 */
.block-container{
    padding-top:0rem !important;
    padding-bottom:0rem !important;
    max-width:700px;
}

header{
    visibility:hidden;
}

/* スクロール領域 */
.main-scroll-area{
    padding-bottom:120px;
}

/* ヘッダー */
.page-header{
    font-size:22px;
    font-weight:800;
    padding:14px 16px;
    border-bottom:1px solid rgba(128,128,128,0.2);
    position:sticky;
    top:0;
    background:white;
    z-index:999;
}

/* 投稿 */
.tweet-card{
    display:flex;
    gap:12px;
    padding:16px 8px;
    border-bottom:1px solid rgba(128,128,128,0.2);
}

.avatar{
    width:48px;
    height:48px;
    border-radius:50%;
    object-fit:cover;
}

.avatar-sm{
    width:36px;
    height:36px;
    border-radius:50%;
    object-fit:cover;
}

.display-name{
    font-weight:700;
    font-size:16px;
}

.screen-name{
    color:gray;
    font-size:13px;
}

.tweet-text{
    margin-top:6px;
    font-size:15px;
    line-height:1.5;
    word-break:break-word;
}

/* 下ナビ (Streamlitの仕様に合わせた固定化) */
div[data-testid="stHorizontalBlock"]:has(#nav-marker) {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: white;
    border-top: 1px solid rgba(0,0,0,0.1);
    padding: 8px 0;
    z-index: 999999;
}

div[data-testid="stHorizontalBlock"]:has(#nav-marker) button {
    width: 100%;
    border: none !important;
    background: transparent !important;
    font-size: 24px !important;
}

/* アイコン */
.icon-preview{
    width:90px;
    height:90px;
    border-radius:50%;
    object-fit:cover;
    border:3px solid #1d9bf0;
    margin:auto;
    display:block;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# Firebase 初期化
# ============================================================
if not firebase_admin._apps:

    try:

        fb_sec = st.secrets["firebase"]

        parts = fb_sec["raw_data"].split(",")

        raw_key = (
            fb_sec["private_key"]
            .replace("-----BEGIN PRIVATE KEY-----", "")
            .replace("-----END PRIVATE KEY-----", "")
        )

        pure_key = re.sub(
            r"[^A-Za-z0-9+/=]",
            "",
            raw_key
        )

        fixed_key = (
            "-----BEGIN PRIVATE KEY-----\n"
            + "\n".join(textwrap.wrap(pure_key, 64))
            + "\n-----END PRIVATE KEY-----\n"
        )

        info_dict = {
            "type": "service_account",
            "project_id": parts[0],
            "private_key_id": parts[1],
            "private_key": fixed_key,
            "client_email": parts[2],
            "client_id": parts[3],
            "auth_uri":
                "https://accounts.google.com/o/oauth2/auth",
            "token_uri":
                "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url":
                "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url":
                f"https://www.googleapis.com/robot/v1/metadata/x509/{parts[2]}",
            "universe_domain": "googleapis.com"
        }

        firebase_admin.initialize_app(
            credentials.Certificate(info_dict)
        )

    except Exception as e:

        st.error(f"Firebase接続エラー: {e}")
        st.stop()

db = firestore.client()

# ============================================================
# 共通ユーティリティ
# ============================================================
def safe_text(text):

    return html.escape(str(text))


def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def verify_login(email, password):

    user_id = (
        email
        .replace("@", "_")
        .replace(".", "_")
    )

    doc = db.collection("users") \
        .document(user_id).get()

    if not doc.exists:
        return None

    user_data = doc.to_dict()

    input_pw = hashlib.sha256(
        password.encode()
    ).hexdigest()

    if input_pw == user_data.get("password"):
        return user_id

    return None


def get_user(uid):

    doc = db.collection("users") \
        .document(uid).get()

    if doc.exists:
        return doc.to_dict()

    return {}


def avatar_html(url, cls="avatar"):

    return (
        f'<img src="{url or DEFAULT_AVATAR}" '
        f'class="{cls}">'
    )


def image_to_base64(file):

    if not file:
        return None

    try:

        img = Image.open(file)

        img.thumbnail((800, 800))

        buf = BytesIO()

        img.save(buf, format="PNG")

        return (
            "data:image/png;base64,"
            + base64.b64encode(
                buf.getvalue()
            ).decode()
        )

    except Exception:

        st.error("画像変換エラー")
        return None

# ============================================================
# セッション
# ============================================================
defaults = {

    "logged_in": False,
    "current_page": "Home"

}

for k, v in defaults.items():

    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# ログイン画面
# ============================================================
if not st.session_state.logged_in:

    st.title("🐦 Iwattar")

    tab_login, tab_signup = st.tabs([
        "ログイン",
        "新規登録"
    ])

    # ログイン
    with tab_login:

        with st.form("login_form"):

            email = st.text_input("メール")

            password = st.text_input(
                "パスワード",
                type="password"
            )

            if st.form_submit_button("ログイン"):

                uid = verify_login(
                    email,
                    password
                )

                if uid:

                    st.session_state.logged_in = True
                    st.session_state.user_id = uid

                    st.rerun()

                else:

                    st.error(
                        "メールまたはパスワードが違います"
                    )

    # 新規登録
    with tab_signup:

        with st.form("signup_form"):

            new_email = st.text_input("メール")

            new_password = st.text_input(
                "パスワード",
                type="password"
            )

            new_name = st.text_input("表示名")

            new_handle = st.text_input("@ハンドル")

            if st.form_submit_button("登録"):

                try:

                    user_id = (
                        new_email
                        .replace("@", "_")
                        .replace(".", "_")
                    )

                    exists = db.collection("users") \
                        .document(user_id).get()

                    if exists.exists:

                        st.error("既に登録されています")
                        st.stop()

                    db.collection("users") \
                        .document(user_id).set({

                            "display_name":
                                safe_text(new_name),

                            "handle":
                                safe_text(new_handle),

                            "email":
                                new_email,

                            "password":
                                hash_password(new_password),

                            "avatar": None,

                            "bio": "",

                            "following": [],

                            "followers": []

                        })

                    st.success("登録完了")

                except Exception as ex:

                    st.error(f"登録エラー: {ex}")

    st.stop()

# ============================================================
# ログインユーザー
# ============================================================
me_ref = db.collection("users") \
    .document(st.session_state.user_id)

me = me_ref.get().to_dict() or {}

MY_NAME = me.get("display_name", "Guest")
MY_HANDLE = me.get("handle", "")
MY_AVATAR = me.get("avatar")

# ============================================================
# サイドバー
# ============================================================
with st.sidebar:

    st.markdown(
        f"""
        <center>

        <img
            src="{MY_AVATAR or DEFAULT_AVATAR}"
            class="icon-preview"
        >

        <h3>{safe_text(MY_NAME)}</h3>

        <p>@{safe_text(MY_HANDLE)}</p>

        </center>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    with st.form("profile_edit"):

        new_name = st.text_input(
            "表示名",
            value=MY_NAME
        )

        new_handle = st.text_input(
            "ハンドル",
            value=MY_HANDLE
        )

        new_bio = st.text_area(
            "自己紹介",
            value=me.get("bio", "")
        )

        avatar_file = st.file_uploader(
            "アイコン",
            type=["png", "jpg", "jpeg"]
        )

        if st.form_submit_button("保存"):

            update_data = {

                "display_name":
                    safe_text(new_name),

                "handle":
                    safe_text(new_handle),

                "bio":
                    safe_text(new_bio)

            }

            avatar_b64 = image_to_base64(
                avatar_file
            )

            if avatar_b64:
                update_data["avatar"] = avatar_b64

            me_ref.update(update_data)

            st.success("更新しました")

            st.rerun()

    st.markdown("---")

    if st.button("ログアウト"):

        for k in list(st.session_state.keys()):
            del st.session_state[k]

        st.rerun()

# ============================================================
# 投稿表示
# ============================================================
def render_tweet(doc_id, d):

    likes = d.get("likes", [])

    st.markdown('<div class="tweet-card">', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 6])

    with c1:

        st.markdown(
            avatar_html(d.get("avatar")),
            unsafe_allow_html=True
        )

    with c2:

        st.markdown(
            f"""
            <div class="display-name">
                {safe_text(d.get("user_name",""))}
            </div>

            <div class="screen-name">
                @{safe_text(d.get("handle",""))}
            </div>

            <div class="tweet-text">
                {safe_text(d.get("text",""))}
            </div>
            """,
            unsafe_allow_html=True
        )

        if d.get("image"):

            st.image(
                d["image"],
                use_container_width=True
            )

        liked = (
            st.session_state.user_id in likes
        )

        if st.button(
            f"{'❤️' if liked else '🤍'} {len(likes)}",
            key=f"like_{doc_id}"
        ):

            ref = db.collection("tweets") \
                .document(doc_id)

            if liked:

                ref.update({

                    "likes":
                        firestore.ArrayRemove([
                            st.session_state.user_id
                        ])

                })

            else:

                ref.update({

                    "likes":
                        firestore.ArrayUnion([
                            st.session_state.user_id
                        ])

                })

            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# メイン
# ============================================================
st.markdown(
    '<div class="main-scroll-area">',
    unsafe_allow_html=True
)

# ============================================================
# ホーム
# ============================================================
if st.session_state.current_page == "Home":

    st.markdown(
        '<div class="page-header">🏠 ホーム</div>',
        unsafe_allow_html=True
    )

    with st.form(
        "post_form",
        clear_on_submit=True
    ):

        post_text = st.text_area(
            "",
            placeholder="いまどうしてる？",
            label_visibility="collapsed"
        )

        post_image = st.file_uploader(
            "画像",
            type=["png", "jpg", "jpeg"]
        )

        if st.form_submit_button("ポストする"):

            if post_text.strip():

                db.collection("tweets").add({

                    "text":
                        safe_text(post_text),

                    "user_name":
                        MY_NAME,

                    "handle":
                        MY_HANDLE,

                    "user_id":
                        st.session_state.user_id,

                    "avatar":
                        MY_AVATAR,

                    "image":
                        image_to_base64(post_image),

                    "likes": [],

                    "created_at":
                        firestore.SERVER_TIMESTAMP

                })

                st.rerun()

    st.markdown("---")

    tweets = db.collection("tweets") \
        .order_by(
            "created_at",
            direction=firestore.Query.DESCENDING
        ) \
        .limit(50) \
        .stream()

    for doc in tweets:

        render_tweet(
            doc.id,
            doc.to_dict()
        )

# ============================================================
# 探索
# ============================================================
elif st.session_state.current_page == "Search":

    st.markdown(
        '<div class="page-header">🔍 探索</div>',
        unsafe_allow_html=True
    )

    st.info("探索機能")

# ============================================================
# 通知
# ============================================================
elif st.session_state.current_page == "Notifications":

    st.markdown(
        '<div class="page-header">🔔 通知</div>',
        unsafe_allow_html=True
    )

    st.info("通知機能")

# ============================================================
# DM
# ============================================================
elif st.session_state.current_page == "DM":

    st.markdown(
        '<div class="page-header">✉️ DM</div>',
        unsafe_allow_html=True
    )

    st.info("DM機能")

# ============================================================
# スクロール領域閉じる
# ============================================================
st.markdown(
    "</div>",
    unsafe_allow_html=True
)

# ============================================================
# ボトムナビ
# ============================================================
n1, n2, n3, n4 = st.columns(4)

with n1:
    # CSSでこのブロック全体を特定するための見えないマーカー
    st.markdown('<span id="nav-marker"></span>', unsafe_allow_html=True)
    
    if st.button("🏠", key="nav_home"):
        st.session_state.current_page = "Home"
        st.rerun()

with n2:
    if st.button("🔍", key="nav_search"):
        st.session_state.current_page = "Search"
        st.rerun()

with n3:
    if st.button("🔔", key="nav_notif"):
        st.session_state.current_page = "Notifications"
        st.rerun()

with n4:
    if st.button("✉️", key="nav_dm"):
        st.session_state.current_page = "DM"
        st.rerun()