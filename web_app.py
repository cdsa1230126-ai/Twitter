import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        fb_config = st.secrets["firebase"]
        
        # TOMLで """ を使ったので、そのまま正しいPEM形式として読み込めます
        fb_creds = {
            "type": "service_account",
            "project_id": fb_config["project_id"],
            "private_key_id": "69a21c56a9c44c9abd9e71103614b8afda3c4819",
            "client_email": fb_config["client_email"],
            "client_id": "101212246496723609810",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": fb_config["token_uri"],
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{fb_config['client_email']}",
            "universe_domain": "googleapis.com",
            "private_key": fb_config["private_key"]
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.title("🎉 Firebase連携完了")
st.success("ついに正しいPEM形式で読み込みに成功しました！")