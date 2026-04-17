import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

if not firebase_admin._apps:
    try:
        # SecretsからJSON文字列を丸ごと取得
        json_string = st.secrets["firebase"]["service_account_json"]
        # 辞書に変換
        info_dict = json.loads(json_string)
        # 初期化
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        st.success("Firebase接続成功！")
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()