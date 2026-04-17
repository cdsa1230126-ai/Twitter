import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json
import base64
import pandas as pd
from io import BytesIO
from PIL import Image

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
    st.session_state.current_page = "タイムライン"

# --- 4. ログイン処理 ---
if not st.session_state.logged_in:
    st.title("Iwattar")
    tab1, tab2 = st.tabs(["ログイン", "アカウント作成"])
    with tab1:
        with st.form("login"):
            e = st.text_input("メールアドレス")
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン"):
                try:
                    u = auth.get_user_by_email(e)
                    st.session_state.logged_in = True
                    st.session_state.user_id = u.uid
                    st.session_state.is_admin_user = (e.strip() == ADMIN_EMAIL.strip())
                    st.session_state.admin_mode_on = st.session_state.is_admin_user
                    udoc = db.collection('users').document(u.uid).get()
                    st.session_state.user_name = udoc.to_dict().get('display_name', u.display_name) if udoc.exists else u.display_name
                    st.rerun()
                except: st.error("ログイン失敗。アドレスかパスワードが違います。")
    st.stop()

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
        # 管理者かつ管理者モードONの場合のみアップロード機能を表示
        if st.session_state.get('is_admin_user') and st.session_state.get('admin_mode_on'):
            with st.expander("📂 【管理者限定】スプレッドシート(CSV)から一括登録"):
                st.write("A列:ID, B列:ゼミ名, C列:教員... の順のCSVをアップロードしてください。")
                csv_file = st.file_uploader("ファイルを選択 (.csv または .xlsx)", type=["csv", "xlsx"])
                
                if st.button("一括登録を実行"):
                    if csv_file is not None:
                        try:
                            # 文字コードをいくつか試して読み込む
                            try:
                                df = pd.read_csv(csv_file, encoding='utf-8')
                            except UnicodeDecodeError:
                                # utf-8で失敗したらshift-jisでリトライ
                                csv_file.seek(0) # 読み込み位置を最初に戻す
                                df = pd.read_csv(csv_file, encoding='cp932')
                            
                            # 1行目が「2026年度34年ゼミ一覧」のようなタイトルの場合、
                            # 実際のデータが始まるまで行を飛ばす処理が必要な場合があります。
                            # もしエラーが出る場合は「df = df.iloc[1:]」などで調整します。
                            
                            for _, row in df.iterrows():
                                # row[0]がID、row[1]がゼミ名...
                                # 空白行をスキップする判定を入れるとより安全です
                                if pd.isna(row[0]): continue 
                                
                                doc_id = str(row[0])
                                db.collection("zemis").document(doc_id).set({
                                    "name": str(row[1]), "prof": str(row[2]),
                                    "desc": str(row[3]), "msg": str(row[4]),
                                    "theme": str(row[5]), "content": str(row[6]),
                                    "format": str(row[7]), "career": str(row[8])
                                })
                            st.success(f"正常に {len(df)} 件のデータをインポートしました！")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"読み込み失敗: {ex}")
                    else:
                        st.warning("ファイルが選択されていません。")

        # ゼミ情報の表示（全ユーザー共通）
        z_items = db.collection("zemis").stream()
        for zi in z_items:
            z = zi.to_dict()
            with st.container(border=True):
                st.subheader(f"{zi.id} {z.get('name')}")
                st.markdown(f"**担当教員：{z.get('prof')}**")
                with st.expander("詳細なゼミ活動を見る"):
                    st.write(f"**テーマ:** {z.get('theme')}")
                    st.write(f"**内容:** {z.get('content')}")
                    st.write(f"**進路:** {z.get('career')}")
                
                # 削除ボタンも管理者のみ
                if st.session_state.get('admin_mode_on'):
                    if st.button(f"🗑️ {zi.id} を削除", key=f"del_{zi.id}"):
                        db.collection("zemis").document(zi.id).delete()
                        st.rerun()

    # --- タイムラインページ ---
    elif page == "タイムライン":
        with st.form("post_form", clear_on_submit=True):
            content = st.text_area("内容", max_chars=140)
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
        
        # 投稿表示（最新15件）
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