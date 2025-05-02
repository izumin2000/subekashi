from config.settings import *
import requests


def send_discord(url, content):
    # urlが設定されていなかったら何もしない(コントリビュータ向け)
    if not url:
        return True
    
    content = content.replace("\n            ", "\n")
    content = content.replace("\n        ", "\n")
    
    if len(content) > 2000:
        content = content[:1997] + "..."
    
    res = requests.post(url, data={'content': content})
    if (400 <= res.status_code < 600):
        return False
        
    return True