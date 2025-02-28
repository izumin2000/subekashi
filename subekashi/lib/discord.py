from config.settings import *
import requests


def send_discord(url, content):
    # urlが設定されていなかったら何もしない(コントリビュータ向け)
    if not url:
        return True
    
    res = requests.post(url, data={'content': content})
    if (400 <= res.status_code < 600):
        return False
        
    return True