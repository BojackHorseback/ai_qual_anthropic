#interview.py - Anthropic (Saving to Google Drive)

import streamlit as st
import time
import re
from utils import (
    check_password,
    check_if_interview_completed,
    save_interview_data,
    save_interview_data_to_drive,
)
import os
import config
import pytz

from datetime import datetime
from urllib.parse import urlparse, parse_qs
import anthropic

api = "anthropic"

# Set page title and icon
st.set_page_config(page_title="Interview - Anthropic", page_icon=config.AVATAR_INTERVIEWER)

# Define Central Time (CT) timezone
central_tz = pytz.timezone("America/Chicago")

# Function to extract UID from URL parameters
def get_qualtrics_uid():
    """Extract UID from URL parameters"""
    query_string = st.query_params
    uid = None
    
    # Try different parameter names that Qualtrics might use for UID
    params_to_check = ['uid', 'UID', 'user_id', 'userId', 'participant_id']
    
    for param in params_to_check:
        if param in query_string:
            uid = query_string[param]
            break
    
    return uid

# Function to ensure query parameters are captured
def ensure_query_params():
    """Ensure query parameters are captured from URL"""
    try:
        # Show JavaScript to capture query params
        st.components.v1.html("""
            <script>
                // Get URL parameters
                const urlParams = new URLSearchParams(window.location.search);
                const uid = urlParams.get('uid');
                
                // Set the UID in Streamlit query params
                if (uid) {
                    window.parent.postMessage({
                        type: 'streamlit:setQueryParam',
                        data: {uid: uid}
                    }, '*');
                }
            </script>
        """, height=0)
    except Exception:
        pass

# Ensure query parameters are captured
ensure_query_params()

# Get current date and time in CT
current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d_%H-%M-%S")

# Get UID from URL
uid = get_qualtrics_uid()

# Store the UID in session state
if uid:
    st.session_state.uid = uid

# Create username with UID instead of ResponseID
if "username" not in st.session_state or st.session_state.username is None:
    if uid:
        # Format: "Anthropic_UID_DateTimeStamp"
        st.session_state.username = f"Anthropic_{uid}_{current_datetime}"
    else:
        # Fallback if no UID
        st.session_state.username = f"Anthropic_NoUID_{current_datetime}"

    
# Create directories if they do not already exist
for directory in [config.TRANSCRIPTS_DIRECTORY, config.TIMES_DIRECTORY, config.BACKUPS_DIRECTORY]:
    os.makedirs(directory, exist_ok=True)

# Initialise session state
st.session_state.setdefault("interview_active", True)
st.session_state.setdefault("messages", [])


# Check if interview previously completed
interview_previously_completed = check_if_interview_completed(
    config.TRANSCRIPTS_DIRECTORY, st.session_state.username
    )

# If app started but interview was previously completed
if interview_previously_completed and not st.session_state.messages:
    st.session_state.interview_active = False
    completed_message = "Interview already completed."
    

# Add 'Quit' button to dashboard
col1, col2 = st.columns([0.85, 0.15])
with col2:
    if st.session_state.interview_active and st.button("Quit", help="End the interview."):
        st.session_state.interview_active = False
        st.session_state.messages.append({"role": "assistant", "content": "You have cancelled the interview."})
        try:
            transcript_path = save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY)
            if transcript_path:
                save_interview_data_to_drive(transcript_path)
        except Exception as e:
            st.error(f"Error saving data: {str(e)}")

# Display previous conversation (except system prompt)
for message in st.session_state.messages[1:]:
    avatar = config.AVATAR_INTERVIEWER if message["role"] == "assistant" else config.AVATAR_RESPONDENT
    if not any(code in message["content"] for code in config.CLOSING_MESSAGES.keys()):
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

# Load API client
client = anthropic.Anthropic(api_key=st.secrets["API_KEY"])
api_kwargs = {"system": config.SYSTEM_PROMPT}

# API kwargs
api_kwargs.update({
    "messages": st.session_state.messages,
    "model": config.MODEL,
    "max_tokens": config.MAX_OUTPUT_TOKENS,
})
if config.TEMPERATURE is not None:
    api_kwargs["temperature"] = config.TEMPERATURE

