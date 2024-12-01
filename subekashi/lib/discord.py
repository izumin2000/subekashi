from config.settings import *
import requests


# TODO send_discordへ
def sendDiscord(url, content):
    res = requests.post(url, data={'content': content})
    if (400 <= res.status_code < 600):
        return False
        
    return True