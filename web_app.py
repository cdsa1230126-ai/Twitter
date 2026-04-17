import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firebase初期化 (最終クリーンアップ版) ---
if not firebase_admin._apps:
    try:
        # 1. Secretsから取得
        fb_dict = dict(st.secrets["firebase"])
        
        if "private_key" in fb_dict:
            pk = fb_dict["private_key"]
            
            # 2. \n が文字列として入っている場合に備えて改行に変換
            pk = pk.replace("\\n", "\n")
            
            # 3. 【重要】鍵の終端記号の後ろにゴミがあれば、物理的にカットする
            # これが InvalidByte(1629, 61) 対策の決め手です
            marker = "-----END PRIVATE KEY-----"
            if marker in pk:
                pk = pk[:pk.find(marker) + len(marker)]
            
            # 4. 前後の余計な空白文字を徹底削除
            fb_dict["private_key"] = pk.strip()
            
        # 5. 証明書としてロード
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# データベース接続
db = firestore.client()
st.success("Firebaseに正常に接続されました！")