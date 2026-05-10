import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import base64
import re
import textwrap
from io import BytesIO
from PIL import Image
from datetime import datetime

# ============================================================
# 0. 基本設定
# ============================================================
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp"
DEFAULT_AVATAR = "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png"
st.set_page_config(page_title="Iwattar", page_icon=":bird:", layout="centered")

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
header {visibility: hidden;}
.main-scroll-area { padding-bottom: 130px; }

.page-header {
    font-size: 20px; font-weight: 800;
    padding: 15px;
    border-bottom: 1px solid rgba(128,128,128,0.2);
    position: sticky; top: 0;
    background-color: var(--background-color);
    z-index: 999;
}

.tweet-card {
    display: flex; padding: 12px 16px;
    border-bottom: 1px solid rgba(128,128,128,0.2);
}
.avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; margin-right: 12px; flex-shrink:0; }
.avatar-sm { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 8px; flex-shrink:0; }
.display-name { font-weight: 700; font-size: 15px; }
.screen-name { font-size: 13px; opacity: 0.55; }
.tweet-text { font-size: 15px; line-height: 1.5; margin: 4px 0 8px; }
.repost-label { font-size: 12px; opacity: 0.6; margin-bottom: 4px; }

.fixed-footer {
    position: fixed; bottom: 0; left: 0; width: 100%;
    background-color: var(--background-color);
    border-top: 1px solid rgba(128,128,128,0.2);
    padding: 8px 0; z-index: 999999;
}

div.stButton > button {
    background-color: transparent !important;
    border: none !important;
    color: var(--text-color) !important;
    font-size: 20px !important;
    width: 100%;
}

.comment-card {
    display: flex; padding: 8px 16px 8px 72px;
    border-bottom: 1px solid rgba(128,128,128,0.1);
    font-size: 14px;
}

