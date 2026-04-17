import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import re
import textwrap

# --- Firebase初期化関数 ---
def init_firebase():
    # すでに初期化されている場合はスキップ
    if not firebase_admin._apps:
        try:
            # 1. Secretsからデータを取得（ここで fb_sec を定義）
            if "firebase" not in st.secrets:
                st.error("Secretsに [firebase] セクションが見つかりません。")
                st.stop()
            
            fb_sec = st.secrets["firebase"]
            
            # 2. raw_dataの解析 (Project ID, Emailなど)
            parts = [p.strip() for p in fb_sec["raw_data"].split(",")]
            if len(parts) < 4:
                st.error("raw_data の項目数が足りません。4つの値をカンマで区切ってください。")
                st.stop()

            # 3. 秘密鍵の徹底洗浄
            raw_key = fb_sec["private_key"]
            # 改行コードの記号化(\n)を実際の改行に変換
            clean_key = raw_key.replace("\\n", "\n")
            # ヘッダー・フッター・空白・改行をすべて除去して純粋なBase64のみ抽出
            pure_base64 = re.sub(r"-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|[\s\n\r]", "", clean_key)
            
            # 4. Googleが認識できる64文字改行形式に再構成
            formatted_body = "\n".join(textwrap.wrap(pure_base64, 64))
            final_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_body}\n-----END PRIVATE KEY-----\n"

            # 5. 認証辞書の構成
            info_dict = {
                "type": "service_account",
                "project_id": parts[0],
                "private_key_id": parts[1],
                "private_key": final_key,
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
            st.success("Firebase接続成功！")
            
        except Exception as e:
            st.error(f"初期化失敗: {e}")
            st.stop()

# 初期化実行
init_firebase()

# DBクライアント作成
db = firestore.client()

# --- 以降、アプリのメイン処理 ---
st.write("🎉 データベースに接続されました。")