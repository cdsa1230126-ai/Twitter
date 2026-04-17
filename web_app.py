import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. Firebase初期化 (徹底洗浄版) ---
if not firebase_admin._apps:
    try:
        # Secretsから取得
        fb_dict = dict(st.secrets["firebase"])
        
        if "private_key" in fb_dict:
            pk = fb_dict["private_key"]
            
            # 文字列内の \n を実際の改行に変換
            pk = pk.replace("\\n", "\n")
            
            # 【重要】-----END PRIVATE KEY----- の後に文字があれば、そこで打ち切る
            end_marker = "-----END PRIVATE KEY-----"
            if end_marker in pk:
                pk = pk[:pk.find(end_marker) + len(end_marker)]
            
            # 前後の余計な空白を削除
            fb_dict["private_key"] = pk.strip()
            
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# 2. クライアント作成
db = firestore.client()
st.success("Firebaseに接続できました！")