import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from groq import Groq
from datetime import datetime
import traceback

# ページ設定
st.set_page_config(page_title="SNSデバッグモード", layout="wide")

# --- 1. 接続設定 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Secretsの設定読み込みでエラーが発生しました。")
    st.code(traceback.format_exc())
    st.stop()

# --- 2. データの読み込み関数（デバッグ版） ---
def fetch_data():
    try:
        # 取得を試みる
        return conn.read(spreadsheet=SHEET_URL, ttl="0s")
    except Exception as e:
        # 失敗したら詳細を表示する
        st.error("🚨 【エラー詳細】スプレッドシートの読み込みに失敗しました")
        st.warning("以下のメッセージを教えてください：")
        st.code(str(e)) # エラーメッセージ本体
        st.info("スタックトレース（技術的な詳細）:")
        st.code(traceback.format_exc())
        st.stop()

# 実行
df = fetch_data()

# --- 3. メイン画面 ---
st.title("𝕏 学内共有タイムライン")
st.success("✅ データの読み込みに成功しました！")

# 投稿フォーム
with st.expander("いまどうしてる？", expanded=True):
    user_name = st.text_input("名前", value="ゲストユーザー")
    tweet_text = st.text_area("内容を入力...")
    
    if st.button("投稿する"):
        if tweet_text:
            try:
                new_post = pd.DataFrame([{
                    "user": user_name,
                    "text": tweet_text,
                    "time": datetime.now().strftime("%m/%d %H:%M")
                }])
                updated_df = pd.concat([df, new_post], ignore_index=True)
                
                # 保存の実行
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success("保存完了！")
                st.rerun()
            except Exception as e:
                st.error("保存中にエラーが発生しました。")
                st.code(str(e))

st.divider()

# タイムライン表示
if not df.empty:
    for index, row in df.iloc[::-1].iterrows():
        st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px; background-color: white;">
                <b>{row['user']}</b> <small style='color:gray;'>{row['time']}</small><br>
                <div style='color:black;'>{row['text']}</div>
            </div>
        """, unsafe_allow_html=True)