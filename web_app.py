import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq
from datetime import datetime
import pytz

# ページ設定
st.set_page_config(page_title="iwitter - Firebase AI Edition", layout="wide")

# --- 1. Firebase初期化 (超強力・自動掃除版) ---
if not firebase_admin._apps:
    try:
        if "firebase" not in st.secrets:
            st.error("Secretsに [firebase] セクションが見つかりません。")
            st.stop()
            
        # Secretsから辞書をコピー
        fb_creds = dict(st.secrets["firebase"])
        
        if "private_key" in fb_creds:
            # 1. まず文字列の前後にある目に見えないスペースや改行を完全に除去
            pk = fb_creds["private_key"].strip()
            # 2. \n という文字を実際の改行に変換
            pk = pk.replace("\\n", "\n")
            # 3. もし引用符などが紛れ込んでいたら除去
            pk = pk.strip('"').strip("'")
            
            fb_creds["private_key"] = pk
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebaseの初期化に失敗しました。\nエラー詳細: {e}")
        # 詳細なデバッグ情報を表示（解決したら消します）
        st.write("デバッグ情報: 鍵の長さは", len(fb_creds.get("private_key", "")))
        st.stop()

db = firestore.client()

# --- 2. Groq AI初期化 ---
try:
    if "GROQ_API_KEY" in st.secrets:
        ai_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    else:
        st.warning("GROQ_API_KEYが設定されていません。AI機能は無効です。")
        ai_client = None
except Exception as e:
    st.error(f"Groqの初期化エラー: {e}")
    ai_client = None

tokyo_tz = pytz.timezone('Asia/Tokyo')

# --- 3. サイドバー（AIアシスタント） ---
with st.sidebar:
    st.header("🤖 AI Assistant")
    st.write("Twitterの投稿内容の相談など、AIに聞いてみよう！")
    ai_query = st.text_input("AIへの質問を入力", key="ai_input")
    
    if st.button("AIに聞く"):
        if ai_client and ai_query:
            with st.spinner("AIが考え中..."):
                try:
                    chat_completion = ai_client.chat.completions.create(
                        messages=[{"role": "user", "content": ai_query}],
                        model="llama-3.3-70b-versatile",
                    )
                    st.info(chat_completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"AIエラー: {e}")
        elif not ai_client:
            st.error("APIキーが正しく設定されていないため、AIを使えません。")

# --- 4. メイン画面（SNS機能） ---
st.title("𝕏 iwitter (Firebase版)")

# 投稿フォーム
with st.container():
    st.subheader("いまどうしてる？")
    name = st.text_input("名前", value="ゲストユーザー", max_chars=20)
    content = st.text_area("ツイート内容を入力してください", max_chars=140)
    
    if st.button("投稿する", use_container_width=True):
        if content:
            try:
                # Firestoreの 'posts' コレクションに保存
                doc_ref = db.collection("posts").document()
                doc_ref.set({
                    "user": name,
                    "text": content,
                    "time": datetime.now(tokyo_tz)
                })
                st.success("投稿が完了しました！")
                st.rerun()
            except Exception as e:
                st.error(f"送信失敗: {e}")
        else:
            st.warning("内容を入力してください。")

st.divider()

# --- 5. タイムライン表示 ---
st.subheader("最新のタイムライン")

try:
    # データを最新順に20件取得
    posts_ref = db.collection("posts").order_by("time", direction=firestore.Query.DESCENDING).limit(20)
    posts = posts_ref.stream()

    found_posts = False
    for post in posts:
        found_posts = True
        p = post.to_dict()
        
        # 時刻の処理
        time_val = p.get('time')
        if time_val:
            # Firestoreから取得した時刻を日本時間に変換して表示
            display_time = time_val.astimezone(tokyo_tz).strftime('%Y/%m/%d %H:%M')
        else:
            display_time = "時刻不明"
            
        # ツイート風の見た目
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1DA1F2; margin-bottom: 15px;">
                <b style="color: #1DA1F2; font-size: 1.1em;">@{p.get('user', '名無し')}</b> 
                <span style="color: #657786; font-size: 0.8em; margin-left: 10px;">{display_time}</span><br>
                <p style="margin-top: 10px; color: #14171A; font-size: 1.0em; line-height: 1.5;">{p.get('text', '')}</p>
            </div>
        """, unsafe_allow_html=True)

    if not found_posts:
        st.info("まだ投稿がありません。最初のツイートをしてみましょう！")

except Exception as e:
    st.error(f"データ取得エラー: {e}")
    st.info("FirebaseのFirestoreで 'posts' コレクションが作成されているか確認してください。")