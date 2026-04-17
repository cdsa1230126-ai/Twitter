import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

if not firebase_admin._apps:
    try:
        # Secretsから取得（'''で囲まれているので、ただの文字の塊として届きます）
        info_json_raw = st.secrets["firebase"]["info"]
        
        # JSONとして解析
        info_dict = json.loads(info_json_raw)
        
        # 秘密鍵の中にある「文字としての \n 」を「本物の改行コード」に置き換える
        # これが Firebase の認証に必須の処理です
        if "private_key" in info_dict:
            info_dict["private_key"] = info_dict["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.success("🎯 ついに接続に成功しました！お待たせしました！")