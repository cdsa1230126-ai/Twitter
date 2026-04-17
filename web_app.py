if not firebase_admin._apps:
    try:
        fb_sec = st.secrets["firebase"]
        # 1. 各項目の前後の空白を徹底排除
        parts = [p.strip() for p in fb_sec["raw_data"].split(",")]
        
        # 2. 秘密鍵の洗浄（改行をあえて入れない1行化スタイル）
        raw_key = fb_sec["private_key"]
        # ヘッダー/フッターを一度消して、中身のBase64だけを抽出
        pure_key = re.sub(r"-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|[\s\n\r]", "", raw_key)
        
        # 正しい枠組みで再構成（改行は \n 1つだけ）
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{pure_key}\n-----END PRIVATE KEY-----\n"
        
        info_dict = {
            "type": "service_account",
            "project_id": parts[0],
            "private_key_id": parts[1],
            "private_key": fixed_key,  # 洗浄済み鍵
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
        # デバッグ用：もし解決しない場合は、下の行のコメントアウトを外して
        # 辞書のキーが正しく入っているか確認してください（秘密鍵そのものは表示しないよう注意）
        # st.write(info_dict.keys()) 
        st.stop()