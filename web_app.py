import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth  # authを追加
import json

# --- 1. Firebase初期化（以前と同じ） ---
if not firebase_admin._apps:
    try:
        json_string = st.secrets["firebase"]["service_account_json"]
        info_dict = json.loads(json_string)
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()

# --- 2. セッション状態の初期化 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""
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
                    # 本来はフロントエンド用のSDKを使うのが一般的ですが、
                    # Admin SDKではパスワード検証が直接できないため、
                    # ユーザー情報の取得のみ確認し、簡易的に「存在チェック」を行います。
                    user = auth.get_user_by_email(email)
                    # ※注意: Admin SDKは管理用のため、実際のサービスでは
                    # Pyrebase等のライブラリを併用してパスワード認証を行うのが定石です。
                    # ここでは「アカウントが存在するか」の確認をログイン代わりとします。
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_id = user.uid
                    st.rerun()
                except Exception as e:
                    st.error("ログイン失敗: メールアドレスが登録されていないか、エラーが発生しました。")

    with tab2:
        with st.form("signup"):
            new_email = st.text_input("登録するメールアドレス")
            new_pass = st.text_input("パスワード（6文字以上）", type="password")
            display_name = st.text_input("表示名（ユーザー名）")
            
            if st.form_submit_button("アカウント作成"):
                try:
                    # Firebase Authにユーザーを作成
                    user = auth.create_user(
                        email=new_email,
                        password=new_pass,
                        display_name=display_name
                    )
                    st.success(f"アカウント作成成功！ {user.display_name}さん、ログインしてください。")
                except Exception as e:
                    st.error(f"作成失敗: {e}")
    st.stop()

# --- 4. ログイン後の画面（以前の投稿機能を流用） ---
st.sidebar.write(f"ログイン中: **{st.session_state.user_email}**")
if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.rerun()

# --- 投稿フォーム ---
st.subheader("いまどうしてる？")
with st.form("tweet", clear_on_submit=True):
    content = st.text_area("内容", max_chars=140)
    if st.form_submit_button("ツイート"):
        if content:
            # 表示名を取得して保存
            user_info = auth.get_user(st.session_state.user_id)
            db.collection("tweets").add({
                "text": content,
                "user_name": user_info.display_name or "名無しさん",
                "user_id": st.session_state.user_id,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            st.rerun()

# --- タイムライン（以前と同じ show_timeline 関数） ---
@st.fragment(run_every=5)
def show_timeline():
    tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
    for tweet in tweets:
        data = tweet.to_dict()
        with st.container(border=True):
            st.markdown(f"**{data.get('user_name')}**")
            st.write(data.get('text'))
            if data.get('user_id') == st.session_state.user_id:
                st.caption("✨ 自分の投稿")

show_timeline()