import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import base64

# --- 1. Firebase初期化設定 ---
# 既に初期化されている場合はスキップ
if not firebase_admin._apps:
    try:
        # Secretsから情報を取得（Base64対応版）
        fb_secrets = st.secrets["firebase"]
        
        # サービスアカウントの辞書を作成
        fb_creds = {
            "type": "service_account",
            "project_id": fb_secrets["project_id"],
            "private_key_id": "69a21c56a9c44c9abd9e71103614b8afda3c4819",
            "client_email": fb_secrets["client_email"],
            "client_id": "101212246496723609810",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": fb_secrets["token_uri"],
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{fb_secrets['client_email']}",
            "universe_domain": "googleapis.com"
        }
        
        # --- 秘密鍵の復元 (Base64デコード) ---
        encoded_key = fb_secrets["private_key_base64"]
        
        # 'utf-8', 'ignore' を指定することで、万が一のゴミ文字によるエラーを回避
        decoded_key = base64.b64decode(encoded_key).decode("utf-8", "ignore")
        
        fb_creds["private_key"] = decoded_key
            
        # Firebaseアプリを初期化
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# --- 2. データベース(Firestore)への接続 ---
db = firestore.client()

# --- 3. アプリのメイン画面 ---
st.title("🔥 Firebase 接続テスト成功！")
st.success("データベースへの接続が正常に完了しました。")

st.write("これで、Groq APIやFirestoreを使った高度な機能の実装に進めます！")

# 動作確認用にプロジェクトIDを表示
st.info(f"Connected to project: `{st.secrets['firebase']['project_id']}`")