from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from config.settings import (
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_CLIENT_SECRET,
    GOOGLE_DRIVE_REFRESH_TOKEN,
    GOOGLE_DRIVE_FOLDER_ID,
)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def get_drive_service():
    credentials = Credentials(
        token=None,
        refresh_token=GOOGLE_DRIVE_REFRESH_TOKEN,
        token_uri=DRIVE_TOKEN_URI,
        client_id=GOOGLE_DRIVE_CLIENT_ID,
        client_secret=GOOGLE_DRIVE_CLIENT_SECRET,
        scopes=DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_backup(file_path, file_name):
    service = get_drive_service()
    file_metadata = {"name": file_name, "parents": [GOOGLE_DRIVE_FOLDER_ID]}
    # MediaFileUploadは開いたファイルを閉じないため、closeを保証できるMediaIoBaseUploadを使う
    with open(file_path, "rb") as f:
        media = MediaIoBaseUpload(f, mimetype="application/x-sqlite3")
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()


def delete_old_backups(keep_nums):
    service = get_drive_service()
    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false"
    response = service.files().list(q=query, orderBy="name", fields="files(id, name)").execute()
    files = response.get("files", [])

    for file in files[:len(files) - keep_nums]:
        service.files().delete(fileId=file["id"]).execute()
