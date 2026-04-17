import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firebase初期化 ---
if not firebase_admin._apps:
    try:
        # 1. Secretsから情報を取得
        fb_config = st.secrets["firebase"]
        
        # 2. 秘密鍵の \n を実際の改行コードに復元
        # (TOML上で "\n" と書かれた文字を、システムが認識できる改行に変換します)
        private_key = fb_config["private_key"].replace("\\n", "\n")

        # 3. 認証情報の辞書を作成
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
            "private_key": private_key
        }
        
        # 4. 初期化実行
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# --- 接続確認後の画面 ---
db = firestore.client()
st.title("🚀 Firebase連携成功")
st.success("Secretsから秘密鍵を安全に読み込み、接続できました!")