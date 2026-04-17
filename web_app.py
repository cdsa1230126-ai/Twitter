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
        with st.form("login_form"):
            st.markdown("### ログイン")
            email = st.text_input("メールアドレス", key="login_email")
            password = st.text_input("パスワード", type="password", key="login_pass")
            if st.form_submit_button("ログイン"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_id = user.uid
                    st.session_state.user_name = user.display_name
                    st.rerun()
                except:
                    st.error("ログイン失敗。メールアドレスを確認してください。")

    with tab2:
        with st.form("signup_form"):
            st.markdown("### 新規登録")
            new_email = st.text_input("メールアドレス（IDになります）", key="signup_email")
            new_pass = st.text_input("パスワード（6文字以上）", type="password", key="signup_pass", help="Googleの自動生成も使えます")
            
            st.divider()
            
            display_name = st.text_input("表示名（ニックネーム）")
            avatar_choice = st.selectbox("アイコンを選択", ["🐱", "🐶", "🦊", "🐻", "🐼", "🤖", "🚀", "🌈", "🐥", "👻"])
            
            if st.form_submit_button("アカウントを作成する"):
                if len(new_pass) < 6:
                    st.error("パスワードは6文字以上にしてください。")
                elif not display_name:
                    st.error("表示名を入力してください。")
                else:
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
st.title("𝕏 クローン (iwitter)")

# サイドバー設定
st.sidebar.title("プロフィール")
try:
    user_doc = db.collection('users').document(st.session_state.user_id).get()
    avatar = user_doc.to_dict().get('avatar', '👤') if user_doc.exists else '👤'
except:
    avatar = '👤'

st.sidebar.markdown(f"## {avatar}")
st.sidebar.write(f"ユーザー名: **{st.session_state.user_name}**")
if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.rerun()

# 投稿フォーム
st.subheader("いまどうしてる？")
with st.form("tweet_form", clear_on_submit=True):
    content = st.text_area("内容を入力してください", max_chars=140)
    if st.form_submit_button("ツイートする"):
        if content.strip():
            user_doc = db.collection("users").document(st.session_state.user_id).get()
            current_avatar = user_doc.to_dict().get("avatar", "👤") if user_doc.exists else "👤"
            
            db.collection("tweets").add({
                "text": content,
                "user_name": st.session_state.user_name,
                "user_id": st.session_state.user_id,
                "avatar": current_avatar,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            st.rerun()

# タイムライン表示（5秒ごとに自動更新）
st.divider()
st.subheader("最新の投稿")

@st.fragment(run_every=5)
def show_timeline():
    try:
        # 最新20件を取得
        tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
        
        for tweet in tweets:
            data = tweet.to_dict()
            tweet_id = tweet.id  # 削除に使うドキュメントID
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 10])
                with col1:
                    st.write(f"## {data.get('avatar', '👤')}")
                with col2:
                    st.markdown(f"**{data.get('user_name', '不明')}**")
                    st.write(data.get('text', ''))
                    
                    # 下部のレイアウト（時間と削除ボタン）
                    foot1, foot2 = st.columns([2, 1])
                    with foot1:
                        ts = data.get('created_at')
                        if ts:
                            st.caption(f"🕒 {ts.strftime('%H:%M:%S')}")
                    
                    with foot2:
                        # 投稿主IDが、現在ログイン中のIDと一致する場合のみ削除ボタンを表示
                        if data.get('user_id') == st.session_state.user_id:
                            # ボタンを右寄せにするために小細工なしでシンプルに設置
                            if st.button("🗑️ 削除", key=f"del_{tweet_id}"):
                                db.collection("tweets").document(tweet_id).delete()
                                st.rerun()
            
    except Exception as e:
        st.error(f"読み込みエラー: {e}")

show_timeline()