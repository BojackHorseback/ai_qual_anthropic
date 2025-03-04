import streamlit as st
import hmac
import os
import time
import io
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_ID = "1-y9bGuI0nmK22CPXg804U5nZU3gA--lV"  # Your Google Drive folder ID


def authenticate_google_drive():
    """Authenticate using a service account and return the Google Drive service."""
    key_path = "/etc/secrets/service-account.json"

    if not os.path.exists(key_path):
        raise FileNotFoundError("Google Drive credentials file not found!")

    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def upload_file_to_drive(service, file_path, file_name, mimetype='text/plain'):
    """Upload a file to Google Drive."""
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]  
    }

    with io.FileIO(file_path, 'rb') as file_data:
        media = MediaIoBaseUpload(file_data, mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file['id']


def save_interview_data(username, save_directory):
    """Save interview transcript and timing data in a single file and upload to Google Drive."""
    if not username:
        st.error("Username is not set!")
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{username}_{timestamp}.txt"
    file_path = os.path.join(save_directory, file_name)

    # Store chat transcript and time data in a single file
    with open(file_path, "w") as file:
        file.write(f"Interview Transcript for {username}\n")
        file.write("=" * 40 + "\n")
        
        for message in st.session_state.messages:
            file.write(f"{message['role']}: {message['content']}\n")
        
        file.write("\nInterview Metadata\n")
        file.write("=" * 40 + "\n")
        duration = (time.time() - st.session_state.start_time) / 60
        file.write(f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
        file.write(f"Interview duration (minutes): {duration:.2f}\n")

    # Upload file to Google Drive
    try:
        service = authenticate_google_drive()
        file_id = upload_file_to_drive(service, file_path, file_name)
        st.success(f"File uploaded! File ID: {file_id}")
    except Exception as e:
        st.error(f"Failed to upload file: {e}")

