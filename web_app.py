import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. Firebase初期化 ---
if not firebase_admin._apps:
    try:
        # 鍵を直接ここに書き込みます（Secretsを経由しないので一番確実です）
        fb_creds = {
            "type": "service_account",
            "project_id": "iwitter-d2260",
            "private_key_id": "69a21c56a9c44c9abd9e71103614b8afda3c4819",
            "client_email": "firebase-adminsdk-fbsvc@iwitter-d2260.iam.gserviceaccount.com",
            "client_id": "101212246496723609810",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40iwitter-d2260.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com",
            # 秘密鍵を直接セット
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKgwggSlAgEAAoIBAQDuuHdJ6QwEnW5w\noxly7uTVqzlxVFj0zkKG6vox1ZFvkTOYeb4KvmMJcOTmBRT2i33LIgt6WD0jgDuw\pdCc1Lg50V7VGRLXAIsiZAYSHhvJ06dxrZh03EsFfQnS6Svea+XId1ZR1jx7Zbei\nt88C1zgQHL+X8OWswZYmgizwUgdL0hhI53O8txX5F6dkZYyHUWRaE81mxPd21S6y\n34ePT6LfYU/qg9IJ1xtaJnYAFNALQRU1VOOgA8E6MOdoAPILUTdTE4+ajD0zGJKH\nhjKdMxONA2s3Vp5yvhuqcYb1SXhyCQBvgwOfJTDYhpCECVyxdFqt93zxuMSmH7iV\nZtVYuGHbAgMBAAECggEAFxeB9oTUFEg0TDICvrLsMN0Ix/UsS7X+CnYFcLejg2LM\n1mWEZB6pjtq8UaHRNs4kg3dOG+4YL+xyGbLYfKs5DOK7ZSqxP1n+m3uIeM0vy/Ss\n4Fq2AivjF+tR/XRvuWq/hgZBM9Zg8GDVBCj6neA6vJhDUkvLs8vgHeZ+uVp9+S/w\nM6H1Dm4/cwsn3fQfM9yAsw7SRz1MmTwDhzLSv/IMqE1h6BVGMvuRMCJ1J4Bb9Na5\nCS1t1iLlDrsuR5gOvzy5QpQOcnnLYrd8hqxM5quhzHY0CRFgTs6kDAHxwV/8wsxA\nDs3qkKpmXF+MgwvK9DtNoAiRIkuKI9GhTSgQZh4FVQKBgQD6rNpLrT45CLd71T8h\nsHXX9eB87TYTima36WJ+zyvDuxUMKhkWVBWlA+jPkQ8aAlnvCD6L1cv7ZNVh1Eb\n/fZUifmn308lhyP3bzOOEKBUYAtQ9CJOoacWFa0X2I6yHZdVQGbEN4y0dZAL64Ei\n5zZQUg+HQ59lxakLEcJ70eERVQKBgQDzypror5LK/2nitMQfRi1w2WJXR2MShJ1p\nvR+flD5g+Nt2tcBH0kEvHGYzvEgrPier3LmYVK4id25DH0j9g26xd55GhrZidU3R\nyR791ZUCaE9eHPI7aqS/VMM7bk+i8aZP5h8UZRK9kmUbo854QnLI6CTjkw54XQfD\ntm1tplJmbwKBgQDamG1sXNDL75wBsr3w1X54EC3gNuNXVSHW2nyCzMHobn0MFbpi\nd7glJ8xTMHNUseyxt06SnUHMm8JFbVD/tgFfS0qYZ5WfRi/JEAHHOxx1N6Pmnl5k\nb3dDPPfKuaAGFuPnBdgX99ENdQ9+NYpRI4srk8PS0tdnamy1KHGOhEFeWQKBgQDU\nyx/zwmyq684MqCQX+DVprxV7gUAkxcRwqzeTHt5j3lQRhgtTpV5oNK2wssN7m0Ed\nbghBwohMZVrFE+WuAq74EKUCgktoHWPTnW2Duo3aEBpW14VH/4nVx7KxiVPRsoOs\gcfzm3GJDPikquwxZRAbU/mxUh+O1g95nIjDZ6Lc72QKBgQDGsu21nWOXHzihplP+\nBmOIgWqkAtoup5RnX1neyviZjgxVqHz0oQPeIXDbc1DGmmxHkVYzM+VwqrRYOm3S\njg4ToZtic32OCoYlCt7sMwgSNnAPvMZRyO9v7twjYs8TmVoTTTMt8bLzryBe+jl/\nLU/aGYHdRiMnU0eBIHV5lJG8Kw==\n-----END PRIVATE KEY-----"
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"初期化失敗: {e}")
        st.stop()

# --- 2. データベース接続 ---
db = firestore.client()
st.title("🔥 接続成功！")
st.success("Firebaseに直接接続できました!")