# Initialize first system message if history is empty
if not st.session_state.messages:
    st.session_state.messages.append({"role": "user", "content": "Hi"})
    with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
        message_placeholder = st.empty()
        message_interviewer = ""
        try:
            with client.messages.stream(**api_kwargs) as stream:
                for text_delta in stream.text_stream:
                    if text_delta:
                        message_interviewer += text_delta
                    message_placeholder.markdown(message_interviewer + "▌")
            message_placeholder.markdown(message_interviewer)
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            message_interviewer = "Sorry, there was an error connecting to the interview service. Please try again later."
            message_placeholder.markdown(message_interviewer)

    st.session_state.messages.append({"role": "assistant", "content": message_interviewer})

    # Store initial backup
    try:
        save_interview_data(
            username=st.session_state.username,
            transcripts_directory=config.BACKUPS_DIRECTORY,
        )
    except Exception as e:
        st.error(f"Error saving backup: {str(e)}")
        
# Main chat if interview is active
if st.session_state.interview_active:
    if message_respondent := st.chat_input("Your message here"):
        st.session_state.messages.append({"role": "user", "content": message_respondent})

        with st.chat_message("user", avatar=config.AVATAR_RESPONDENT):
            st.markdown(message_respondent)

        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            message_placeholder = st.empty()
            message_interviewer = ""

            try:
                with client.messages.stream(**api_kwargs) as stream:
                    for text_delta in stream.text_stream:
                        if text_delta:
                            message_interviewer += text_delta
                        if len(message_interviewer) > 5:
                            message_placeholder.markdown(message_interviewer + "▌")
                        if any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                            message_placeholder.empty()
                            break
            except Exception as e:
                st.error(f"API Error: {str(e)}")
                message_interviewer = "Sorry, there was an error. Your response was saved, but we couldn't generate a reply."
                
            if not any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                message_placeholder.markdown(message_interviewer)
                st.session_state.messages.append({"role": "assistant", "content": message_interviewer})

                try:
                    save_interview_data(
                        username=st.session_state.username,
                        transcripts_directory=config.BACKUPS_DIRECTORY,
                    )
                except Exception as e:
                    st.warning(f"Failed to save backup: {str(e)}")

            for code in config.CLOSING_MESSAGES.keys():
                if code in message_interviewer:
                    st.session_state.messages.append({"role": "assistant", "content": message_interviewer})
                    st.session_state.interview_active = False
                    st.markdown(config.CLOSING_MESSAGES[code])

                    final_transcript_stored = False
                    retries = 0
                    max_retries = 10
                    transcript_path = None
                    
                    while not final_transcript_stored and retries < max_retries:
                        try:
                            transcript_path = save_interview_data(
                                username=st.session_state.username,
                                transcripts_directory=config.TRANSCRIPTS_DIRECTORY,
                            )
                            final_transcript_stored = check_if_interview_completed(config.TRANSCRIPTS_DIRECTORY, st.session_state.username)
                        except Exception as e:
                            st.warning(f"Retry {retries+1}/{max_retries}: Error saving transcript - {str(e)}")
                        
                        time.sleep(0.1)
                        retries += 1

                    if retries == max_retries and not final_transcript_stored:
                        st.error("Error: Interview transcript could not be saved properly after multiple attempts!")
                        # Create emergency local transcript
                        emergency_file = f"emergency_transcript_{st.session_state.username}.txt"
                        try:
                            with open(emergency_file, "w") as t:
                                for message in st.session_state.messages:
                                    t.write(f"{message['role']}: {message['content']}\n")
                            transcript_path = emergency_file
                            st.success(f"Created emergency transcript: {emergency_file}")
                        except Exception as e:
                            st.error(f"Failed to create emergency transcript: {str(e)}")

                    if transcript_path:
                        try:
                            # Save to Google Drive without displaying any ID information
                            save_interview_data_to_drive(transcript_path)
                        except Exception as e:
                            st.error(f"Failed to upload to Google Drive: {str(e)}")
