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

# --- 画像保護用CSS ---
st.markdown(
    """
    <style>
    img { -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; user-select: none; pointer-events: none; }
    /* 右側ナビゲーションボタンのスタイル */
    .stButton > button { width: 100%; border-radius: 5px; height: 3em; margin-bottom: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

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

# --- 2. 関数群 ---
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
if "current_page" not in st.session_state:
    st.session_state.current_page = "タイムライン" # 初期表示ページ

# --- 4. ログイン・サインアップ ---
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
                    st.success("作成成功！")
                except Exception as e: st.error(f"失敗: {e}")
    st.stop()

# --- 5. メイン画面構成 ---
# 画面を「左プロフィール・中コンテンツ・右メニュー」の3カラムに分割
side_col, main_col, nav_col = st.columns([2, 5, 2])

# --- 左カラム：プロフィール ---
with side_col:
    st.title("Iwattar")
    user_ref = db.collection('users').document(st.session_state.user_id)
    user_data = user_ref.get().to_dict() or {}
    current_avatar = user_data.get('avatar_data')

    if current_avatar: st.image(current_avatar, width=100)
    else: st.markdown("# 👤")
    
    st.write(f"**{st.session_state.user_name}**")
    
    with st.expander("設定"):
        new_name = st.text_input("名前変更", value=st.session_state.user_name)
        up_avatar = st.file_uploader("アイコン変更", type=["jpg", "png"])
        if st.button("保存"):
            up_data = {"display_name": new_name}
            if up_avatar: up_data["avatar_data"] = convert_image_to_base64(up_avatar, (128, 128))
            user_ref.set(up_data, merge=True)
            st.session_state.user_name = new_name
            st.rerun()
    
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# --- 右カラム：ナビゲーションメニュー ---
with nav_col:
    st.markdown("### Menu")
    if st.button("🏠 タイムライン"):
        st.session_state.current_page = "タイムライン"
        st.rerun()
    if st.button("🎓 ゼミ一覧"):
        st.session_state.current_page = "ゼミ一覧"
        st.rerun()
    if st.button("📢 お知らせ"):
        st.session_state.current_page = "お知らせ"
        st.rerun()
    
    st.divider()
    if st.session_state.is_admin_user:
        st.session_state.admin_mode_on = st.toggle("🛠️ 管理者モード", value=st.session_state.get('admin_mode_on', False))

# --- 中央カラム：メインコンテンツ（ここが切り替わる） ---
with main_col:
    page = st.session_state.current_page
    st.header(page)

    if page == "タイムライン":
        with st.form("post_form", clear_on_submit=True):
            content = st.text_area("いまどうしてる？", max_chars=140)
            post_img = st.file_uploader("画像を載せる", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("ポストする"):
                if content.strip():
                    img_base64 = convert_image_to_base64(post_img) if post_img else None
                    db.collection("tweets").add({
                        "text": content, "user_name": st.session_state.user_name,
                        "user_id": st.session_state.user_id, "avatar_data": current_avatar,
                        "post_image": img_base64, "created_at": firestore.SERVER_TIMESTAMP
                    })
                    st.rerun()

        st.divider()
        tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(15).stream()
        for t in tweets:
            d = t.to_dict()
            with st.container(border=True):
                c1, c2 = st.columns([1, 6])
                with c1:
                    if d.get('avatar_data'): st.image(d.get('avatar_data'), width=45)
                    else: st.write("👤")
                with c2:
                    st.markdown(f"**{d.get('user_name')}**")
                    st.write(d.get('text'))
                    if d.get('post_image'): st.image(d.get('post_image'), use_container_width=True)
                    if st.session_state.get('admin_mode_on') or d.get('user_id') == st.session_state.user_id:
                        if st.button("🗑️", key=f"del_{t.id}"):
                            db.collection("tweets").document(t.id).delete()
                            st.rerun()

    elif page == "ゼミ一覧":
        st.info("興味のあるゼミを探してみましょう。")
        zemis = [
            {"name": "情報工学ゼミ", "prof": "山田教授", "desc": "AI、Webアプリ、ブロックチェーン技術を実践的に学びます。"},
            {"name": "経営デザインゼミ", "prof": "佐藤教授", "desc": "新サービスの企画やマーケティング戦略を研究します。"},
            {"name": "ビジュアル表現ゼミ", "prof": "田中教授", "desc": "広告デザインやUX/UIなど、視覚伝達の最適化を追求します。"}
        ]
        for z in zemis:
            with st.container(border=True):
                st.subheader(f"📘 {z['name']}")
                st.caption(f"担当：{z['prof']}")
                st.write(z['desc'])
                st.button("ゼミの掲示板を見る", key=f"btn_{z['name']}")

    elif page == "お知らせ":
        if st.session_state.get('admin_mode_on'):
            with st.form("news_add"):
                new_title = st.text_input("重要なお知らせを入力")
                if st.form_submit_button("配信"):
                    db.collection("news").add({"title": new_title, "date": firestore.SERVER_TIMESTAMP})
                    st.rerun()
        
        news_items = db.collection("news").order_by("date", direction=firestore.Query.DESCENDING).stream()
        for n in news_items:
            nd = n.to_dict()
            st.info(f"📅 {nd.get('title')}")
            if st.session_state.get('admin_mode_on'):
                if st.button("❌ 削除", key=f"n_del_{n.id}"):
                    db.collection("news").document(n.id).delete()
                    st.rerun()