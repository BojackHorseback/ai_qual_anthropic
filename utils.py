#utils.py - Updated with proper UID handling and metadata

import streamlit as st
import hmac
import time
import io
import os
from datetime import datetime
from google.oauth2.service_account import Credentials 
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import config
import pytz

# Initialize session state variables
if "username" not in st.session_state:
    # Define Central Time (CT) timezone
    central_tz = pytz.timezone("America/Chicago")
    # Get current date and time in CT
    current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d_%H-%M-%S")
    st.session_state.username = f"User_{current_datetime}"

# Initialize UID in session state if not already set
if "response_id" not in st.session_state:
    query_params = st.query_params
    # Look for UID parameter only
    response_id = query_params.get("UID", None)
    st.session_state.response_id = response_id

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
    """Upload a file to a specific Google Drive folder."""
    
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

def save_interview_data_to_drive(transcript_path):
    """Save interview transcript & timing data to Google Drive."""
    
    if st.session_state.username is None:
        # Define a fallback username with timestamp if none exists
        central_tz = pytz.timezone("America/Chicago")
        current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d_%H-%M-%S")
        st.session_state.username = f"User_{current_datetime}"

    # Before uploading the file, make sure it contains the full conversation
    # This creates a fresh transcript with all messages to ensure completeness
    if os.path.exists(transcript_path):
        try:
            # Define Central Time (CT) timezone
            central_tz = pytz.timezone("America/Chicago")
            # Get current date and time in CT
            current_time = datetime.now(central_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
            
            with open(transcript_path, "w") as t:
                # Add metadata header with complete information
                t.write("=== INTERVIEW METADATA ===\n")
                # Determine API based on config.MODEL since OpenAI and Anthropic have different model naming conventions
                api_type = 'openai' if 'gpt' in config.MODEL.lower() else 'anthropic'
                t.write(f"API: {api_type}\n")
                t.write(f"Model: {config.MODEL}\n")
                t.write(f"Start Time (CT): {st.session_state.get('start_time', 'Unknown')}\n")
                t.write(f"End Time (CT): {current_time}\n")
                t.write(f"Username: {st.session_state.username}\n")
                t.write(f"UID: {st.session_state.get('response_id', 'None')}\n")  # Changed from ResponseID to UID
                t.write(f"Number of Responses: {len([m for m in st.session_state.messages if m['role'] == 'user'])}\n")
                t.write("========================\n\n")
                
                # Skip the system prompt (first message) when saving the transcript
                for message in st.session_state.messages:
                    if message.get('role') == 'system':
                        continue
                    t.write(f"{message['role']}: {message['content']}\n\n")
        except Exception as e:
            st.error(f"Error updating transcript before upload: {str(e)}")

    service = authenticate_google_drive()  # Authenticate Drive API

    try:
        transcript_id = upload_file_to_drive(service, transcript_path, os.path.basename(transcript_path))
        st.success(f"Files uploaded! Transcript ID: {transcript_id}")
    except Exception as e:
        st.error(f"Failed to upload files: {e}")

def save_interview_data(username, transcripts_directory, times_directory=None, file_name_addition_transcript="", file_name_addition_time=""):
    """Write interview data to disk."""
    # Ensure username is not None
    if username is None:
        central_tz = pytz.timezone("America/Chicago")
        current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d_%H-%M-%S")
        username = f"User_{current_datetime}"
        st.session_state.username = username
    
    # Set start time if not already set
    if 'interview_start_time' not in st.session_state:
        central_tz = pytz.timezone("America/Chicago")
        st.session_state.interview_start_time = datetime.now(central_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Ensure directories exist
    os.makedirs(transcripts_directory, exist_ok=True)
    if times_directory:
        os.makedirs(times_directory, exist_ok=True)
    
    # Create proper file paths
    transcript_file = os.path.join(transcripts_directory, f"{username}{file_name_addition_transcript}.txt")

    # Store chat transcript
    try:
        # Define Central Time (CT) timezone
        central_tz = pytz.timezone("America/Chicago")
        # Get current date and time in CT
        current_time = datetime.now(central_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        # Determine API type based on config.MODEL
        api_type = 'openai' if 'gpt' in config.MODEL.lower() else 'anthropic'
        
        with open(transcript_file, "w") as t:
            # Add metadata header with complete information
            t.write("=== INTERVIEW METADATA ===\n")
            t.write(f"API: {api_type}\n")
            t.write(f"Model: {config.MODEL}\n")
            t.write(f"Start Time (CT): {st.session_state.get('interview_start_time', 'Unknown')}\n")  # Fixed reference
            t.write(f"End Time (CT): {current_time}\n")
            t.write(f"Username: {username}\n")
            
            # Get UID from various possible names
            uid = (st.session_state.get('response_id') or 
                   st.session_state.get('qualtrics_uid') or 
                   st.session_state.get('qualtrics_response_id') or 
                   'None')
            t.write(f"UID: {uid}\n")
            
            t.write(f"Number of Responses: {len([m for m in st.session_state.messages if m['role'] == 'user'])}\n")
            t.write("========================\n\n")
            
            # Skip the system prompt when saving the transcript
            for message in st.session_state.messages:
                if message.get('role') == 'system':
                    continue
                t.write(f"{message['role']}: {message['content']}\n\n")
        return transcript_file
    except Exception as e:
        st.error(f"Error saving transcript: {str(e)}")
        return None

# Password screen for dashboard (note: only very basic authentication!)
# Based on https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso
def check_password():
    """Returns 'True' if the user has entered a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether username and password entered by the user are correct."""
        if st.session_state.username in st.secrets.passwords and hmac.compare_digest(
            st.session_state.password,
            st.secrets.passwords[st.session_state.username],
        ):
            st.session_state.password_correct = True

        else:
            st.session_state.password_correct = False

        del st.session_state.password  # don't store password in session state

    # Return True, username if password was already entered correctly before
    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    # Otherwise show login screen
    login_form()
    if "password_correct" in st.session_state:
        st.error("User or password incorrect")
    return False, st.session_state.username


def check_if_interview_completed(directory, username):
    """Check if interview transcript/time file exists."""
    if username is None:
        return False
    if username != "testaccount":
        return os.path.exists(os.path.join(directory, f"{username}.txt"))
    return False
