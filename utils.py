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
if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_ID = "1-y9bGuI0nmK22CPXg804U5nZU3gA--lV"  # Your Google Drive folder ID

def authenticate_google_drive():
    """Authenticate using a service account and return the Google Drive service."""
    key_path = "/etc/secrets/service-account.json"

    if not os.path.exists(key_path):
        st.error("Google Drive credentials file not found!")
        return None

    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def upload_file_to_drive(service, file_path, file_name, mimetype='text/plain'):
    """Upload a file to a specific Google Drive folder."""
    
    if service is None:
        st.error("Google Drive authentication failed!")
        return None

    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]  # Upload into the specified folder
    }

    try:
        with io.FileIO(file_path, 'rb') as file_data:
            media = MediaIoBaseUpload(file_data, mimetype=mimetype)

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

        return file['id']
    except Exception as e:
        st.error(f"Failed to upload file: {e}")
        return None


def save_and_upload_interview(username, save_directory):
    """Save interview transcript & timing data in one file, then upload to Google Drive."""
    
    if not username:
        st.error("Username is not set!")
        return None

    # Ensure the directory exists
    os.makedirs(save_directory, exist_ok=True)

    # Create a unique filename with the interview completion time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{username}_{timestamp}.txt"
    file_path = os.path.join(save_directory, file_name)

    try:
        # Open the file and write transcript + timing data
        with open(file_path, "w") as file:
            # Store chat transcript
            file.write("### Interview Transcript ###\n")
            if "messages" in st.session_state and st.session_state.messages:
                for message in st.session_state.messages:
                    file.write(f"{message['role']}: {message['content']}\n")
            else:
                file.write("No messages recorded.\n")

            # Store interview start time and duration
            if "start_time" in st.session_state:
                duration = (time.time() - st.session_state.start_time) / 60
                file.write("\n### Interview Timing ###\n")
                file.write(f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
                file.write(f"Interview duration (minutes): {duration:.2f} minutes\n")
            else:
                file.write("\nStart time not available.\n")

        # Upload file to Google Drive
        service = authenticate_google_drive()
        if service:
            file_id = upload_file_to_drive(service, file_path, file_name)
            if file_id:
                st.success(f"File uploaded successfully! File ID: {file_id}")
            else:
                st.error("File upload failed.")
        else:
            st.error("Google Drive authentication failed.")

    except Exception as e:
        st.error(f"Failed to save interview data: {e}")
        return None

    return file_path


def check_password():
    """Returns 'True' if the user has entered a correct password."""
    def login_form():
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        if (
            "username" in st.session_state and 
            st.session_state.username in st.secrets.passwords and 
            hmac.compare_digest(st.session_state.password, st.secrets.passwords[st.session_state.username])
        ):
            st.session_state.password_correct = True
        else:
            st.session_state.password_correct = False
            st.error("User or password incorrect")

        # Remove password from session state for security
        if "password" in st.session_state:
            del st.session_state.password  

    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    login_form()
    return False, None


def check_if_interview_completed(directory, username):
    """Check if interview transcript file exists."""
    if username != "testaccount":
        return os.path.exists(os.path.join(directory, f"{username}.txt"))
    return False

