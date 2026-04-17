import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firebase初期化 ---
if not firebase_admin._apps:
    try:
        # st.secrets から firebase 情報を取得
        fb_creds = dict(st.secrets["firebase"])
        
        # 秘密鍵が含まれているか確認
        if "private_key" not in fb_creds:
            st.error("Secretsに private_key がありません。")
            st.stop()
            
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# データベース接続
db = firestore.client()
st.success("Firebaseに正常に接続されました！")