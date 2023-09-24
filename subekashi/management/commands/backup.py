import requests
import pickle
from datetime import datetime
import os


BACKUP_FOLDER_NUMS = 30
if "C:" in os.getcwd() :
    BACKUP_FOLDER = "backups/"
else :
    BACKUP_FOLDER = "/home/izuminapp/izuminapp/backups/"


files = os.listdir(BACKUP_FOLDER)
now = datetime.now()
if len(files) <= BACKUP_FOLDER_NUMS :
    songs = requests.get("https://lyrics.imicomweb.com/api/song/?format=json").json()
    if now.hour % 6 != 0 :
        fileName = f"{BACKUP_FOLDER}{now.strftime('%Y-%m-%d-%H')}.pkl"
        f = open(fileName, 'wb')
        pickle.dump(songs, f)
        f.close()


if len(files) >= BACKUP_FOLDER_NUMS :
    files.sort()
    first_file = os.path.join(BACKUP_FOLDER, files[0])
    
    try:
        os.remove(first_file)
    except OSError as e:
        print(f"ファイルの削除中にエラーが発生しました: {str(e)}")