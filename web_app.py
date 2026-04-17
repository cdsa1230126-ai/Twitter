import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json

# --- 設定：ここを自分のメールアドレスに変えてください ---
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp" 

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
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False  # 事前に作っておく

# --- 3. ログイン・サインアップ画面 ---
if not st.session_state.logged_in:
    st.title("𝕏 iwitter")
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
                    
                    # 管理者判定
                    st.session_state.is_admin = (email == ADMIN_EMAIL)
                        
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
            avatar_choice = st.selectbox("アイコンを選択", ["🐱", "🐶", "🦊", "🐻", "🐼", "🤖", "🚀", "🌈", "🐥", "👻"])
            
            if st.form_submit_button("アカウントを作成する"):
                try:
                    user = auth.create_user(email=new_email, password=new_pass, display_name=display_name)
                    db.collection("users").document(user.uid).set({
                        "display_name": display_name,
                        "avatar": avatar_choice
                    })
                    st.success("作成成功！ログインしてください。")
                except Exception as e:
                    st.error(f"作成失敗: {e}")
    st.stop()

# --- 4. ログイン後のメイン画面 ---
st.title("𝕏 iwitter")

# 安全に管理者判定を行う（エラー回避用）
if st.session_state.get("is_admin", False):
    st.warning("🛠️ 管理者モードでログイン中：すべての投稿を削除できます。")

# --- サイドバー：プロフィール設定 ---
st.sidebar.title("プロフィール設定")
user_ref = db.collection('users').document(st.session_state.user_id)
user_doc = user_ref.get()
user_data = user_doc.to_dict() if user_doc.exists else {"display_name": st.session_state.user_name, "avatar": "👤"}
current_avatar = user_data.get('avatar', '👤')
current_name = user_data.get('display_name', st.session_state.user_name)

st.sidebar.markdown(f"# {current_avatar}")
with st.sidebar.form("profile_edit_form"):
    new_name = st.text_input("名前を変更", value=current_name)
    avatar_list = ["🐱", "🐶", "🦊", "🐻", "🐼", "🤖", "🚀", "🌈", "🐥", "👻", "🐯", "🦁", "🐧"]
    try: current_index = avatar_list.index(current_avatar)
    except: current_index = 0
    new_avatar = st.selectbox("アイコンを変更", avatar_list, index=current_index)
    if st.form_submit_button("プロフィールを更新"):
        user_ref.set({"display_name": new_name, "avatar": new_avatar}, merge=True)
        st.session_state.user_name = new_name
        st.rerun()

if st.sidebar.button("ログアウト"):
    st.session_state.clear() # セッションを完全にクリアしてログアウト
    st.rerun()

# --- 投稿フォーム ---
st.subheader("いまどうしてる？")
with st.form("tweet_form", clear_on_submit=True):
    content = st.text_area("内容を入力してください", max_chars=140)
    if st.form_submit_button("ツイートする"):
        if content.strip():
            db.collection("tweets").add({
                "text": content,
                "user_name": st.session_state.user_name,
                "user_id": st.session_state.user_id,
                "avatar": current_avatar, 
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
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 10])
                with col1:
                    st.write(f"## {data.get('avatar', '👤')}")
                with col2:
                    st.markdown(f"**{data.get('user_name', '不明')}**")
                    st.write(data.get('text', ''))
                    
                    foot1, foot2 = st.columns([2, 1])
                    with foot1:
                        ts = data.get('created_at')
                        if ts: st.caption(f"🕒 {ts.strftime('%H:%M:%S')}")
                    
                    with foot2:
                        # 管理者か自分の投稿なら削除ボタンを表示
                        if st.session_state.get("is_admin", False) or is_own_post:
                            btn_label = "🗑️ 削除" if is_own_post else "🗑️ 管理削除"
                            if st.button(btn_label, key=f"del_{tweet_id}"):
                                db.collection("tweets").document(tweet_id).delete()
                                st.rerun()
    except Exception as e:
        st.error(f"読み込みエラー: {e}")

show_timeline()