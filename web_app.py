import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import textwrap

if not firebase_admin._apps:
    try:
        fb_cfg = st.secrets["firebase"]
        
        # 1. 英数字だけの塊を取得
        pure_data = fb_cfg["private_key_pure"]
        
        # 2. 秘密鍵を正しいPEM形式に整形（ここが重要！）
        # RSA鍵のルールに従い、64文字ごとに本物の改行を入れます
        wrapped_data = "\n".join(textwrap.wrap(pure_data, 64))
        
        # 3. 前後のヘッダー・フッターを合体
        formatted_key = f"-----BEGIN PRIVATE KEY-----\n{wrapped_data}\n-----END PRIVATE KEY-----\n"

        fb_creds = {
            "type": "service_account",
            "project_id": fb_cfg["project_id"],
            "private_key_id": "69a21c56a9c44c9abd9e71103614b8afda3c4819",
            "client_email": fb_cfg["client_email"],
            "client_id": "101212246496723609810",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": fb_cfg["token_uri"],
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{fb_cfg['client_email']}",
            "universe_domain": "googleapis.com",
            "private_key": formatted_key
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# --- 接続成功メッセージ ---
db = firestore.client()
st.title("🏆 ついに完全勝利です！")
st.success("鍵の整形（64文字改行ルール）をクリアし、接続に成功しました！")