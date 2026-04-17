import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import re
import textwrap

# ページの設定（ブラウザのタブに表示される名前とアイコン）
st.set_page_config(page_title="iwitter", page_icon="𝕏")

# --- 1. Firebase初期化設定 ---
if not firebase_admin._apps:
    try:
        # SecretsからJSON文字列を丸ごと取得
        json_string = st.secrets["firebase"]["service_account_json"]
        info_dict = json.loads(json_string)
        
        # 秘密鍵の超強力洗浄（念のため残してあります）
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        content = info_dict["private_key"].replace(header, "").replace(footer, "")
        pure_content = re.sub(r"[^A-Za-z0-9+/=]", "", content)
        formatted_body = "\n".join([pure_content[i:i+64] for i in range(0, len(pure_content), 64)])
        info_dict["private_key"] = f"{header}\n{formatted_body}\n{footer}\n"
        
        # 初期化実行
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"Firebase初期化失敗: {e}")
        st.stop()

# Firestoreクライアントの作成
db = firestore.client()

# --- 2. Twitter風 UI の実装 ---
st.title("Iwitter")

# --- 投稿フォームエリア ---
# st.formの「clear_on_submit=True」で送信後に文字を消します
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
                "created_at": firestore.SERVER_TIMESTAMP,
                "user_name": user_name
            })
            st.toast("投稿が完了しました！", icon="🚀")
            # 投稿直後に画面を更新して自分の投稿を反映させる
            st.rerun()
        else:
            st.warning("内容を入力してください。")

# --- 3. タイムライン表示エリア（自動更新機能付き） ---
st.divider()
st.subheader("最新の投稿（5秒ごとに自動更新）")

# fragmentを使ってこの関数の中身だけを定期的に実行（リロード）する
@st.fragment(run_every=5)
def show_timeline():
    try:
        # 投稿を新しい順（created_atの降順）に取得
        tweets_ref = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING)
        tweets = tweets_ref.stream()

        count = 0
        for tweet in tweets:
            count += 1
            data = tweet.to_dict()
            
            # 各ツイートを枠線付きのコンテナで表示
            with st.container(border=True):
                st.markdown(f"**{data.get('user_name', '不明')}**")
                st.write(data.get('text', ''))
                
                # 時刻の表示
                ts = data.get('created_at')
                if ts:
                    # 日本時間にする場合は調整が必要ですが、まずはそのまま表示
                    st.caption(f"🕒 {ts.strftime('%H:%M:%S')}")
        
        if count == 0:
            st.info("まだ投稿がありません。最初のツイートをしてみましょう！")

    except Exception as e:
        # インデックス作成が必要な場合、ここにエラーと作成用URLが表示されます
        st.error(f"タイムライン取得エラー: {e}")
        st.info("※Firestoreで『インデックス作成』が必要な場合があります。エラー内のURLを確認してください。")

# タイムライン関数の実行
show_timeline()