# 秘密鍵の洗浄：これであらゆる形式（改行混じり、1行、ヒアドキュメント）に対応します
raw_key = fb_sec["private_key"]

# 1. まず「実際の改行文字」や「エスケープされた改行(\\n)」をすべてスペースに置換
clean_key = raw_key.replace("\\n", "\n")

# 2. ヘッダーとフッターを一旦取り除く
inner_key = clean_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")

# 3. 中身から「改行」「スペース」「タブ」を完全に排除
pure_base64 = "".join(inner_key.split())

# 4. Googleが求める「64文字ごとの改行」形式に再構築
import textwrap
formatted_body = "\n".join(textwrap.wrap(pure_base64, 64))
final_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_body}\n-----END PRIVATE KEY-----\n"