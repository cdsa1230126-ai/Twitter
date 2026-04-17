import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firebase初期化 (究極にシンプル化) ---
if not firebase_admin._apps:
    try:
        # Secretsから取得
        fb_dict = dict(st.secrets["firebase"])
        
        # 鍵の中の \n を実際の改行に戻す
        if "private_key" in fb_dict:
            fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
            
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.success("Firebaseに接続できました！")