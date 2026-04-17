import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import base64

if not firebase_admin._apps:
    try:
        # 1. Base64文字列を取得
        b64_key = st.secrets["firebase"]["private_key_b64"]
        
        # 2. デコードして「本物の秘密鍵」を復元
        # これにより、改行や文字数制限などのすべての問題を自動解決します
        decoded_key = base64.b64decode(b64_key).decode("utf-8")

        # 3. 認証情報の組み立て
        fb_cfg = st.secrets["firebase"]
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
            "private_key": decoded_key
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.title("🏆 ついに、本当の解決です！")
st.success("Base64方式により、秘密鍵の復元に成功しました！")