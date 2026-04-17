import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firebase初期化 ---
if not firebase_admin._apps:
    try:
        # st.secrets["firebase"] の中身を丸ごと辞書として渡す
        fb_creds = dict(st.secrets["firebase"])
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.success("Firebaseに正常に接続されました！")