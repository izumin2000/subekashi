from time import sleep 
import requests
while 1 : 
    res = requests.get("https://earthmc.net/map/aurora/standalone/dynmap_earth.json")
    sleep(5)