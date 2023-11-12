import requests
songs = requests.get("https://lyrics.imicomweb.com/api/clean").json()
print(songs)