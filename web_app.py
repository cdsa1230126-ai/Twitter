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

st.set_page_config(page_title="Iwattar", page_icon="🐦", layout="wide")

# 画像のデザインと投稿枠のスタイル
st.markdown(
    """
    <style>
    .stImage > img { border-radius: 50%; object-fit: cover; }
    .tweet-img img { border-radius: 10px !important; }
    .stButton > button { width: 100%; border-radius: 8px; font-weight: bold; }
    .tweet-container { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #f9f9f9; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. Firebase初期化 (秘密鍵洗浄ロジック搭載) ---
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
def convert_image_to_base64(uploaded_file, size=(300, 300)):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        img.thumbnail(size)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return None

# --- 3. セッション管理 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_page" not in st.session_state: st.session_state.current_page = "タイムライン"
if "saved_email" not in st.session_state: st.session_state.saved_email = ""
if "viewing_user_id" not in st.session_state: st.session_state.viewing_user_id = None

# --- 4. ログイン・アカウント作成画面 ---
if not st.session_state.logged_in:
    st.title("Iwattar")
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
                except: st.error("ログイン失敗。登録情報を確認してください。")
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

# ユーザー情報のリアルタイム取得
user_ref = db.collection('users').document(st.session_state.user_id)
user_data = user_ref.get().to_dict() or {}
st.session_state.user_name = user_data.get('display_name', "Guest")
st.session_state.avatar = user_data.get('avatar_data')

# --- 5. レイアウト構成 ---
side_col, main_col, nav_col = st.columns([2, 5, 2])

with side_col:
    st.title("Iwattar")
    if st.session_state.avatar: st.image(st.session_state.avatar, width=100)
    else: st.markdown("### 👤")
    st.write(f"**{st.session_state.user_name}**")
    if st.button("📝 プロフィールを編集"): st.session_state.current_page = "プロフィール編集"; st.rerun()
    if st.button("🖼️ マイページ"): 
        st.session_state.viewing_user_id = st.session_state.user_id
        st.session_state.current_page = "ユーザー投稿"; st.rerun()
    if st.button("🚪 ログアウト"): st.session_state.clear(); st.rerun()

with nav_col:
    st.markdown("### Menu")
    if st.button("🏠 タイムライン"): st.session_state.viewing_user_id = None; st.session_state.current_page = "タイムライン"; st.rerun()
    if st.button("🎓 ゼミ一覧"): st.session_state.current_page = "ゼミ一覧"; st.rerun()
    if st.button("📢 お知らせ"): st.session_state.current_page = "お知らせ"; st.rerun()
    st.divider()
    if st.session_state.is_admin_user:
        st.session_state.admin_mode_on = st.toggle("🛠️ 管理モード", value=st.session_state.admin_mode_on)

with main_col:
    page = st.session_state.current_page
    
    # --- プロフィール編集 ---
    if page == "プロフィール編集":
        st.header("プロフィール編集")
        with st.form("edit_profile"):
            new_name = st.text_input("新しい表示名", value=st.session_state.user_name)
            new_img = st.file_uploader("アイコン画像を変更", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("変更を保存"):
                upd = {"display_name": new_name}
                if new_img: upd["avatar_data"] = convert_image_to_base64(new_img)
                user_ref.update(upd); st.success("更新しました！"); st.rerun()
        if st.button("キャンセル"): st.session_state.current_page = "タイムライン"; st.rerun()

    # --- タイムライン & ユーザー投稿 ---
    elif page in ["タイムライン", "ユーザー投稿"]:
        st.header("マイページ" if page == "ユーザー投稿" else "タイムライン")
        
        if page == "タイムライン":
            with st.form("post"):
                txt = st.text_area("いまどうしてる？", max_chars=140)
                img = st.file_uploader("画像を添付", type=["jpg", "png", "jpeg"])
                if st.form_submit_button("ポスト"):
                    if txt.strip():
                        db.collection("tweets").add({
                            "text": txt, "user_name": st.session_state.user_name,
                            "user_id": st.session_state.user_id, "avatar_data": st.session_state.avatar,
                            "post_image": convert_image_to_base64(img, size=(500, 400)) if img else None,
                            "created_at": firestore.SERVER_TIMESTAMP
                        }); st.rerun()

        # クエリ構築
        q = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING)
        if st.session_state.viewing_user_id:
            q = q.where("user_id", "==", st.session_state.viewing_user_id)
            if st.button("← タイムラインに戻る"): st.session_state.viewing_user_id = None; st.rerun()

        for t in q.limit(20).stream():
            d = t.to_dict()
            with st.container():
                st.markdown('<div class="tweet-container">', unsafe_allow_html=True)
                c1, c2 = st.columns([1, 6])
                with c1:
                    # アイコンボタンでユーザー投稿へ
                    if st.button("👤", key=f"btn_{t.id}"):
                        st.session_state.viewing_user_id = d.get('user_id')
                        st.session_state.current_page = "ユーザー投稿"; st.rerun()
                    if d.get('avatar_data'): st.image(d.get('avatar_data'), width=50)
                with c2:
                    st.write(f"**{d.get('user_name')}**")
                    st.write(d.get('text'))
                    if d.get('post_image'): st.markdown('<div class="tweet-img">', unsafe_allow_html=True); st.image(d.get('post_image')); st.markdown('</div>', unsafe_allow_html=True)
                    if st.session_state.admin_mode_on or d.get('user_id') == st.session_state.user_id:
                        if st.button("🗑️ 削除", key=f"del_{t.id}"): db.collection("tweets").document(t.id).delete(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ゼミ一覧 ---
    elif page == "ゼミ一覧":
        if st.session_state.admin_mode_on:
            with st.expander("CSV一括登録"):
                csv = st.file_uploader("CSVを選択")
                if st.button("実行"):
                    try:
                        df = pd.read_csv(csv, encoding='cp932', header=None)
                        for _, r in df.iloc[1:].iterrows():
                            if str(r[0]) != "nan":
                                db.collection("zemis").document(str(r[0])).set({
                                    "name": str(r[1]), "prof": str(r[2]), "theme": str(r[5]), "career": str(r[8])
                                })
                        st.success("完了"); st.rerun()
                    except: st.error("エラー")
        
        for z in db.collection("zemis").stream():
            zd = z.to_dict()
            with st.container(border=True):
                st.subheader(f"{z.id} {zd.get('name')}")
                st.write(f"教員: {zd.get('prof')}")
                with st.expander("詳細"): st.write(f"テーマ: {zd.get('theme')}\n\n進路: {zd.get('career')}")
                if st.session_state.admin_mode_on:
                    if st.button("削除", key=f"z_{z.id}"): db.collection("zemis").document(z.id).delete(); st.rerun()

    # --- お知らせ ---
    elif page == "お知らせ":
        if st.session_state.admin_mode_on:
            with st.form("news"):
                nt = st.text_input("件名")
                if st.form_submit_button("配信"):
                    db.collection("news").add({"title": nt, "date": firestore.SERVER_TIMESTAMP}); st.rerun()
        for n in db.collection("news").order_by("date", direction=firestore.Query.DESCENDING).stream():
            st.info(f"📅 {n.to_dict().get('title')}")
            if st.session_state.admin_mode_on:
                if st.button("削除", key=f"n_{n.id}"): db.collection("news").document(n.id).delete(); st.rerun()