import requests
from time import sleep

while 1 :
    songs = requests.get("https://lyrics.imicomweb.com/api/clean").json()
    print(songs)
    sleep(300)