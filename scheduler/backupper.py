import requests
import pickle
from datetime import date

songs = requests.get("https://lyrics.imicomweb.com//api/song/?format=json").json()

fileName = f"home\\izuminapp\\izuminapp\\backups\\{date.today()}.pkl"
f = open(fileName, 'wb')
pickle.dump(songs, f)
f.close()