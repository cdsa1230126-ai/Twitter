import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import re

# --- ここから初期化処理 ---
if not firebase_admin._apps:
    try:
        # Secretsから取得
        fb_sec = st.secrets["firebase"]
        
        # 1. 各項目の前後の空白を徹底排除
        parts = [p.strip() for p in fb_sec["raw_data"].split(",")]
        
        # 2. 秘密鍵の洗浄（改行を排除して1行にまとめる）
        raw_key = fb_sec["private_key"]
        # ヘッダー、フッター、改行、空白をすべて削除
        pure_key = re.sub(r"-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|[\s\n\r]", "", raw_key)
        
        # 3. Googleが認識できる正しい形式に再構成
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{pure_key}\n-----END PRIVATE KEY-----\n"
        
        # 4. 認証情報ディクショナリの作成
        info_dict = {
            "type": "service_account",
            "project_id": parts[0],
            "private_key_id": parts[1],
            "private_key": fixed_key,
            "client_email": parts[2],
            "client_id": parts[3],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{parts[2]}",
            "universe_domain": "googleapis.com"
        }
        
        # 5. Firebase初期化
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        st.success("Firebaseの初期化に成功しました！")

    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# DBクライアントの作成
db = firestore.client()

# --- 動作確認用テスト ---
st.write("Firestoreへの接続準備が整いました。")