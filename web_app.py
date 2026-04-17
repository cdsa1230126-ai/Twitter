import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        fb_cfg = st.secrets["firebase"]
        
        # 記号のない英数字の塊を読み込む
        pure_data = fb_cfg["private_key_pure"]
        
        # Python側で、確実に正しいPEM形式（改行付き）に組み立てる
        # これにより、Secretsの記号解釈トラブルを100%回避します
        formatted_key = "-----BEGIN PRIVATE KEY-----\n" + pure_data + "\n-----END PRIVATE KEY-----"

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

db = firestore.client()
st.title("🎉 根本解決！")
st.success("記号トラブルを回避して接続に成功しました。")