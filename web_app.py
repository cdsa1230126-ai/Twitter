import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import re

if not firebase_admin._apps:
    try:
        # 1. JSON文字列の取得
        json_string = st.secrets["firebase"]["service_account_json"]
        info_dict = json.loads(json_string)
        
        # 2. 秘密鍵の「超強力洗浄」
        raw_key = info_dict["private_key"]
        
        # ヘッダーとフッターを分離
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # 中身だけを抽出
        content = raw_key.replace(header, "").replace(footer, "")
        
        # 【重要】Base64で許可されている文字以外（制御文字やバイナリゴミ）を正規表現で完全に削除
        # A-Z, a-z, 0-9, +, /, = 以外をすべて排除
        pure_content = re.sub(r"[^A-Za-z0-9+/=]", "", content)
        
        # 3. 64文字ごとに改行を入れて再構成（これがPEM形式の厳密なルール）
        formatted_body = "\n".join([pure_content[i:i+64] for i in range(0, len(pure_content), 64)])
        final_key = f"{header}\n{formatted_body}\n{footer}\n"
        
        # 4. 辞書を更新して初期化
        info_dict["private_key"] = final_key
        
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
        st.success("Firebase接続に成功しましたゴミ文字を排除しました。")
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

db = firestore.client()