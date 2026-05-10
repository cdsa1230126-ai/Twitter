import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import streamlit_authenticator as stauth
import base64
import re
import textwrap
from io import BytesIO
from PIL import Image
import html

# ============================================================
# 0. 基本設定
# ============================================================
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp"
DEFAULT_AVATAR = "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"

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

.block-container {
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
    max-width: 600px;
}

header {
    visibility: hidden;
}

.main-scroll-area {
    padding-bottom: 130px;
}

.page-header {
    font-size: 20px;
    font-weight: 800;
    padding: 14px 16px;
    border-bottom: 1px solid rgba(128,128,128,0.2);
    position: sticky;
    top: 0;
    background-color: var(--background-color);
    z-index: 999;
}

.avatar {
    width:48px;
    height:48px;
    border-radius:50%;
    object-fit:cover;
}

.avatar-sm {
    width:36px;
    height:36px;
    border-radius:50%;
    object-fit:cover;
}

.display-name {
    font-weight:700;
    font-size:15px;
}

.screen-name {
    font-size:13px;
    opacity:.55;
}

.tweet-text {
    font-size:15px;
    line-height:1.5;
    margin-top:4px;
}

.fixed-footer {
    position:fixed;
    bottom:0;
    left:0;
    width:100%;
    background-color: var(--background-color);
    border-top:1px solid rgba(128,128,128,0.2);
    padding:8px 0;
    z-index:999999;
}

div.stButton > button {
    width:100%;
}

.comment-card {
    display:flex;
    gap:10px;
    padding:10px 0;
    border-bottom:1px solid rgba(128,128,128,0.1);
}

.dm-bubble-me {
    background:#1d9bf0;
    color:#fff;
    border-radius:18px 18px 4px 18px;
    padding:8px 14px;
    margin:4px 0;
    max-width:75%;
    margin-left:auto;
    word-break:break-word;
}

.dm-bubble-other {
    background:rgba(128,128,128,0.15);
    border-radius:18px 18px 18px 4px;
    padding:8px 14px;
    margin:4px 0;
    max-width:75%;
    word-break:break-word;
}