.dm-bubble-me {
    background: #1d9bf0; color: #fff;
    border-radius: 18px 18px 4px 18px;
    padding: 8px 14px; margin: 4px 0;
    max-width: 75%; margin-left: auto;
    font-size: 14px; word-break: break-word;
}
.dm-bubble-other {
    background: rgba(128,128,128,0.15);
    border-radius: 18px 18px 18px 4px;
    padding: 8px 14px; margin: 4px 0;
    max-width: 75%; font-size: 14px; word-break: break-word;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1. Firebase 初期化
# ============================================================
if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        parts = fb_sec["raw_data"].split(",")
        raw_key = fb_sec["private_key"].replace("-----BEGIN PRIVATE KEY-----","").replace("-----END PRIVATE KEY-----","")
        pure_key = re.sub(r"[^A-Za-z0-9+/=]", "", raw_key)
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{chr(10).join(textwrap.wrap(pure_key,64))}\n-----END PRIVATE KEY-----\n"
        info_dict = {
            "type": "service_account", "project_id": parts[0], "private_key_id": parts[1],
            "private_key": fixed_key, "client_email": parts[2], "client_id": parts[3],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{parts[2]}",
            "universe_domain": "googleapis.com"
        }
        firebase_admin.initialize_app(credentials.Certificate(info_dict))
    except Exception as e:
        st.error(f"Firebase接続エラー: {e}"); st.stop()

db = firestore.client()

# ============================================================
# 2. 共通ユーティリティ
# ============================================================
def image_to_base64(file):
    if file:
        img = Image.open(file); img.thumbnail((800,800))
        buf = BytesIO(); img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    return None

def get_user(uid):
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() or {} if doc.exists else {}

def avatar_html(url, cls="avatar"):
    src = url or DEFAULT_AVATAR
    return f'<img src="{src}" class="{cls}">'

# ============================================================
# 3. セッション初期化
# ============================================================
defaults = {
    "logged_in": False, "current_page": "Home",
    "view_tweet_id": None, "view_profile_uid": None,
    "dm_partner_uid": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# 4. 認証画面
# ============================================================
if not st.session_state.logged_in:
    st.title("🐦 Iwattar")
    tab_l, tab_s = st.tabs(["ログイン", "新規登録"])
    with tab_l:
        with st.form("login_f"):
            e = st.text_input("メール")
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    u = auth.get_user_by_email(e)
                    st.session_state.logged_in = True
                    st.session_state.user_id = u.uid
                    st.rerun()
                except:
                    st.error("メールまたはパスワードが正しくありません")
    with tab_s:
        with st.form("signup_f"):
            ne = st.text_input("メール")
            np = st.text_input("パスワード（6文字以上）")
            nn = st.text_input("表示名")
            nh = st.text_input("@ハンドル名（英数字）")
            if st.form_submit_button("登録"):
                try:
                    user = auth.create_user(email=ne, password=np, display_name=nn)
                    db.collection("users").document(user.uid).set({
                        "display_name": nn, "handle": nh or user.uid[:8],
                        "avatar": None, "bio": "",
                        "followers": [], "following": []
                    })
                    st.success("登録完了！ログインしてください")
                except Exception as ex:
                    st.error(f"エラー: {ex}")
    st.stop()

# ============================================================
# 5. ログイン済みユーザーデータ
# ============================================================
me_ref = db.collection("users").document(st.session_state.user_id)
me = me_ref.get().to_dict() or {}
MY_NAME      = me.get("display_name", "Guest")
MY_HANDLE    = me.get("handle", "unknown")
MY_AVATAR    = me.get("avatar")
MY_FOLLOWING = me.get("following", [])
MY_FOLLOWERS = me.get("followers", [])

# ============================================================
# 6. サイドバー
# ============================================================
with st.sidebar:
    st.image(MY_AVATAR or DEFAULT_AVATAR, width=72)
    st.markdown(f"**{MY_NAME}**")
    st.caption(f"@{MY_HANDLE}")
    st.caption(f"フォロー {len(MY_FOLLOWING)}　フォロワー {len(MY_FOLLOWERS)}")
    st.markdown("---")
    if st.button("🚪 ログアウト"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ============================================================
# 7. 投稿カード描画ヘルパー
# ============================================================
def render_tweet(doc_id, d, show_actions=True):
    is_repost = d.get("repost_of") is not None
    orig = d
    tweet_id_for_action = doc_id

    if is_repost:
        orig_doc = db.collection("tweets").document(d["repost_of"]).get()
        if not orig_doc.exists:
            return
        orig = orig_doc.to_dict()
        tweet_id_for_action = d["repost_of"]

    likes         = orig.get("likes", [])
    reposts_list  = orig.get("reposts", [])
    comment_docs  = list(db.collection("tweets").document(tweet_id_for_action).collection("comments").stream())
    comment_count = len(comment_docs)

    col_av, col_body = st.columns([1, 6])
    with col_av:
        st.markdown(avatar_html(orig.get("avatar")), unsafe_allow_html=True)
    with col_body:
        if is_repost:
            st.markdown(f'<div class="repost-label">🔁 {MY_NAME} がリポスト</div>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="display-name">{orig.get("user_name","")}</span> '
            f'<span class="screen-name">@{orig.get("handle","")}</span>',
            unsafe_allow_html=True
        )
        st.markdown(f'<div class="tweet-text">{orig.get("text","")}</div>', unsafe_allow_html=True)
        if orig.get("image"):
            st.image(orig["image"], use_container_width=True)

        if show_actions:
            liked    = st.session_state.user_id in likes
            reposted = st.session_state.user_id in reposts_list
            a1, a2, a3, a4 = st.columns(4)

            # いいね
            with a1:
                if st.button(f"{'❤️' if liked else '🤍'} {len(likes)}", key=f"like_{doc_id}"):
                    t_ref = db.collection("tweets").document(tweet_id_for_action)
                    if liked:
                        t_ref.update({"likes": firestore.ArrayRemove([st.session_state.user_id])})
                    else:
                        t_ref.update({"likes": firestore.ArrayUnion([st.session_state.user_id])})
                        if orig.get("user_id") != st.session_state.user_id:
                            db.collection("notifications").add({
                                "to_uid": orig["user_id"], "from_uid": st.session_state.user_id,
                                "from_name": MY_NAME, "type": "like",
                                "tweet_id": tweet_id_for_action,
                                "tweet_text": orig.get("text","")[:30],
                                "created_at": firestore.SERVER_TIMESTAMP, "read": False
                            })
                    st.rerun()

            # リポスト
            with a2:
                if st.button(f"{'🔁' if reposted else '↩️'} {len(reposts_list)}", key=f"rp_{doc_id}"):
                    t_ref = db.collection("tweets").document(tweet_id_for_action)
                    if reposted:
                        t_ref.update({"reposts": firestore.ArrayRemove([st.session_state.user_id])})
                        for rp in db.collection("tweets")\
                                .where("repost_of","==", tweet_id_for_action)\
                                .where("user_id","==", st.session_state.user_id).stream():
                            db.collection("tweets").document(rp.id).delete()
                    else:
                        t_ref.update({"reposts": firestore.ArrayUnion([st.session_state.user_id])})
                        db.collection("tweets").add({
                            "repost_of": tweet_id_for_action,
                            "user_id": st.session_state.user_id,
                            "user_name": MY_NAME, "handle": MY_HANDLE, "avatar": MY_AVATAR,
                            "created_at": firestore.SERVER_TIMESTAMP
                        })
                        if orig.get("user_id") != st.session_state.user_id:
                            db.collection("notifications").add({
                                "to_uid": orig["user_id"], "from_uid": st.session_state.user_id,
                                "from_name": MY_NAME, "type": "repost",
                                "tweet_id": tweet_id_for_action,
                                "tweet_text": orig.get("text","")[:30],
                                "created_at": firestore.SERVER_TIMESTAMP, "read": False
                            })
                    st.rerun()

            # コメント（詳細ページへ）
            with a3:
                if st.button(f"💬 {comment_count}", key=f"cm_{doc_id}"):
                    st.session_state.view_tweet_id = tweet_id_for_action
                    st.session_state.current_page = "TweetDetail"
                    st.rerun()

            # 削除（自分の投稿のみ）
            with a4:
                if orig.get("user_id") == st.session_state.user_id:
                    if st.button("🗑️", key=f"del_{doc_id}"):
                        db.collection("tweets").document(tweet_id_for_action).delete()
                        st.rerun()

    st.markdown("---")

# ============================================================
# 8. メイン画面
# ============================================================
st.markdown('<div class="main-scroll-area">', unsafe_allow_html=True)

# ── ホーム ──────────────────────────────────────────────────
if st.session_state.current_page == "Home":
    st.markdown('<div class="page-header">🏠 ホーム</div>', unsafe_allow_html=True)
    tab_all, tab_follow = st.tabs(["✨ おすすめ", "👥 フォロー中"])

    def post_form(suffix):
        c1, c2 = st.columns([1, 6])
        with c1:
            st.markdown(avatar_html(MY_AVATAR), unsafe_allow_html=True)
        with c2:
            txt = st.text_area("", placeholder="いまどうしてる？",
                               key=f"tw_in_{suffix}", label_visibility="collapsed")
            img_file = st.file_uploader("画像", type=["jpg","png"],
                                        label_visibility="collapsed", key=f"tw_img_{suffix}")
            if st.button("ポストする", key=f"tw_btn_{suffix}"):
                if txt.strip():
                    db.collection("tweets").add({
                        "text": txt, "user_name": MY_NAME, "handle": MY_HANDLE,
                        "user_id": st.session_state.user_id, "avatar": MY_AVATAR,
                        "image": image_to_base64(img_file),
                        "likes": [], "reposts": [],
                        "created_at": firestore.SERVER_TIMESTAMP
                    })
                    st.rerun()

    with tab_all:
        post_form("all")
        st.markdown("---")
        for doc in db.collection("tweets")\
                .order_by("created_at", direction=firestore.Query.DESCENDING)\
                .limit(30).stream():
            render_tweet(doc.id, doc.to_dict())

    with tab_follow:
        post_form("follow")
        st.markdown("---")
        if not MY_FOLLOWING:
            st.info("フォローしているユーザーがいません。探索からフォローしましょう！")
        else:
            shown = 0
            for doc in db.collection("tweets")\
                    .order_by("created_at", direction=firestore.Query.DESCENDING)\
                    .limit(50).stream():
                d = doc.to_dict()
                if d.get("user_id") in MY_FOLLOWING:
                    render_tweet(doc.id, d); shown += 1
            if shown == 0:
                st.info("フォロー中のユーザーの投稿がありません")

# ── 探索 / フォロー ─────────────────────────────────────────
elif st.session_state.current_page == "Search":
    st.markdown('<div class="page-header">🔍 探索</div>', unsafe_allow_html=True)
    query = st.text_input("ユーザー名 or @ハンドルで検索", placeholder="@handle または 表示名")

    if query:
        results = []
        for u in db.collection("users").stream():
            ud = u.to_dict()
            if (query.lower() in ud.get("display_name","").lower() or
                    query.lower() in ud.get("handle","").lower()):
                results.append((u.id, ud))

        if not results:
            st.info("ユーザーが見つかりませんでした")
        for uid, ud in results:
            if uid == st.session_state.user_id:
                continue
            c1, c2, c3 = st.columns([1, 4, 2])
            with c1:
                st.markdown(avatar_html(ud.get("avatar"), "avatar-sm"), unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{ud.get('display_name','')}** @{ud.get('handle','')}")
                st.caption(ud.get("bio",""))
            with c3:
                is_following = uid in MY_FOLLOWING
                label = "フォロー解除" if is_following else "フォロー"
                if st.button(label, key=f"follow_{uid}"):
                    if is_following:
                        me_ref.update({"following": firestore.ArrayRemove([uid])})
                        db.collection("users").document(uid).update(
                            {"followers": firestore.ArrayRemove([st.session_state.user_id])})
                    else:
                        me_ref.update({"following": firestore.ArrayUnion([uid])})
                        db.collection("users").document(uid).update(
                            {"followers": firestore.ArrayUnion([st.session_state.user_id])})
                        db.collection("notifications").add({
                            "to_uid": uid, "from_uid": st.session_state.user_id,
                            "from_name": MY_NAME, "type": "follow",
                            "created_at": firestore.SERVER_TIMESTAMP, "read": False
                        })
                    st.rerun()
            if st.button("投稿を見る →", key=f"prof_{uid}"):
                st.session_state.view_profile_uid = uid
                st.session_state.current_page = "UserProfile"
                st.rerun()
            st.markdown("---")
    else:
        st.caption("ユーザーを検索してフォローしましょう")

# ── 通知 ────────────────────────────────────────────────────
elif st.session_state.current_page == "Notifications":
    st.markdown('<div class="page-header">🔔 通知</div>', unsafe_allow_html=True)
    notifs = list(
        db.collection("notifications")
        .where("to_uid","==", st.session_state.user_id)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(30).stream()
    )
    if not notifs:
        st.info("通知はありません")
    for n in notifs:
        nd = n.to_dict()
        ntype = nd.get("type","")
        fname = nd.get("from_name","")
        ttext = nd.get("tweet_text","")
        if ntype == "like":
            msg = f"❤️ **{fname}** があなたの投稿にいいねしました 「{ttext}…」"
        elif ntype == "repost":
            msg = f"🔁 **{fname}** があなたの投稿をリポストしました 「{ttext}…」"
        elif ntype == "follow":
            msg = f"👤 **{fname}** があなたをフォローしました"
        elif ntype == "comment":
            msg = f"💬 **{fname}** がコメントしました 「{ttext}…」"
        else:
            msg = f"📢 {fname} からの通知"
        read = nd.get("read", False)
        bg = "" if read else "background:rgba(29,155,240,0.06);border-radius:8px;padding:6px;"
        st.markdown(f'<div style="{bg}">{msg}</div>', unsafe_allow_html=True)
        if not read:
            db.collection("notifications").document(n.id).update({"read": True})
        st.markdown("---")

# ── DM ──────────────────────────────────────────────────────
elif st.session_state.current_page == "DM":
    st.markdown('<div class="page-header">✉️ DM</div>', unsafe_allow_html=True)

    if not st.session_state.dm_partner_uid:
        # 会話リスト（フォロー中のユーザー）
        st.caption("フォローしているユーザーにDMを送れます")
        if not MY_FOLLOWING:
            st.info("フォローしているユーザーがいません")
        else:
            for fuid in MY_FOLLOWING:
                fdata = get_user(fuid)
                c1, c2, c3 = st.columns([1, 4, 2])
                with c1:
                    st.markdown(avatar_html(fdata.get("avatar"), "avatar-sm"), unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{fdata.get('display_name','')}** @{fdata.get('handle','')}")
                with c3:
                    if st.button("開く", key=f"dm_open_{fuid}"):
                        st.session_state.dm_partner_uid = fuid
                        st.rerun()
                st.markdown("---")
    else:
        # チャット画面
        partner_uid = st.session_state.dm_partner_uid
        pdata = get_user(partner_uid)
        if st.button("← 戻る"):
            st.session_state.dm_partner_uid = None
            st.rerun()
        st.markdown(f"**{pdata.get('display_name','')}** @{pdata.get('handle','')} とのDM")
        st.markdown("---")

        room_id = "_".join(sorted([st.session_state.user_id, partner_uid]))
        msgs = list(
            db.collection("dm_rooms").document(room_id)
            .collection("messages")
            .order_by("created_at").limit(50).stream()
        )
        for m in msgs:
            md = m.to_dict()
            is_me = md.get("sender_uid") == st.session_state.user_id
            cls = "dm-bubble-me" if is_me else "dm-bubble-other"
            st.markdown(f'<div class="{cls}">{md.get("text","")}</div>', unsafe_allow_html=True)

        st.markdown("---")
        with st.form("dm_form", clear_on_submit=True):
            dm_text = st.text_input("", label_visibility="collapsed", placeholder="メッセージを入力…")
            if st.form_submit_button("送信 ▶"):
                if dm_text.strip():
                    db.collection("dm_rooms").document(room_id)\
                        .collection("messages").add({
                            "text": dm_text,
                            "sender_uid": st.session_state.user_id,
                            "sender_name": MY_NAME,
                            "created_at": firestore.SERVER_TIMESTAMP
                        })
                    st.rerun()

# ── 自分のプロフィール ───────────────────────────────────────
elif st.session_state.current_page == "Profile":
    st.markdown('<div class="page-header">👤 プロフィール設定</div>', unsafe_allow_html=True)
    st.image(MY_AVATAR or DEFAULT_AVATAR, width=100)
    new_name   = st.text_input("表示名", value=MY_NAME)
    new_handle = st.text_input("@ハンドル", value=MY_HANDLE)
    new_bio    = st.text_area("自己紹介", value=me.get("bio",""))
    new_avatar = st.file_uploader("アイコン画像", type=["jpg","png"])
    if st.button("保存する"):
        upd = {"display_name": new_name, "handle": new_handle, "bio": new_bio}
        if new_avatar:
            upd["avatar"] = image_to_base64(new_avatar)
        me_ref.update(upd)
        st.success("更新しました！")
        st.rerun()
    st.markdown("---")
    st.subheader("自分の投稿")
    for doc in db.collection("tweets")\
            .where("user_id","==", st.session_state.user_id)\
            .order_by("created_at", direction=firestore.Query.DESCENDING)\
            .limit(20).stream():
        render_tweet(doc.id, doc.to_dict())

# ── 他ユーザープロフィール ───────────────────────────────────
elif st.session_state.current_page == "UserProfile":
    uid = st.session_state.view_profile_uid
    if not uid:
        st.session_state.current_page = "Home"; st.rerun()
    udata = get_user(uid)
    if st.button("← 戻る"):
        st.session_state.current_page = "Search"; st.rerun()
    st.markdown(avatar_html(udata.get("avatar")), unsafe_allow_html=True)
    st.markdown(f"## {udata.get('display_name','')}")
    st.caption(
        f"@{udata.get('handle','')}　"
        f"フォロー {len(udata.get('following',[]))}　"
        f"フォロワー {len(udata.get('followers',[]))}"
    )
    if udata.get("bio"):
        st.write(udata["bio"])
    is_following = uid in MY_FOLLOWING
    if st.button("フォロー解除" if is_following else "フォローする"):
        if is_following:
            me_ref.update({"following": firestore.ArrayRemove([uid])})
            db.collection("users").document(uid).update(
                {"followers": firestore.ArrayRemove([st.session_state.user_id])})
        else:
            me_ref.update({"following": firestore.ArrayUnion([uid])})
            db.collection("users").document(uid).update(
                {"followers": firestore.ArrayUnion([st.session_state.user_id])})
        st.rerun()
    st.markdown("---")
    for doc in db.collection("tweets")\
            .where("user_id","==", uid)\
            .order_by("created_at", direction=firestore.Query.DESCENDING)\
            .limit(20).stream():
        render_tweet(doc.id, doc.to_dict())

# ── 投稿詳細（コメント）───────────────────────────────────────
elif st.session_state.current_page == "TweetDetail":
    tweet_id = st.session_state.view_tweet_id
    if not tweet_id:
        st.session_state.current_page = "Home"; st.rerun()
    if st.button("← 戻る"):
        st.session_state.current_page = "Home"; st.rerun()

    t_doc = db.collection("tweets").document(tweet_id).get()
    if not t_doc.exists:
        st.error("投稿が見つかりません"); st.stop()

    render_tweet(tweet_id, t_doc.to_dict())
    st.markdown("**💬 コメント**")

    with st.form("comment_form", clear_on_submit=True):
        cm_text = st.text_input("", label_visibility="collapsed", placeholder="返信する…")
        if st.form_submit_button("返信する"):
            if cm_text.strip():
                db.collection("tweets").document(tweet_id).collection("comments").add({
                    "text": cm_text, "user_name": MY_NAME, "handle": MY_HANDLE,
                    "user_id": st.session_state.user_id, "avatar": MY_AVATAR,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                td = t_doc.to_dict()
                if td.get("user_id") != st.session_state.user_id:
                    db.collection("notifications").add({
                        "to_uid": td["user_id"], "from_uid": st.session_state.user_id,
                        "from_name": MY_NAME, "type": "comment",
                        "tweet_id": tweet_id, "tweet_text": cm_text[:30],
                        "created_at": firestore.SERVER_TIMESTAMP, "read": False
                    })
                st.rerun()

    for c in db.collection("tweets").document(tweet_id).collection("comments")\
            .order_by("created_at").stream():
        cd = c.to_dict()
        st.markdown(
            f'<div class="comment-card">'
            f'{avatar_html(cd.get("avatar"), "avatar-sm")}'
            f'<div><b>{cd.get("user_name","")}</b> '
            f'<span style="opacity:.5;font-size:12px;">@{cd.get("handle","")}</span>'
            f'<br>{cd.get("text","")}</div></div>',
            unsafe_allow_html=True
        )

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# 9. ボトムナビゲーション（5タブ）
# ============================================================
unread_count = len(list(
    db.collection("notifications")
    .where("to_uid","==", st.session_state.user_id)
    .where("read","==", False)
    .limit(10).stream()
))
notif_icon = f"🔔{unread_count}" if unread_count > 0 else "🔔"

st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
n1, n2, n3, n4, n5 = st.columns(5)
with n1:
    if st.button("🏠", key="nav_home"):
        st.session_state.current_page = "Home"; st.rerun()
with n2:
    if st.button("🔍", key="nav_search"):
        st.session_state.current_page = "Search"; st.rerun()
with n3:
    if st.button(notif_icon, key="nav_notif"):
        st.session_state.current_page = "Notifications"; st.rerun()
with n4:
    if st.button("✉️", key="nav_dm"):
        st.session_state.dm_partner_uid = None
        st.session_state.current_page = "DM"; st.rerun()
with n5:
    if st.button("👤", key="nav_profile"):
        st.session_state.current_page = "Profile"; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)