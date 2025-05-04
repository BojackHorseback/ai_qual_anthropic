#interview.py - OpenAI (Saving to Google Drive)

import streamlit as st
import time
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
from openai import OpenAI
api = "openai"

# Set page title and icon
st.set_page_config(page_title="Interview - OpenAI", page_icon=config.AVATAR_INTERVIEWER)

# Define Central Time (CT) timezone
central_tz = pytz.timezone("America/Chicago")

# Get current date and time in CT
current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d_%H-%M-%S")

# Get URL parameters
query_params = st.query_params

# Initialize session state for participant ID if not exists
if "participant_id" not in st.session_state:
    # Check for 'uid' parameter in URL
    participant_id = query_params.get("uid", None)
    if participant_id:
        # If array, take first value
        if isinstance(participant_id, list):
            participant_id = participant_id[0]
        st.session_state.participant_id = participant_id
    else:
        st.session_state.participant_id = None

# Set the username with date and time + participant ID if available
if "username" not in st.session_state or st.session_state.username is None:
    if st.session_state.participant_id:
        st.session_state.username = f"OpenAI_{current_datetime}_UID_{st.session_state.participant_id}"
    else:
        st.session_state.username = f"OpenAI_{current_datetime}"

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
if api == "openai":
    client = OpenAI(api_key=st.secrets["API_KEY"])
    api_kwargs = {"stream": True}
elif api == "anthropic":
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
    if api == "openai":
        st.session_state.messages.append({"role": "system", "content": config.SYSTEM_PROMPT})
        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            try:
                stream = client.chat.completions.create(**api_kwargs)
                message_interviewer = st.write_stream(stream)
            except Exception as e:
                st.error(f"API Error: {str(e)}")
                message_interviewer = "Sorry, there was an error connecting to the interview service. Please try again later."

    elif api == "anthropic":
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

    # Store initial backup - no need to save or upload yet as there's no conversation
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
                if api == "openai":
                    stream = client.chat.completions.create(**api_kwargs)
                    for message in stream:
                        text_delta = message.choices[0].delta.content
                        if text_delta:
                            message_interviewer += text_delta
                        if len(message_interviewer) > 5:
                            message_placeholder.markdown(message_interviewer + "▌")
                        if any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                            message_placeholder.empty()
                            break

                elif api == "anthropic":
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
                    # Save a backup after each message
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
                    
                    # Display generic closing message without participant ID
                    st.markdown(config.CLOSING_MESSAGES[code])
                    
                    # Record completion status without displaying to participant
                    if st.session_state.participant_id:
                        st.session_state.messages.append({"role": "system", "content": f"Interview completed for Participant ID: {st.session_state.participant_id}"})

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
                            # Double check the transcript was actually written
                            if os.path.exists(transcript_path) and os.path.getsize(transcript_path) > 0:
                                final_transcript_stored = True
                            else:
                                final_transcript_stored = False
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
                                # Skip the system prompt when saving, but include the final participant ID
                                for message in st.session_state.messages[1:]:
                                    t.write(f"{message['role']}: {message['content']}\n\n")
                            transcript_path = emergency_file
                            st.success(f"Created emergency transcript: {emergency_file}")
                        except Exception as e:
                            st.error(f"Failed to create emergency transcript: {str(e)}")

                    if transcript_path:
                        try:
                            # Debug output to check file content before upload
                            with open(transcript_path, "r") as f:
                                file_content = f.read()
                                if len(file_content.strip()) < 10:  # Check if file is practically empty
                                    st.warning(f"Warning: Transcript file appears to be nearly empty before upload!")
                                    
                                    # Try to write the file again with full content
                                    with open(transcript_path, "w") as t:
                                        for message in st.session_state.messages[1:]:
                                            t.write(f"{message['role']}: {message['content']}\n\n")
                            
                            # Now upload to Google Drive
                            save_interview_data_to_drive(transcript_path)
                        except Exception as e:
                            st.error(f"Failed to upload to Google Drive: {str(e)}")
