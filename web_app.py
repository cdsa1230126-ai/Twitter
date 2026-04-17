import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import textwrap
import re

if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        
        # 1. 基本データの復元
        parts = fb_sec["raw_data"].split(",")
        
        # 2. 【究極の秘密鍵クレンジング】
        # まず、ヘッダー/フッター、改行、スペースをすべて排除して「純粋な英数字のみ」の塊にする
        raw_key = fb_sec["private_key"]
        raw_key = raw_key.replace("-----BEGIN PRIVATE KEY-----", "")
        raw_key = raw_key.replace("-----END PRIVATE KEY-----", "")
        # 改行や空白、タブなどをすべて削除
        pure_key = re.sub(r"[\s\n\r]", "", raw_key)
        
        # 規格（RFC 7468）に従い、64文字ごとに本物の改行を入れる
        formatted_content = "\n".join(textwrap.wrap(pure_key, 64))
        
        # 正しいヘッダーとフッターで包み直す
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

# --- 接続成功 ---
db = firestore.client()
st.title("🏆 ついに完全勝利です！")
st.success("秘密鍵のフォーマット（64文字ルール）をプログラムで強制解決し、Firestoreへ接続できました")