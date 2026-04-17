import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import textwrap

if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        
        # 1. 基本データの復元
        parts = fb_sec["raw_data"].split(",")
        
        # 2. 秘密鍵の整形（ここが今回のポイント！）
        # 前後のヘッダー・フッターを一度取り除き、中身を64文字ごとに改行し直します
        raw_key = fb_sec["private_key"].replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").replace("\n", "").strip()
        formatted_content = "\n".join(textwrap.wrap(raw_key, 64))
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_content}\n-----END PRIVATE KEY-----\n"
        
        # 3. 辞書の組み立て
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
        
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()
st.title("🏆 完全勝利")
st.success("Firebaseへの接続に成功しました！これですべての準備が整いました。")