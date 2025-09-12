import requests
from time import sleep
from config.settings import DEBUG


def send_discord(url, content):
    # urlが設定されていなかったら何もしない
    if not url:
        return True
    
    if DEBUG:
        return True

    # 余分なインデントの削除
    content = content.replace("\n            ", "\n")
    content = content.replace("\n        ", "\n")

    # メッセージを2000文字ごとに分割
    CHUNC_SIZE = 2000
    chunks = [content[i:i + CHUNC_SIZE] for i in range(0, len(content), CHUNC_SIZE)]

    try:
        for i, chunk in enumerate(chunks):
            # 送信
            res = requests.post(url, data={'content': chunk})
            if 400 <= res.status_code < 600:
                return False

            # 最後のチャンク以外は1秒待つ
            if i < len(chunks) - 1:
                sleep(1)

        return True
    
    except:
        return False