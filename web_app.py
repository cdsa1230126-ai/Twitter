import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from groq import Groq
from datetime import datetime

# ページ設定
st.set_page_config(page_title="学内共有SNS & AI", layout="wide")

# --- 1. 接続設定 ---
# Secretsに設定したサービスアカウント情報を使って接続
conn = st.connection("gsheets", type=GSheetsConnection)

# Groq AIの初期化
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# スプレッドシートのURL（Secretsから取得）
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 2. データの読み込み関数 ---
def fetch_data():
    # 常に最新のデータをスプレッドシートから直接読み込む
    return conn.read(spreadsheet=SHEET_URL, ttl="0s")

# 起動時にデータを読み込む
try:
    df = fetch_data()
except Exception as e:
    st.error(f"データの読み込みに失敗しました。スプレッドシートの共有設定（サービスアカウントの追加）を確認してください。")
    st.stop()

# --- 3. サイドバー：AIアシスタント ---
with st.sidebar:
    st.header("🤖 AIアシスタント")
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if ai_prompt := st.chat_input("AIに相談する..."):
        st.session_state.ai_messages.append({"role": "user", "content": ai_prompt})
        with st.chat_message("user"):
            st.markdown(ai_prompt)
            
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "あなたは大学生活をサポートする優秀な助手です。"}, *st.session_state.ai_messages]
            )
            ans = response.choices[0].message.content
            st.markdown(ans)
        st.session_state.ai_messages.append({"role": "assistant", "content": ans})

# --- 4. メイン画面：SNSタイムライン ---
st.title("𝕏 学内共有タイムライン")

# 投稿フォーム
with st.expander("いまどうしてる？", expanded=True):
    user_name = st.text_input("名前", value="ゲストユーザー")
    tweet_text = st.text_area("内容を入力...")
    
    if st.button("投稿する"):
        if tweet_text:
            # 最新のデータを取得
            current_df = fetch_data()
            
            # 新しい投稿を作成
            new_post = pd.DataFrame([{
                "user": user_name,
                "text": tweet_text,
                "time": datetime.now().strftime("%m/%d %H:%M")
            }])
            
            # 既存データに結合
            updated_df = pd.concat([current_df, new_post], ignore_index=True)
            
            # 【重要】スプレッドシートを更新（サービスアカウント経由で保存）
            try:
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success("投稿が保存されました！")
                st.rerun() # 画面をリロードして反映
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")
        else:
            st.warning("内容を入力してください。")

st.divider()

# タイムラインの表示（逆順）
if not df.empty:
    for index, row in df.iloc[::-1].iterrows():
        st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px; background-color: white;">
                <span style="font-weight:bold; color:#1DA1F2;">{row['user']}</span> 
                <span style="color:gray; font-size:0.8em;">@{row['user']} · {row['time']}</span><br>
                <div style="margin-top:5px; color: black;">{row['text']}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("まだ投稿がありません。最初の投稿をしてみましょう！")