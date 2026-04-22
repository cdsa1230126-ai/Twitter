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

# --- 設定：管理者のメールアドレス ---
ADMIN_EMAIL = "cdsa1230126@gn.iwasaki.ac.jp" 

st.set_page_config(page_title="Iwattar", page_icon="🐦", layout="wide")

# --- 画像保護 & デザインCSS ---
st.markdown(
    """
    <style>
    img { -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; user-select: none; pointer-events: none; }
    .stButton > button { width: 100%; border-radius: 8px; height: 3.5em; margin-bottom: 8px; font-weight: bold; }
    </style>
    <script>document.addEventListener('contextmenu', event => event.preventDefault());</script>
    """,
    unsafe_allow_html=True
)

# --- 1. Firebase初期化 (秘密鍵洗浄ロジック) ---
if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        parts = fb_sec["raw_data"].split(",")
        
        # 秘密鍵の整形
        raw_key = fb_sec["private_key"].replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
        pure_key = re.sub(r"[^A-Za-z0-9+/=]", "", raw_key)
        formatted_content = "\n".join(textwrap.wrap(pure_key, 64))
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_content}\n-----END PRIVATE KEY-----\n"
        
        info_dict = {
            "type": "service_account",
            "project_id": parts[0],
            "private_key_id": parts[1],
            "private_key": fixed_key,
            "client_email": parts[2],
            "client_id": parts[3],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{parts[2]}",
            "universe_domain": "googleapis.com"
        }
        
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
    st.session_state.current_page = "タイムライン"
if "saved_email" not in st.session_state:
    st.session_state.saved_email = ""

# --- 4. ログイン・アカウント作成処理 ---
if not st.session_state.logged_in:
    st.title("Iwattar")
    tab1, tab2 = st.tabs(["ログイン", "アカウント作成"])
    
    with tab1:
        with st.form("login"):
            # 保存されているメアドがあれば初期値に入れる
            e = st.text_input("メールアドレス", value=st.session_state.saved_email)
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    u = auth.get_user_by_email(e)
                    st.session_state.logged_in = True
                    st.session_state.user_id = u.uid
                    st.session_state.saved_email = e  # 次回のためにメアド保存
                    st.session_state.is_admin_user = (e.strip() == ADMIN_EMAIL.strip())
                    st.session_state.admin_mode_on = st.session_state.is_admin_user
                    
                    udoc = db.collection('users').document(u.uid).get()
                    if udoc.exists:
                        st.session_state.user_name = udoc.to_dict().get('display_name', e.split('@')[0])
                    else:
                        st.session_state.user_name = u.display_name if u.display_name else e.split('@')[0]
                    st.rerun()
                except:
                    st.error("ログイン失敗。アドレスが登録されていないか、エラーが発生しました。")

    with tab2:
        with st.form("signup"):
            new_email = st.text_input("メールアドレス (アカウント作成)")
            new_password = st.text_input("パスワード (6文字以上)", type="password")
            new_name = st.text_input("表示名")
            
            if st.form_submit_button("新規登録"):
                if len(new_password) < 6:
                    st.error("パスワードは6文字以上にしてください。")
                elif not new_email or not new_name:
                    st.error("すべての項目を入力してください。")
                else:
                    try:
                        user = auth.create_user(email=new_email, password=new_password, display_name=new_name)
                        db.collection('users').document(user.uid).set({
                            "display_name": new_name, "email": new_email, "avatar_data": None
                        })
                        st.success("作成成功！ログインタブからログインしてください。")
                        st.session_state.saved_email = new_email
                    except Exception as ex:
                        st.error(f"作成失敗: {ex}")
    st.stop()

# --- 4.5 ログイン情報の安全性チェック (AttributeError防止) ---
if "user_name" not in st.session_state or "user_id" not in st.session_state:
    st.session_state.logged_in = False
    st.rerun()

# --- 5. メインレイアウト ---
side_col, main_col, nav_col = st.columns([2, 5, 2])

# 【左】プロフィール
with side_col:
    st.title("Iwattar")
    user_ref = db.collection('users').document(st.session_state.user_id)
    user_data = user_ref.get().to_dict() or {}
    avatar = user_data.get('avatar_data')
    if avatar: st.image(avatar, width=100)
    else: st.markdown("### 👤")
    st.write(f"**{st.session_state.user_name}**")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# 【右】メニュー
