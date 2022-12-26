from time import sleep
import requests, json
from orissaconfig import XIA_DISCORD_URL
from views import SendDiscord

isfirst = 1
isok = 1

while 1 :
    res = requests.get("https://earthmc.net/map/aurora/standalone/dynmap_earth.json")
    if res.status_code != 200 :
        if isok :
            message = f"エラーが発生しました。以下詳細です。\r```{res.text}...```"
            SendDiscord(message)
            isok = 0
        print("error")
    else :
        if isfirst :
            content = f"GETした結果は以下の通りです。\r```{res.text[:300]}...```"
            SendDiscord(message)
            isfirst = 0
            print("start")
        print(res.json()["currentcount"])
    sleep(4)