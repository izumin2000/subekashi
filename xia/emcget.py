from time import sleep 
import requests
DISCORD_URL = "https://discord.com/api/webhooks/1044246836644425758/6yV-POi0_9DDcfpL8oAqz8PJfBM3g8Dx1gOpBMcCjrloA3sU06HRH2CtDfxkkBUU0UmD"

while 1 : 
    res = requests.get("https://earthmc.net/map/aurora/standalone/dynmap_earth.json")
    if res.status_code != 200 :
        requests.post(DISCORD_URL, data={'content': f"エラーが発生しました。以下詳細です。\n f```{res.text}```"})
    sleep(6)