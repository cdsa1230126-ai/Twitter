import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json
import base64
from io import BytesIO
from PIL import Image

# --- 設定：管理者のメールアドレス ---
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp" 

# ブラウザのタブ名も Iwattar に変更
st.set_page_config(page_title="Iwattar", page_icon="🐦")

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

# --- 2. セッション状態の初期化 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin_user" not in st.session_state:
    st.session_state.is_admin_user = False
if "admin_mode_on" not in st.session_state:
    st.session_state.admin_mode_on = False 

# --- 3. ログイン・サインアップ画面 ---
if not st.session_state.logged_in:
    st.title("Iwattar") # 𝕏 を削除
    tab1, tab2 = st.tabs(["ログイン", "アカウント作成"])

    with tab1:
        with st.form("login_form"):
            st.markdown("### ログイン")
            email = st.text_input("メールアドレス")
            password = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_id = user.uid
                    
                    st.session_state.is_admin_user = (email.strip() == ADMIN_EMAIL.strip())
                    st.session_state.admin_mode_on = st.session_state.is_admin_user
                    
                    user_doc = db.collection('users').document(user.uid).get()
                    st.session_state.user_name = user_doc.to_dict().get('display_name', user.display_name) if user_doc.exists else user.display_name
                    st.rerun()
                except:
                    st.error("ログイン失敗。メールアドレスを確認してください。")

    with tab2:
        with st.form("signup_form"):
            st.markdown("### 新規登録")
            new_email = st.text_input("メールアドレス")
            new_pass = st.text_input("パスワード（6文字以上）", type="password")
            display_name = st.text_input("表示名（ニックネーム）")
            if st.form_submit_button("アカウントを作成する"):
                try:
                    user = auth.create_user(email=new_email, password=new_pass, display_name=display_name)
                    db.collection("users").document(user.uid).set({
                        "display_name": display_name,
                        "avatar_data": None
                    })
                    st.success("作成成功！ログインしてください。")
                except Exception as e:
                    st.error(f"作成失敗: {e}")
    st.stop()

# --- 4. ログイン後のメイン画面 ---
st.title("Iwattar") # 𝕏 を削除

# 管理者スイッチ
if st.session_state.is_admin_user:
    st.session_state.admin_mode_on = st.toggle("🛠️ 管理者モードを有効にする", value=st.session_state.admin_mode_on)
    if st.session_state.admin_mode_on:
        st.warning("現在：管理者モード（全投稿の削除権限あり）")
    else:
        st.info("現在：一般モード")

# --- サイドバー：プロフィール設定 ---
st.sidebar.title("プロフィール設定")
user_ref = db.collection('users').document(st.session_state.user_id)
user_doc = user_ref.get()
user_data = user_doc.to_dict() if user_doc.exists else {}

current_name = user_data.get('display_name', st.session_state.user_name)
current_avatar_data = user_data.get('avatar_data')

if current_avatar_data:
    st.sidebar.image(current_avatar_data, width=100)
else:
    st.sidebar.markdown("# 👤")

with st.sidebar.form("profile_edit_form"):
    new_name = st.text_input("名前を変更", value=current_name)
    uploaded_file = st.file_uploader("画像をアップロード", type=["jpg", "png", "jpeg"])
    
    if st.form_submit_button("プロフィールを更新"):
        update_data = {"display_name": new_name}
        if uploaded_file is not None:
            img = Image.open(uploaded_file)
            img.thumbnail((128, 128))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            update_data["avatar_data"] = f"data:image/png;base64,{img_str}"
        user_ref.set(update_data, merge=True)
        st.session_state.user_name = new_name
        st.success("更新しました！")
        st.rerun()

if st.sidebar.button("ログアウト"):
    st.session_state.clear()
    st.rerun()

# --- 投稿フォーム ---
st.subheader("いまどうしてる？")
with st.form("tweet_form", clear_on_submit=True):
    content = st.text_area("内容を入力してください", max_chars=140)
    if st.form_submit_button("ポストする"): # ボタンのテキストも少しマイルドに
        if content.strip():
            db.collection("tweets").add({
                "text": content,
                "user_name": st.session_state.user_name,
                "user_id": st.session_state.user_id,
                "avatar_data": current_avatar_data,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            st.rerun()

# --- タイムライン表示 ---
st.divider()
@st.fragment(run_every=5)
def show_timeline():
    try:
        tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(30).stream()
        for tweet in tweets:
            data = tweet.to_dict()
            tweet_id = tweet.id
            is_own_post = data.get('user_id') == st.session_state.user_id
            is_admin_mode = st.session_state.is_admin_user and st.session_state.admin_mode_on
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 6])
                with col1:
                    if data.get('avatar_data'):
                        st.image(data.get('avatar_data'), width=50)
                    else:
                        st.write("## 👤")
                with col2:
                    st.markdown(f"**{data.get('user_name', '不明')}**")
                    st.write(data.get('text', ''))
                    
                    foot1, foot2 = st.columns([2, 1])
                    with foot1:
                        ts = data.get('created_at')
                        if ts: st.caption(f"🕒 {ts.strftime('%H:%M:%S')}")
                    with foot2:
                        if is_admin_mode or is_own_post:
                            btn_label = "🗑️ 削除" if is_own_post else "🗑️ 管理削除"
                            if st.button(btn_label, key=f"del_{tweet_id}"):
                                db.collection("tweets").document(tweet_id).delete()
                                st.rerun()
    except Exception as e:
        st.error(f"読み込みエラー: {e}")

show_timeline()