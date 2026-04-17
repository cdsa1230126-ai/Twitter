import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

if not firebase_admin._apps:
    try:
        # Secretsから文字列を取得
        info_json = st.secrets["firebase"]["info"]
        
        # JSON辞書に変換
        info_dict = json.loads(info_json)
        
        # 秘密鍵内の \n 文字を実際の改行に置換
        info_dict["private_key"] = info_dict["private_key"].replace("\\n", "\n")
        
        # Firebase初期化
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.success("🎉 おめでとうございます！ついに接続できました！")