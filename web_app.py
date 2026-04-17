import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json
import base64
from io import BytesIO
from PIL import Image

# --- 設定：管理者のメールアドレス ---
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp" 

st.set_page_config(page_title="Iwattar", page_icon="🐦", layout="wide")

# --- 1. Firebase初期化 ---
if not firebase_admin._apps:
    try:
        json_string = st.secrets["firebase"]["service_account_json"]
        info_dict = json.loads(json_string)
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase初期化失敗: {e}")
        st.stop()

db = firestore.client()

# --- 2. 画像変換用関数 ---
def convert_image_to_base64(uploaded_file, size=(400, 300)):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        img.thumbnail(size)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return None

# --- 3. セッション状態の初期化 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin_user" not in st.session_state:
    st.session_state.is_admin_user = False
if "admin_mode_on" not in st.session_state:
    st.session_state.admin_mode_on = False

# --- 4. ログイン処理 ---
if not st.session_state.logged_in:
    st.title("Iwattar")
    tab1, tab2 = st.tabs(["ログイン", "アカウント作成"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("メールアドレス")
            password = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.logged_in = True
                    st.session_state.user_id = user.uid
                    st.session_state.is_admin_user = (email.strip() == ADMIN_EMAIL.strip())
                    st.session_state.admin_mode_on = st.session_state.is_admin_user
                    user_doc = db.collection('users').document(user.uid).get()
                    st.session_state.user_name = user_doc.to_dict().get('display_name', user.display_name) if user_doc.exists else user.display_name
                    st.rerun()
                except: st.error("ログイン失敗")
    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("メールアドレス")
            new_pass = st.text_input("パスワード（6文字以上）", type="password")
            display_name = st.text_input("表示名")
            if st.form_submit_button("作成"):
                try:
                    user = auth.create_user(email=new_email, password=new_pass, display_name=display_name)
                    db.collection("users").document(user.uid).set({"display_name": display_name, "avatar_data": None})
                    st.success("成功！ログインしてください")
                except Exception as e: st.error(f"失敗: {e}")
    st.stop()

# --- 5. メイン画面 ---
st.title("Iwattar")

# 管理者スイッチ
if st.session_state.is_admin_user:
    st.session_state.admin_mode_on = st.toggle("🛠️ 管理者モード", value=st.session_state.admin_mode_on)

# サイドバー設定
st.sidebar.title("プロフィール")
user_ref = db.collection('users').document(st.session_state.user_id)
user_data = user_ref.get().to_dict() or {}
current_avatar = user_data.get('avatar_data')

if current_avatar: st.sidebar.image(current_avatar, width=100)
else: st.sidebar.markdown("# 👤")

with st.sidebar.form("profile_edit"):
    new_name = st.text_input("名前", value=user_data.get('display_name', st.session_state.user_name))
    up_avatar = st.file_uploader("アイコン変更", type=["jpg", "png"])
    if st.form_submit_button("更新"):
        up_data = {"display_name": new_name}
        if up_avatar: up_data["avatar_data"] = convert_image_to_base64(up_avatar, (128, 128))
        user_ref.set(up_data, merge=True)
        st.session_state.user_name = new_name
        st.rerun()

if st.sidebar.button("ログアウト"):
    st.session_state.clear()
    st.rerun()

# --- タブ構成 ---
main_tab, zemi_tab, news_tab = st.tabs(["🏠 タイムライン", "🎓 ゼミ一覧", "📢 お知らせ"])

# --- 🏠 タイムラインタブ ---
with main_tab:
    with st.form("post_form", clear_on_submit=True):
        content = st.text_area("いまどうしてる？", max_chars=140)
        post_img = st.file_uploader("画像を載せる", type=["jpg", "png", "jpeg"])
        if st.form_submit_button("ポストする"):
            if content.strip():
                img_base64 = convert_image_to_base64(post_img) if post_img else None
                db.collection("tweets").add({
                    "text": content,
                    "user_name": st.session_state.user_name,
                    "user_id": st.session_state.user_id,
                    "avatar_data": current_avatar,
                    "post_image": img_base64,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                st.rerun()

    st.divider()
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
    for t in tweets:
        d = t.to_dict()
        with st.container(border=True):
            col1, col2 = st.columns([1, 6])
            with col1:
                if d.get('avatar_data'): st.image(d.get('avatar_data'), width=50)
                else: st.write("## 👤")
            with col2:
                st.markdown(f"**{d.get('user_name')}**")
                st.write(d.get('text'))
                if d.get('post_image'): st.image(d.get('post_image'), use_container_width=True)
                
                if st.session_state.admin_mode_on or d.get('user_id') == st.session_state.user_id:
                    if st.button("🗑️ 削除", key=f"del_{t.id}"):
                        db.collection("tweets").document(t.id).delete()
                        st.rerun()

# --- 🎓 ゼミ一覧タブ ---
with zemi_tab:
    st.subheader("ゼミナール紹介")
    # ここは将来的にデータベースから取得するようにできます
    zemis = [
        {"name": "情報工学ゼミ", "prof": "山田教授", "desc": "AIとWeb開発を中心に研究しています。"},
        {"name": "経営戦略ゼミ", "prof": "佐藤教授", "desc": "現代のスタートアップ文化を分析します。"},
        {"name": "デザインゼミ", "prof": "田中教授", "desc": "UI/UXデザインの実践的な習得を目指します。"}
    ]
    for z in zemis:
        with st.expander(f"📘 {z['name']} ({z['prof']})"):
            st.write(z['desc'])
            st.button("詳細を見る", key=z['name'])

# --- 📢 お知らせ一覧タブ ---
with news_tab:
    st.subheader("学校からのお知らせ")
    # 管理者ならお知らせを投稿できる機能を追加可能
    if st.session_state.admin_mode_on:
        with st.expander("➕ お知らせを新規作成（管理者用）"):
            new_news = st.text_input("タイトル")
            if st.button("お知らせを公開"):
                db.collection("news").add({
                    "title": new_news,
                    "date": firestore.SERVER_TIMESTAMP
                })
                st.rerun()

    news_items = db.collection("news").order_by("date", direction=firestore.Query.DESCENDING).stream()
    for n in news_items:
        nd = n.to_dict()
        st.info(f"📅 {nd.get('title')}")
        if st.session_state.admin_mode_on:
            if st.button("❌ 削除", key=f"news_{n.id}"):
                db.collection("news").document(n.id).delete()
                st.rerun()