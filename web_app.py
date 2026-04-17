import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

if not firebase_admin._apps:
    try:
        # Secretsから文字列を取得
        info_str = st.secrets["firebase"]["info"]
        
        # 文字列を辞書(dict)に変換
        info_dict = json.loads(info_str)
        
        # 秘密鍵内の改行（\n）が、文字列として入っている場合を考慮して置換
        if "private_key" in info_dict:
            info_dict["private_key"] = info_dict["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"Firebaseの初期化に失敗しました: {e}")
        st.stop()

db = firestore.client()
st.success("🎯 ついに接続成功です！")