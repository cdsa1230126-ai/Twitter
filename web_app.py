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

# --- 画像保護 & デザイン調整CSS ---
st.markdown(
    """
    <style>
    /* 画像の保存・ドラッグを制限 */
    img { 
        -webkit-user-select: none; 
        -moz-user-select: none; 
        -ms-user-select: none; 
        user-select: none; 
        pointer-events: none; 
    }
    /* サイドメニューボタンの横幅を揃える */
    .stButton > button { 
        width: 100%; 
        border-radius: 8px; 
        height: 3.5em; 
        margin-bottom: 8px;
        font-weight: bold;
    }
    /* タイムラインのコンテナ調整 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(255, 255, 255, 0.05);
    }
    </style>
    <script>
    document.addEventListener('contextmenu', event => event.preventDefault());
    </script>
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

# --- 2. 便利関数群 ---
def convert_image_to_base64(uploaded_file, size=(400, 300)):
    """画像をBase64形式に変換（リサイズ付き）"""
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
    st.session_state.current_page = "タイムライン"
if "admin_mode_on" not in st.session_state:
    st.session_state.admin_mode_on = False

# --- 4. ログイン・サインアップ画面 ---
if not st.session_state.logged_in:
    st.title("Iwattar")
    tab_login, tab_signup = st.tabs(["ログイン", "アカウント作成"])
    
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("メールアドレス")
            password = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.logged_in = True
                    st.session_state.user_id = user.uid
                    st.session_state.user_email = email
                    # 管理者判定
                    st.session_state.is_admin_user = (email.strip() == ADMIN_EMAIL.strip())
                    st.session_state.admin_mode_on = st.session_state.is_admin_user
                    
                    user_doc = db.collection('users').document(user.uid).get()
                    st.session_state.user_name = user_doc.to_dict().get('display_name', user.display_name) if user_doc.exists else user.display_name
                    st.rerun()
                except:
                    st.error("ログインに失敗しました。")

    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("学校用メールアドレス")
            new_pass = st.text_input("パスワード（6文字以上）", type="password")
            new_name = st.text_input("表示名（ニックネーム）")
            if st.form_submit_button("新規アカウント作成"):
                try:
                    user = auth.create_user(email=new_email, password=new_pass, display_name=new_name)
                    db.collection("users").document(user.uid).set({
                        "display_name": new_name,
                        "avatar_data": None
                    })
                    st.success("作成完了！ログインしてください。")
                except Exception as e:
                    st.error(f"作成エラー: {e}")
    st.stop()

# --- 5. メインレイアウト（3カラム） ---
side_col, main_col, nav_col = st.columns([2, 5, 2])

# --- 左カラム：プロフィール ---
with side_col:
    st.title("Iwattar")
    user_ref = db.collection('users').document(st.session_state.user_id)
    user_data = user_ref.get().to_dict() or {}
    current_avatar = user_data.get('avatar_data')

    if current_avatar:
        st.image(current_avatar, width=100)
    else:
        st.markdown("### 👤")
    
    st.write(f"**{st.session_state.user_name}**")
    
    with st.expander("プロフィール設定"):
        edit_name = st.text_input("名前変更", value=st.session_state.user_name)
        up_avatar = st.file_uploader("アイコン変更", type=["jpg", "png"])
        if st.button("変更を保存"):
            up_data = {"display_name": edit_name}
            if up_avatar:
                up_data["avatar_data"] = convert_image_to_base64(up_avatar, (128, 128))
            user_ref.set(up_data, merge=True)
            st.session_state.user_name = edit_name
            st.success("更新しました。")
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
    # 管理者専用：スイッチ
    if st.session_state.is_admin_user:
        st.session_state.admin_mode_on = st.toggle("🛠️ 管理者モード", value=st.session_state.admin_mode_on)
        if st.session_state.admin_mode_on:
            st.caption("管理者として編集・削除が可能")

# --- 中央カラム：メインコンテンツ ---
with main_col:
    page = st.session_state.current_page
    st.header(page)

    # --- 🏠 タイムライン ---
    if page == "タイムライン":
        with st.form("post_form", clear_on_submit=True):
            content = st.text_area("いまどうしてる？", max_chars=140, placeholder="ゼミの進捗や就活情報など...")
            post_img = st.file_uploader("画像を添付（閲覧専用）", type=["jpg", "png", "jpeg"])
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
                c1, c2 = st.columns([1, 6])
                with c1:
                    if d.get('avatar_data'): st.image(d.get('avatar_data'), width=45)
                    else: st.write("👤")
                with c2:
                    st.markdown(f"**{d.get('user_name')}**")
                    st.write(d.get('text'))
                    if d.get('post_image'):
                        st.image(d.get('post_image'), use_container_width=True)
                    
                    # 削除権限：自分の投稿 or 管理者モードON
                    if st.session_state.admin_mode_on or d.get('user_id') == st.session_state.user_id:
                        if st.button("🗑️ 削除", key=f"del_{t.id}"):
                            db.collection("tweets").document(t.id).delete()
                            st.rerun()

    # --- 🎓 ゼミ一覧（詳細編集機能付き） ---
    elif page == "ゼミ一覧":
        if st.session_state.admin_mode_on:
            with st.expander("➕ 新しいゼミ情報を追加"):
                with st.form("add_zemi_form"):
                    z_id = st.text_input("ゼミID (例: C-271)")
                    z_name = st.text_input("ゼミ名")
                    z_prof = st.text_input("担当教員")
                    z_theme = st.text_input("ゼミテーマ")
                    z_desc = st.text_area("ゼミ内容")
                    z_msg = st.text_area("学生へのメッセージ・望む人物像")
                    z_career = st.text_area("進路イメージ")
                    if st.form_submit_button("データベースに登録"):
                        if z_id and z_name:
                            db.collection("zemis").document(z_id).set({
                                "name": z_name, "prof": z_prof, "theme": z_theme,
                                "desc": z_desc, "msg": z_msg, "career": z_career
                            })
                            st.success(f"{z_name}を登録しました。")
                            st.rerun()

        st.info("2026年度 3・4年ゼミ一覧。クリックで詳細を表示します。")
        zemi_docs = db.collection("zemis").stream()
        
        for z_doc in zemi_docs:
            z = z_doc.to_dict()
            zid = z_doc.id
            with st.container(border=True):
                st.subheader(f"{zid} {z.get('name')}")
                st.markdown(f"**担当：{z.get('prof')}**")
                st.caption(f"📌 テーマ：{z.get('theme')}")
                
                with st.expander("詳細なゼミ情報・メッセージを見る"):
                    st.markdown("**【ゼミ内容】**")
                    st.write(z.get('desc'))
                    st.markdown("**【学生へのメッセージ・望む人物像】**")
                    st.write(z.get('msg'))
                    st.markdown("**【進路イメージ】**")
                    st.write(z.get('career'))

                if st.session_state.admin_mode_on:
                    if st.button(f"🗑️ {zid} を削除", key=f"del_z_{zid}"):
                        db.collection("zemis").document(zid).delete()
                        st.rerun()

    # --- 📢 お知らせ ---
    elif page == "お知らせ":
        if st.session_state.admin_mode_on:
            with st.form("news_add_form"):
                n_title = st.text_input("お知らせのタイトル")
                if st.form_submit_button("配信する"):
                    if n_title:
                        db.collection("news").add({
                            "title": n_title,
                            "date": firestore.SERVER_TIMESTAMP
                        })
                        st.rerun()
        
        news_items = db.collection("news").order_by("date", direction=firestore.Query.DESCENDING).stream()
        for n in news_items:
            nd = n.to_dict()
            st.info(f"📅 {nd.get('title')}")
            if st.session_state.admin_mode_on:
                if st.button("❌ 削除", key=f"n_del_{n.id}"):
                    db.collection("news").document(n.id).delete()
                    st.rerun()