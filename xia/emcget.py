from time import sleep 
import requests
from config.settings import XIA_DISCORD_URL

while 1 : 
    res = requests.get("https://earthmc.net/map/aurora/standalone/dynmap_earth.json")
    if res.status_code != 200 :
        requests.post(XIA_DISCORD_URL, data={'content': f"@KANATA200\nエラーが発生しました。以下詳細です。\n f```{res.text}```"})
    sleep(5)