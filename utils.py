import streamlit as st
import hmac
import os
import time
import io
import config
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


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
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]  #Upload to correct folder
    }

    with io.FileIO(file_path, 'rb') as file_data:
        media = MediaIoBaseUpload(file_data, mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file['id']


def save_interview_data(username, transcripts_directory): #updated to transcripts_directory which is defined in other files
    """Save interview transcript and timing data in a single file and upload to Google Drive."""
    
    if not username: #In functional code, this is: if st.session_state.username is None:
        st.error("Username is not set!")
        return
    #should be specifying the timestamp, file name and directions, and file path
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{username}_{timestamp}.txt"
    file_path = os.path.join(transcripts_directory, file_name) #updated to transcripts_directory

    # Store chat transcript and time data in a single file
    with open(file_path, "w") as file:
        file.write(f"Interview Transcript for {username}\n")
        file.write("=" * 40 + "\n") #AP not sure what this means
        
        for message in st.session_state.messages:
            file.write(f"{message['role']}: {message['content']}\n") 
        
        file.write("\nInterview Metadata\n")
        file.write("=" * 40 + "\n")
        duration = (time.time() - st.session_state.start_time) / 60
        file.write(f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
        file.write(f"Interview duration (minutes): {duration:.2f}\n")

    # Upload file to Google Drive
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

