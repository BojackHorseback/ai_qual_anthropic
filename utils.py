import streamlit as st
import hmac
import os
import time
import io
from datetime import datetime
from google.oauth2.service_account import Credentials  # FIXED import
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import config

# Initialize session state variables
if "username" not in st.session_state:
    st.session_state.username = None

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
    """Upload a file to a specific Google Drive folder."""
    
    FOLDER_ID = "1-y9bGuI0nmK22CPXg804U5nZU3gA--lV"  # Your folder ID

    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]  # Upload into the specified folder
    }

    with io.FileIO(file_path, 'rb') as file_data:
        media = MediaIoBaseUpload(file_data, mimetype=mimetype)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

    return file['id']


def save_interview_data_to_drive(transcript_path, time_path):
    """Save interview transcript & timing data to Google Drive."""
    
    if st.session_state.username is None:
        st.error("Username is not set!")
        return

    service = authenticate_google_drive()  # Authenticate Drive API

    try:
        transcript_id = upload_file_to_drive(service, transcript_path, os.path.basename(transcript_path))
        time_id = upload_file_to_drive(service, time_path, os.path.basename(time_path))
        st.success(f"Files uploaded! Transcript ID: {transcript_id}, Time ID: {time_id}")
    except Exception as e:
        st.error(f"Failed to upload files: {e}")


def save_interview_data(username, transcripts_directory, times_directory, file_name_addition_transcript="", file_name_addition_time=""):
    """Write interview data to disk."""
    transcript_file = os.path.join(transcripts_directory, f"{username}{file_name_addition_transcript}.txt")
    time_file = os.path.join(times_directory, f"{username}{file_name_addition_time}.txt")

    # Store chat transcript
    with open(transcript_file, "w") as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    # Store interview start time and duration
    with open(time_file, "w") as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
        d.write(f"Interview duration (minutes): {duration:.2f}")

    return transcript_file, time_file


def check_password():
    """Returns 'True' if the user has entered a correct password."""
    def login_form():
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        if st.session_state.username in st.secrets.passwords and hmac.compare_digest(
            st.session_state.password,
            st.secrets.passwords[st.session_state.username],
        ):
            st.session_state.password_correct = True
        else:
            st.session_state.password_correct = False
        del st.session_state.password  # Don't store password in session state

    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    login_form()
    if "password_correct" in st.session_state:
        st.error("User or password incorrect")
    return False, st.session_state.username


def check_if_interview_completed(directory, username):
    """Check if interview transcript/time file exists."""
    if username != "testaccount":
        return os.path.exists(os.path.join(directory, f"{username}.txt"))
    return False
