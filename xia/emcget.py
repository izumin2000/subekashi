from time import sleep
import requests, json
from orissaconfig import XIA_DISCORD_URL

headers = {'Content-Type': 'application/json'}
isfirst = 1
isok = 1
# requests.post(XIA_DISCORD_URL, data={'content': f"Hello Orissa!"})

while 1 :
    res = requests.get("https://earthmc.net/map/aurora/standalone/dynmap_earth.json")
    if res.status_code != 200 :
        if isok :
            content = f"エラーが発生しました。以下詳細です。\r```" + res.text.replace("\n", "\r") + "\r...```"
            postres = requests.post(XIA_DISCORD_URL, json.dumps({"content": content}), headers = headers)
            isok = 0
        print("error")
    else :
        if isfirst :
            content = f"GETした結果は以下の通りです。\r```" + res.text.replace("\n", "\r")[:300] + "\r...```"
            postres = requests.post(XIA_DISCORD_URL, json.dumps({"content": content}), headers = headers)
            print(postres, end=" ")
            isfirst = 0
            print("start")
        print(res.json()["currentcount"])
    sleep(4)