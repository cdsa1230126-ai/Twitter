import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        # Secretsから取得
        fb_secrets = st.secrets["firebase"]
        
        # \n 文字を実際の改行に確実に変換する処理は残しておく（これがエラー防止に重要）
        clean_key = fb_secrets["private_key"].replace("\\n", "\n")

        fb_creds = {
            "type": "service_account",
            "project_id": fb_secrets["project_id"],
            "private_key_id": "69a21c56a9c44c9abd9e71103614b8afda3c4819",
            "client_email": fb_secrets["client_email"],
            "client_id": "101212246496723609810",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{fb_secrets['client_email']}",
            "universe_domain": "googleapis.com",
            "private_key": clean_key
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()