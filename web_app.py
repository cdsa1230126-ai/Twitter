import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import textwrap
import re

if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        
        # 1. raw_data（カンマ区切り）から基本情報を復元
        parts = fb_sec["raw_data"].split(",")
        
        # 2. 【徹底洗浄】秘密鍵のクレンジング
        # ヘッダーとフッターを一旦取り除く
        raw_key = fb_sec["private_key"]
        raw_key = raw_key.replace("-----BEGIN PRIVATE KEY-----", "")
        raw_key = raw_key.replace("-----END PRIVATE KEY-----", "")
        
        # ★重要：英数字と記号（+ / =）以外の「すべての見えない文字（改行、スペース、タブ）」を完全消去
        pure_key = re.sub(r"[^A-Za-z0-9+/=]", "", raw_key)
        
        # 規格に従い、64文字ごとに改行を入れ直す
        formatted_content = "\n".join(textwrap.wrap(pure_key, 64))
        
        # 正しい形で包み直す
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_content}\n-----END PRIVATE KEY-----\n"
        
        # 3. 認証用辞書の組み立て
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

# --- 接続成功時 ---
db = firestore.client()
st.title("🏆 ついに、完全勝利です！")
st.success("Firebaseの厳格なフォーマットチェックをプログラムで突破しました！")