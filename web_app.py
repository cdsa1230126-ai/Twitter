import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firebase初期化 ---
if not firebase_admin._apps:
    try:
        # 1. Secretsから辞書形式で取得
        fb_cfg = st.secrets["firebase"]
        
        # 2. 秘密鍵内の「\\n」(文字列) を「\n」(本物の改行コード) に確実に変換
        # これにより、TOMLのパースエラーやPEMの読み込みエラーを防ぎます
        raw_key = fb_cfg["private_key"]
        fixed_key = raw_key.replace("\\n", "\n")

        # 3. 認証情報の組み立て
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
            "private_key": fixed_key
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# --- 以降、DB処理 ---
db = firestore.client()
st.title("🛡️ セキュアな接続に成功！")
st.success("鍵をコードに書かずに、Firebaseへ接続できました。")