with nav_col:
    st.markdown("### Menu")
    if st.button("🏠 タイムライン"): st.session_state.current_page = "タイムライン"; st.rerun()
    if st.button("🎓 ゼミ一覧"): st.session_state.current_page = "ゼミ一覧"; st.rerun()
    if st.button("📢 お知らせ"): st.session_state.current_page = "お知らせ"; st.rerun()
    st.divider()
    if st.session_state.is_admin_user:
        st.session_state.admin_mode_on = st.toggle("🛠️ 管理者モード", value=st.session_state.admin_mode_on)

# 【中央】メインコンテンツ
with main_col:
    page = st.session_state.current_page
    st.header(page)

    # --- ゼミ一覧ページ ---
    if page == "ゼミ一覧":
        if st.session_state.get('is_admin_user') and st.session_state.get('admin_mode_on'):
            with st.expander("📂 【管理者限定】CSVから一括登録"):
                csv_file = st.file_uploader("CSVファイルを選択", type=["csv", "xlsx"])
                if st.button("一括登録を実行"):
                    if csv_file is not None:
                        try:
                            try:
                                df_raw = pd.read_csv(csv_file, encoding='utf-8', header=None)
                            except:
                                csv_file.seek(0)
                                df_raw = pd.read_csv(csv_file, encoding='cp932', header=None)
                            
                            header_idx = None
                            for i in range(len(df_raw)):
                                if "ID" in str(df_raw.iloc[i, 0]):
                                    header_idx = i
                                    break
                            
                            if header_idx is not None:
                                df = df_raw.iloc[header_idx+1:].copy()
                                count = 0
                                for _, row in df.iterrows():
                                    val_id = str(row[0]).strip()
                                    if val_id and val_id != "nan":
                                        db.collection("zemis").document(val_id).set({
                                            "name": str(row[1]), "prof": str(row[2]), "desc": str(row[3]),
                                            "msg": str(row[4]), "theme": str(row[5]), "content": str(row[6]),
                                            "format": str(row[7]), "career": str(row[8])
                                        })
                                        count += 1
                                st.success(f"{count}件インポート完了")
                                st.rerun()
                        except Exception as ex: st.error(f"失敗: {ex}")

        z_items = db.collection("zemis").stream()
        for zi in z_items:
            z = zi.to_dict()
            with st.container(border=True):
                st.subheader(f"{zi.id} {z.get('name')}")
                st.write(f"**教員:** {z.get('prof')}")
                with st.expander("詳細"):
                    st.write(f"**テーマ:** {z.get('theme')}")
                    st.write(f"**内容:** {z.get('content')}")
                if st.session_state.get('admin_mode_on'):
                    if st.button(f"🗑️ {zi.id}", key=f"del_{zi.id}"):
                        db.collection("zemis").document(zi.id).delete()
                        st.rerun()

    # --- タイムラインページ ---
    elif page == "タイムライン":
        with st.form("post_form", clear_on_submit=True):
            content = st.text_area("いまどうしてる？", max_chars=140)
            post_img = st.file_uploader("画像", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("ポスト"):
                if content.strip():
                    img_base64 = convert_image_to_base64(post_img) if post_img else None
                    db.collection("tweets").add({
                        "text": content, "user_name": st.session_state.user_name,
                        "user_id": st.session_state.user_id, "avatar_data": avatar,
                        "post_image": img_base64, "created_at": firestore.SERVER_TIMESTAMP
                    })
                    st.rerun()
        
        tweets = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(15).stream()
        for t in tweets:
            d = t.to_dict()
            with st.container(border=True):
                c1, c2 = st.columns([1, 6])
                with c1:
                    if d.get('avatar_data'): st.image(d.get('avatar_data'), width=45)
                    else: st.write("👤")
                with c2:
                    st.write(f"**{d.get('user_name')}**")
                    st.write(d.get('text'))
                    if d.get('post_image'): st.image(d.get('post_image'), use_container_width=True)
                    if st.session_state.get('admin_mode_on') or d.get('user_id') == st.session_state.user_id:
                        if st.button("🗑️", key=f"t_del_{t.id}"):
                            db.collection("tweets").document(t.id).delete()
                            st.rerun()

    # --- お知らせページ ---
    elif page == "お知らせ":
        if st.session_state.get('admin_mode_on'):
            with st.form("news_form"):
                n_t = st.text_input("タイトル")
                if st.form_submit_button("配信"):
                    db.collection("news").add({"title": n_t, "date": firestore.SERVER_TIMESTAMP})
                    st.rerun()
        news = db.collection("news").order_by("date", direction=firestore.Query.DESCENDING).stream()
        for n in news:
            st.info(f"📅 {n.to_dict().get('title')}")
            if st.session_state.get('admin_mode_on'):
                if st.button("削除", key=f"n_del_{n.id}"):
                    db.collection("news").document(n.id).delete()
                    st.rerun()