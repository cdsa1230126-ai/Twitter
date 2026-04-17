import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Firebase初期化
if not firebase_admin._apps:
    try:
        # Secretsから文字列としてJSONを取得
        info_str = st.secrets["firebase"]["info"]
        
        # 文字列を辞書オブジェクトに変換
        info_dict = json.loads(info_str)
        
        # 秘密鍵の改行文字が正しく解釈されるよう念のため処理
        info_dict["private_key"] = info_dict["private_key"].replace("\\n", "\n")
        
        # 認証
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"Firebaseの初期化に失敗しました: {e}")
        st.stop()

db = firestore.client()
st.success("🎯 ついに接続成功しました！おめでとうございます！")