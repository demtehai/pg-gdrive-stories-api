from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from datetime import datetime, timedelta
from io import BytesIO
import os
import json

app = Flask(__name__)
CORS(app)  # ✅ Разрешаем CORS

# Авторизация
credentials_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
credentials = service_account.Credentials.from_service_account_info(
    credentials_info,
    scopes=["https://www.googleapis.com/auth/drive.readonly"]
)
drive_service = build("drive", "v3", credentials=credentials)
FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")

@app.route("/")
def home():
    return "✅ GDrive Stories API is working."

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/stories")
def list_stories():
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"
        query = f"'{FOLDER_ID}' in parents and (mimeType contains 'image/' or mimeType contains 'video/') and modifiedTime > '{cutoff}'"
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, mimeType, modifiedTime)",
            orderBy="modifiedTime desc"
        ).execute()
        files = results.get("files", [])
        for f in files:
            f["webContentLink"] = f"https://drive.google.com/uc?id={f['id']}&export=download"
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/media")
def media():
    file_id = request.args.get("id")
    if not file_id:
        return "Missing file ID", 400

    try:
        request_media = drive_service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request_media)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        file_metadata = drive_service.files().get(fileId=file_id, fields="mimeType, name").execute()
        mime_type = file_metadata["mimeType"]
        name = file_metadata["name"]
        return send_file(fh, mimetype=mime_type, download_name=name)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