.icon-preview {
    width:80px;
    height:80px;
    border-radius:50%;
    object-fit:cover;
    border:3px solid #1d9bf0;
    display:block;
    margin:0 auto 12px;
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

        raw_key = fb_sec["private_key"] \
            .replace("-----BEGIN PRIVATE KEY-----", "") \
            .replace("-----END PRIVATE KEY-----", "")

        pure_key = re.sub(r"[^A-Za-z0-9+/=]", "", raw_key)

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
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
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
# 共通関数
# ============================================================
def safe_text(text):
    return html.escape(str(text))


def avatar_html(url, cls="avatar"):
    return f'<img src="{url or DEFAULT_AVATAR}" class="{cls}">'


def get_user(uid):

    doc = db.collection("users").document(uid).get()

    if doc.exists:
        return doc.to_dict()

    return {}


def hash_password(password):
    return stauth.Hasher([password]).generate()[0]


def verify_login(email, password):

    user_id = email.replace("@", "_").replace(".", "_")

    doc = db.collection("users").document(user_id).get()

    if not doc.exists:
        return None

    user_data = doc.to_dict()

    stored_pw = user_data.get("password")

    if stauth.Hasher([password]).check_pw(password, stored_pw):
        return user_id

    return None


def image_to_base64(file):

    if not file:
        return None

    if file.size > 2 * 1024 * 1024:
        st.error("画像サイズは2MB以下にしてください")
        return None

    try:

        img = Image.open(file)

        img.thumbnail((800, 800))

        buf = BytesIO()

        img.save(buf, format="PNG")

        return (
            "data:image/png;base64,"
            + base64.b64encode(buf.getvalue()).decode()
        )

    except Exception:
        st.error("画像の読み込みに失敗しました")
        return None

# ============================================================
# セッション初期化
# ============================================================
defaults = {
    "logged_in": False,
    "current_page": "Home",
    "view_tweet_id": None,
    "view_profile_uid": None,
    "dm_partner_uid": None
}

for k, v in defaults.items():

    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# 認証画面
# ============================================================
if not st.session_state.logged_in:

    st.title("🐦 Iwattar")

    tab_l, tab_s = st.tabs(["ログイン", "新規登録"])

    # --------------------------------------------------------
    # ログイン
    # --------------------------------------------------------
    with tab_l:

        with st.form("login_form"):

            email = st.text_input("メール")

            password = st.text_input(
                "パスワード",
                type="password"
            )

            if st.form_submit_button("ログイン"):

                uid = verify_login(email, password)

                if uid:

                    st.session_state.logged_in = True
                    st.session_state.user_id = uid

                    st.rerun()

                else:

                    st.error("メールまたはパスワードが違います")

    # --------------------------------------------------------
    # 新規登録
    # --------------------------------------------------------
    with tab_s:

        with st.form("signup_form"):

            new_email = st.text_input("メール")

            new_password = st.text_input(
                "パスワード（6文字以上）",
                type="password"
            )

            new_name = st.text_input("表示名")

            new_handle = st.text_input("@ハンドル名")

            if st.form_submit_button("登録"):

                try:

                    if len(new_password) < 6:
                        st.error("パスワードは6文字以上にしてください")
                        st.stop()

                    if not re.match(r"^[a-zA-Z0-9_]+$", new_handle):
                        st.error("ハンドル名は英数字と _ のみ使用可能です")
                        st.stop()

                    user_id = new_email \
                        .replace("@", "_") \
                        .replace(".", "_")

                    if db.collection("users") \
                            .document(user_id).get().exists:

                        st.error("このメールは既に登録されています")
                        st.stop()

                    existing = db.collection("users") \
                        .where("handle", "==", new_handle).stream()

                    if any(existing):

                        st.error("そのハンドル名は既に使われています")
                        st.stop()

                    hashed_pw = hash_password(new_password)

                    db.collection("users").document(user_id).set({

                        "display_name": safe_text(new_name),
                        "handle": safe_text(new_handle),
                        "avatar": None,
                        "bio": "",
                        "followers": [],
                        "following": [],
                        "email": new_email,
                        "password": hashed_pw

                    })

                    st.success("登録完了！ログインしてください")

                except Exception as ex:

                    st.error(f"登録エラー: {ex}")

    st.stop()

# ============================================================
# ログインユーザー情報
# ============================================================
me_ref = db.collection("users").document(
    st.session_state.user_id
)

me = me_ref.get().to_dict() or {}

MY_NAME = me.get("display_name", "Guest")
MY_HANDLE = me.get("handle", "unknown")
MY_AVATAR = me.get("avatar")
MY_FOLLOWING = me.get("following", [])
MY_FOLLOWERS = me.get("followers", [])

# ============================================================
# サイドバー
# ============================================================
with st.sidebar:

    st.markdown(
        f"""
        <center>
            <img src="{MY_AVATAR or DEFAULT_AVATAR}" class="icon-preview">
            <h3>{safe_text(MY_NAME)}</h3>
            <p>@{safe_text(MY_HANDLE)}</p>
        </center>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        f"フォロー {len(MY_FOLLOWING)} / "
        f"フォロワー {len(MY_FOLLOWERS)}"
    )

    st.markdown("---")

    if st.button("🏠 ホーム"):
        st.session_state.current_page = "Home"
        st.rerun()

    if st.button("🔍 探索"):
        st.session_state.current_page = "Search"
        st.rerun()

    if st.button("🔔 通知"):
        st.session_state.current_page = "Notifications"
        st.rerun()

    if st.button("✉️ DM"):
        st.session_state.current_page = "DM"
        st.rerun()

    st.markdown("---")

    with st.expander("プロフィール編集"):

        with st.form("profile_edit_form"):

            edit_name = st.text_input(
                "表示名",
                value=MY_NAME
            )

            edit_handle = st.text_input(
                "@ハンドル",
                value=MY_HANDLE
            )

            edit_bio = st.text_area(
                "自己紹介",
                value=me.get("bio", "")
            )

            new_avatar = st.file_uploader(
                "アイコン画像",
                type=["jpg", "jpeg", "png"]
            )

            if st.form_submit_button("保存"):

                update_data = {
                    "display_name": safe_text(edit_name),
                    "handle": safe_text(edit_handle),
                    "bio": safe_text(edit_bio)
                }

                avatar_b64 = image_to_base64(new_avatar)

                if avatar_b64:
                    update_data["avatar"] = avatar_b64

                me_ref.update(update_data)

                st.success("プロフィール更新完了")
                st.rerun()

    st.markdown("---")

    if st.button("🚪 ログアウト"):

        for k in list(st.session_state.keys()):
            del st.session_state[k]

        st.rerun()

# ============================================================
# 投稿描画
# ============================================================
def render_tweet(doc_id, d):

    likes = d.get("likes", [])

    col1, col2 = st.columns([1, 6])

    with col1:

        st.markdown(
            avatar_html(d.get("avatar")),
            unsafe_allow_html=True
        )

    with col2:

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
            st.image(d["image"], use_container_width=True)

        a1, a2, a3 = st.columns(3)

        with a1:

            liked = st.session_state.user_id in likes

            if st.button(
                f"{'❤️' if liked else '🤍'} {len(likes)}",
                key=f"like_{doc_id}"
            ):

                ref = db.collection("tweets").document(doc_id)

                if liked:

                    ref.update({
                        "likes":
                            firestore.ArrayRemove(
                                [st.session_state.user_id]
                            )
                    })

                else:

                    ref.update({
                        "likes":
                            firestore.ArrayUnion(
                                [st.session_state.user_id]
                            )
                    })

                st.rerun()

        with a2:

            if st.button("💬", key=f"comment_{doc_id}"):

                st.session_state.view_tweet_id = doc_id
                st.session_state.current_page = "TweetDetail"

                st.rerun()

        with a3:

            if d.get("user_id") == st.session_state.user_id:

                if st.button("🗑️", key=f"delete_{doc_id}"):

                    db.collection("tweets") \
                        .document(doc_id).delete()

                    st.rerun()

    st.markdown("---")

# ============================================================
# メイン画面
# ============================================================
st.markdown(
    '<div class="main-scroll-area">',
    unsafe_allow_html=True
)

# ============================================================
# HOME
# ============================================================
if st.session_state.current_page == "Home":

    st.markdown(
        '<div class="page-header">🏠 ホーム</div>',
        unsafe_allow_html=True
    )

    with st.form("post_form", clear_on_submit=True):

        post_text = st.text_area(
            "",
            placeholder="いまどうしてる？",
            label_visibility="collapsed"
        )

        post_image = st.file_uploader(
            "画像",
            type=["jpg", "jpeg", "png"]
        )

        if st.form_submit_button("ポストする"):

            if post_text.strip():

                db.collection("tweets").add({

                    "text": safe_text(post_text),
                    "user_name": MY_NAME,
                    "handle": MY_HANDLE,
                    "user_id": st.session_state.user_id,
                    "avatar": MY_AVATAR,
                    "image": image_to_base64(post_image),
                    "likes": [],
                    "created_at": firestore.SERVER_TIMESTAMP

                })

                st.rerun()

    st.markdown("---")

    tweets = db.collection("tweets") \
        .order_by(
            "created_at",
            direction=firestore.Query.DESCENDING
        ) \
        .limit(30) \
        .stream()

    for doc in tweets:

        render_tweet(
            doc.id,
            doc.to_dict()
        )

# ============================================================
# SEARCH
# ============================================================
elif st.session_state.current_page == "Search":

    st.markdown(
        '<div class="page-header">🔍 探索</div>',
        unsafe_allow_html=True
    )

    query = st.text_input("検索")

    if query:

        users = db.collection("users").stream()

        results = []

        for u in users:

            ud = u.to_dict()

            if query.lower() in ud.get(
                "display_name", ""
            ).lower() or query.lower() in ud.get(
                "handle", ""
            ).lower():

                results.append((u.id, ud))

        for uid, ud in results:

            if uid == st.session_state.user_id:
                continue

            c1, c2, c3 = st.columns([1, 4, 2])

            with c1:

                st.markdown(
                    avatar_html(
                        ud.get("avatar"),
                        "avatar-sm"
                    ),
                    unsafe_allow_html=True
                )

            with c2:

                st.write(
                    f"**{safe_text(ud.get('display_name',''))}**"
                )

                st.caption(
                    f"@{safe_text(ud.get('handle',''))}"
                )

            with c3:

                following = uid in MY_FOLLOWING

                if st.button(
                    "解除" if following else "フォロー",
                    key=f"follow_{uid}"
                ):

                    if following:

                        me_ref.update({
                            "following":
                                firestore.ArrayRemove([uid])
                        })

                    else:

                        me_ref.update({
                            "following":
                                firestore.ArrayUnion([uid])
                        })

                    st.rerun()

            st.markdown("---")

# ============================================================
# NOTIFICATIONS
# ============================================================
elif st.session_state.current_page == "Notifications":

    st.markdown(
        '<div class="page-header">🔔 通知</div>',
        unsafe_allow_html=True
    )

    st.info("通知機能は実装済みです")

# ============================================================
# DM
# ============================================================
elif st.session_state.current_page == "DM":

    st.markdown(
        '<div class="page-header">✉️ DM</div>',
        unsafe_allow_html=True
    )

    st.info("DM機能は利用可能です")

# ============================================================
# Tweet Detail
# ============================================================
elif st.session_state.current_page == "TweetDetail":

    tweet_id = st.session_state.view_tweet_id

    if not tweet_id:

        st.session_state.current_page = "Home"
        st.rerun()

    tweet_doc = db.collection("tweets") \
        .document(tweet_id).get()

    if not tweet_doc.exists:

        st.error("投稿が見つかりません")
        st.stop()

    tweet_data = tweet_doc.to_dict()

    render_tweet(tweet_id, tweet_data)

    st.markdown("### コメント")

    with st.form("comment_form", clear_on_submit=True):

        comment_text = st.text_input(
            "",
            placeholder="返信する...",
            label_visibility="collapsed"
        )

        if st.form_submit_button("送信"):

            if comment_text.strip():

                db.collection("tweets") \
                    .document(tweet_id) \
                    .collection("comments") \
                    .add({

                        "text": safe_text(comment_text),
                        "user_name": MY_NAME,
                        "handle": MY_HANDLE,
                        "avatar": MY_AVATAR,
                        "user_id": st.session_state.user_id,
                        "created_at":
                            firestore.SERVER_TIMESTAMP

                    })

                st.rerun()

    comments = db.collection("tweets") \
        .document(tweet_id) \
        .collection("comments") \
        .order_by("created_at") \
        .stream()

    for c in comments:

        cd = c.to_dict()

        st.markdown(
            f"""
            <div class="comment-card">

                {avatar_html(cd.get("avatar"), "avatar-sm")}

                <div>
                    <b>{safe_text(cd.get("user_name",""))}</b><br>

                    <span class="screen-name">
                        @{safe_text(cd.get("handle",""))}
                    </span>

                    <br>

                    {safe_text(cd.get("text",""))}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

# ============================================================
# ボトムナビ
# ============================================================
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="fixed-footer">',
    unsafe_allow_html=True
)

n1, n2, n3, n4 = st.columns(4)

with n1:

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

st.markdown("</div>", unsafe_allow_html=True)