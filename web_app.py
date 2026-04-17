import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import textwrap

# --- 1. Firebase初期化設定 ---
if not firebase_admin._apps:
    try:
        # Secretsから取得
        fb_cfg = st.secrets["firebase"]
        
        # 【重要】英数字だけの塊を取得
        pure_data = fb_cfg["private_key_pure"]
        
        # 【重要】RSA鍵の厳格なルール「64文字ごとに改行」を強制適用
        # これをやらないと "extra data" エラーになります
        wrapped_data = "\n".join(textwrap.wrap(pure_data, 64))
        
        # 正しいPEM形式（ヘッダー・フッター・改行）に組み立て
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
        
        # Firebaseアプリを初期化
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# --- 2. 接続確認 ---
db = firestore.client()

st.title("🏆 ついに完全接続！")
st.success("秘密鍵のフォーマット問題を突破し、Firestoreへの接続に成功しました。")

# プロジェクトIDを表示して確認
st.info(f"現在の接続先: {fb_cfg['project_id']}")