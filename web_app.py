import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --- 1. Firebase初期化設定 ---
if not firebase_admin._apps:
    try:
        # SecretsからJSON文字列を丸ごと取得
        json_string = st.secrets["firebase"]["service_account_json"]
        
        # 辞書に変換
        info_dict = json.loads(json_string)
        
        # 初期化
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        # 接続確認ができたら、最初は成功メッセージを出しておくと安心です
        # st.success("Firebase接続成功！") 
        
    except Exception as e:
        st.error(f"Firebase初期化失敗: {e}")
        st.stop()

# Firestoreクライアントの作成
db = firestore.client()

# --- 2. Twitter風 UI の実装 ---
st.title("𝕏 クローン (iwitter)")

# --- 投稿フォーム ---
st.subheader("いまどうしてる？")
with st.form("tweet_form", clear_on_submit=True):
    tweet_text = st.text_area("内容を入力してください", max_chars=140, placeholder="今日は何してた？")
    user_name = st.text_input("名前", value="匿名ユーザー")
    submitted = st.form_submit_button("ツイートする")

    if submitted:
        if tweet_text.strip() != "":
            # Firestoreにデータを追加
            db.collection("tweets").add({
                "text": tweet_text,
                "created_at": firestore.SERVER_TIMESTAMP, # サーバー時刻で保存
                "user_name": user_name
            })
            st.toast("投稿が完了しました！", icon="🚀")
            # 投稿直後に画面を更新するために再読み込み
            st.rerun()
        else:
            st.warning("内容を入力してください。")

# --- タイムライン表示 ---
st.divider()
st.subheader("最新の投稿")

try:
    # 投稿を新しい順（created_atの降順）に取得
    tweets_ref = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING)
    tweets = tweets_ref.stream()

    for tweet in tweets:
        data = tweet.to_dict()
        # 各ツイートを枠で囲って表示
        with st.container():
            st.markdown(f"**{data.get('user_name', '不明')}**")
            st.write(data.get('text', ''))
            # 時刻データの処理（Noneの場合の考慮）
            ts = data.get('created_at')
            if ts:
                st.caption(f"投稿日時: {ts.strftime('%Y/%m/%d %H:%M')}")
            st.divider()

except Exception as e:
    st.info("まだ投稿がありません。最初のツイートをしてみましょう！")
    # インデックス未作成エラーが出る場合があるため、エラー詳細を表示
    # st.error(f"エラー詳細: {e}")