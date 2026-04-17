import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --- Firebase初期化 (徹底クリーニング・最終手段版) ---
if not firebase_admin._apps:
    try:
        # 1. Secretsから取得
        fb_dict = dict(st.secrets["firebase"])
        
        if "private_key" in fb_dict:
            pk = fb_dict["private_key"]
            
            # 2. \n の置換（1行書き・複数行書き両方に対応）
            pk = pk.replace("\\n", "\n")
            
            # 3. 【最重要】InvalidByte(1629, 61) の原因となる末尾のゴミを徹底排除
            # "-----END PRIVATE KEY-----" のあとの文字をすべて消します
            end_marker = "-----END PRIVATE KEY-----"
            if end_marker in pk:
                pk = pk.split(end_marker)[0] + end_marker
            
            # 4. 前後の不要な改行やスペース、変な記号を完全に消す
            fb_dict["private_key"] = pk.strip()
            
        # 5. Firebaseに渡す
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        # 具体的に何が起きているか詳細を出すようにしました
        st.error(f"初期化失敗の詳細: {e}")
        st.stop()

db = firestore.client()
st.success("Firebaseに正常に接続されました！")