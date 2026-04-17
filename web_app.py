import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        
        # カンマ区切りの文字列をリストに戻す
        parts = fb_sec["raw_data"].split(",")
        
        # 辞書を再構成（プログラムが手動で組み立てるので、TOMLのパースエラーが起きません）
        info_dict = {
            "type": "service_account",
            "project_id": parts[0],
            "private_key_id": parts[1],
            "private_key": fb_sec["private_key"],
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
st.success("🏆 やりました！ついに、ついに成功です！")