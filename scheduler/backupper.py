import requests
import pickle
from datetime import datetime
from glob import glob
import os

if "C:" in os.getcwd() :
    BACKUP_FOLDER = "backups\\"
    PKL_FILES = f"{BACKUP_FOLDER}\\*.pkl"
else :
    BACKUP_FOLDER = "/home/izuminapp/izuminapp/backups/"
    PKL_FILES = f"{BACKUP_FOLDER}/*.pkl"

songs = requests.get("https://lyrics.imicomweb.com//api/song/?format=json").json()

fileName = f"{BACKUP_FOLDER}{datetime.now().strftime('%Y-%m-%d-%H')}.pkl"
f = open(fileName, 'wb')
pickle.dump(songs, f)
f.close()

# f = glob(PKL_FILES)
# os.remove(f[0])