# --- ツイート投稿フォーム ---
st.subheader("いまどうしてる？")
with st.form("tweet_form"):
    tweet_text = st.text_area("内容を入力", max_chars=140)
    submitted = st.form_submit_button("ツイートする")

    if submitted and tweet_text:
        # Firestoreに保存
        db.collection("tweets").add({
            "text": tweet_text,
            "created_at": firestore.SERVER_TIMESTAMP,
            "user_name": "テストユーザー"
        })
        st.success("投稿されました！")

# --- タイムライン表示 ---
st.divider()
st.subheader("タイムライン")

# 投稿を新しい順に取得
tweets_ref = db.collection("tweets").order_by("created_at", direction=firestore.Query.DESCENDING)
tweets = tweets_ref.stream()

for tweet in tweets:
    data = tweet.to_dict()
    # 投稿内容をカード風に表示
    st.info(f"**{data.get('user_name')}**: {data.get('text')}")