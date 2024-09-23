import requests
from config.settings import *


def sendDiscord(url, content) :
    res = requests.post(url, data={'content': content})
    return res.status_code