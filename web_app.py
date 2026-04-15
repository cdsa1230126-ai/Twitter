import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from groq import Groq
from datetime import datetime

# ページ設定（ブラウザのタブ名や画面幅）
st.set_page_config(page_title="学内共有SNS & AI Assistant", layout="wide")

# --- 1. 接続設定 ---
# Googleスプレッドシートへの接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

# Groq AIの初期化（SecretsからAPIキーを読み込む）
# ※エラーが出る場合は api_key="gsk_..." と直接書いてもOK
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. データの読み込み関数 ---
def fetch_data():
    # SecretsからスプレッドシートのURLを取得
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # スプレッドシートを読み込む（ttl="0s"でキャッシュを無効化し常に最新を取得）
    return conn.read(spreadsheet=url, ttl="0s")

# データの読み込み実行
try:
    df = fetch_data()
except Exception as e:
    st.error("データの読み込みに失敗しました。スプレッドシートのURLや共有設定を確認してください。")
    st.stop()

# --- 3. サイドバー：Grok風 AIアシスタント ---
with st.sidebar:
    st.header("🤖 AIアシスタント")
    st.caption("授業や履修の相談、SNSの内容への質問など")
    
    # チャット履歴の管理
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    # 履歴を表示
    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # AIへの入力
    if ai_prompt := st.chat_input("AIに相談する..."):
        st.session_state.ai_messages.append({"role": "user", "content": ai_prompt})
        with st.chat_message("user"):
            st.markdown(ai_prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "あなたは学内SNSに常駐する優秀な助手です。"},
                        *st.session_state.ai_messages
                    ]
                )
                ans = response.choices[0].message.content
                st.markdown(ans)
        st.session_state.ai_messages.append({"role": "assistant", "content": ans})

# --- 4. メイン画面：SNSタイムライン ---
st.title("𝕏 学内共有タイムライン")

# 投稿フォーム
with st.expander("いまどうしてる？（新しい投稿）", expanded=True):
    # ユーザー名を入力できるようにする（空ならゲスト）
    user_name = st.text_input("名前", value="ゲストユーザー")
    tweet_text = st.text_area("内容を入力...", placeholder="今日は天気がいいですね")
    
    if st.button("投稿する"):
        if tweet_text:
            # 新しい投稿データを作成
            new_post = pd.DataFrame([{
                "user": user_name,
                "text": tweet_text,
                "time": datetime.now().strftime("%m/%d %H:%M")
            }])
            
            # 既存のデータと結合
            updated_df = pd.concat([df, new_post], ignore_index=True)
            
            # スプレッドシートを更新
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=updated_df)
            
            st.success("投稿が完了しました！")
            st.rerun() # 画面を更新して投稿を表示
        else:
            st.warning("内容を入力してください。")

st.divider()

# タイムラインの表示（新しい投稿が上に来るように逆順で表示）
if not df.empty:
    for index, row in df.iloc[::-1].iterrows():
        # スプレッドシートの列名に合わせて表示（user, text, time）
        st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px; background-color: #f8f9fa;">
                <span style="font-weight:bold; color:#1DA1F2;">{row['user']}</span> 
                <span style="color:gray; font-size:0.8em;">@{row['user']} · {row['time']}</span><br>
                <div style="margin-top:5px; color: #000;">{row['text']}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.write("まだ投稿がありません。最初の投稿をしてみましょう！")