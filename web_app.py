import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json

# ページの設定
st.set_page_config(page_title="iwitter", page_icon="𝕏")

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
    st.session_state.user_name = ""
    st.session_state.user_id = ""

# --- 3. ログイン・サインアップ画面 ---
if not st.session_state.logged_in:
    st.title("𝕏 iwitter (Firebase Auth)")
    tab1, tab2 = st.tabs(["ログイン", "アカウント作成"])

    with tab1:
        with st.form("login"):
            email = st.text_input("メールアドレス")
            password = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    # 注: 本格的なパスワード認証にはpyrebase等が必要ですが
                    # 現状は簡易的にアカウントの存在確認をログインとします
                    user = auth.get_user_by_email(email)
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_id = user.uid
                    st.session_state.user_name = user.display_name
                    st.rerun()
                except:
                    st.error("ログイン失敗。メールアドレスを確認してください。")

    with tab2:
        with st.form("signup"):
            new_email = st.text_input("登録するメールアドレス")
            new_pass = st.text_input("パスワード（6文字以上）", type="password")
            display_name = st.text_input("表示名（ユーザー名）")
            # アイコン選択
            avatar_choice = st.selectbox("アイコンを選択", ["🐱", "🐶", "🦊", "🐻", "🐼", "🤖", "🚀", "🌈"])
            
            if st.form_submit_button("アカウント作成"):
                try:
                    user = auth.create_user(email=new_email, password=new_pass, display_name=display_name)
                    # Firestoreにアイコン情報を保存
                    db.collection("users").document(user.uid).set({
                        "display_name": display_name,
                        "avatar": avatar_choice
                    })
                    st.success("作成成功！ログインしてください。")
                except Exception as e:
                    st.error(f"作成失敗: {e}")
    st.stop()

# --- 4. ログイン後のメイン画面 ---
st.title("𝕏 クローン (iwitter)")
st.sidebar.write(f"ログイン中: **{st.session_state.user_name}**")
if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.rerun()

# 投稿フォーム
with st.form("tweet_form", clear_on_submit=True):
    content = st.text_area("いまどうしてる？", max_chars=140)
    if st.form_submit_button("ツイートする"):
        if content.strip():
            # アイコン情報を取得
            user_doc = db.collection("users").document(st.session_state.user_id).get()
            avatar = user_doc.to_dict().get("avatar", "👤") if user_doc.exists else "👤"
            
            db.collection("tweets").add({
                "text": content,
                "user_name": st.session_state.user_name,
                "user_id": st.session_state.user_id,
                "avatar": avatar,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            st.rerun()

# タイムライン表示（自動更新）
@st.fragment(run_every=5)
def show_timeline():
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
    for tweet in tweets:
        data = tweet.to_dict()
        with st.container(border=True):
            col1, col2 = st.columns([1, 10])
            with col1:
                st.write(f"## {data.get('avatar', '👤')}")
            with col2:
                st.markdown(f"**{data.get('user_name')}**")
                st.write(data.get('text'))

show_timeline()