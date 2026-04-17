import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import base64  # これが必要！

if not firebase_admin._apps:
    try:
        # Secretsから基本情報を取得
        fb_creds = {
            "type": "service_account",
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": "69a21c56a9c44c9abd9e71103614b8afda3c4819",
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": "101212246496723609810",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{st.secrets['firebase']['client_email']}",
            "universe_domain": "googleapis.com"
        }
        
        # Base64を解凍して秘密鍵を復元
        encoded_key = st.secrets["firebase"]["private_key_base64"]
        decoded_key = base64.b64decode(encoded_key).decode("utf-8")
        fb_creds["private_key"] = decoded_key
            
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.success("Firebaseに正常に接続されました！")