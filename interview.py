#interview.py - Anthropic (Saving to Google Drive) - Response ID Integration + Qualtrics API Integration

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
import requests  # <<<< CHANGE 1: Added for Qualtrics API calls
import re  # <<<< NEW: For single question enforcement

from datetime import datetime
import anthropic
api = "anthropic"

# ===== NEW: SINGLE QUESTION ENFORCEMENT =====
def count_questions(text):
    """Count the number of questions in a text response"""
    question_marks = text.count('?')
    
    # Detect question patterns without question marks
    question_patterns = [
        r'\bcan you tell me\b',
        r'\bcan you describe\b',
        r'\bwhat (?:do|did|does|is|are|was|were)\b',
        r'\bhow (?:do|did|does|is|are|was|were)\b',
        r'\bwhy (?:do|did|does)\b',
        r'\bcould you\b',
        r'\bwould you\b'
    ]
    
    pattern_count = sum(1 for pattern in question_patterns if re.search(pattern, text.lower()))
    return max(question_marks, pattern_count)

def enforce_single_question(response_text):
    """Force response to contain only one question by truncating after first question"""
    num_questions = count_questions(response_text)
    
    if num_questions > 1:
        parts = response_text.split('?')
        if len(parts) > 1:
            return parts[0] + '?'
    
    return response_text
# ===== END SINGLE QUESTION ENFORCEMENT =====

# ===== CHANGE 2: QUALTRICS INTEGRATION START =====
# Load Qualtrics credentials from environment
QUALTRICS_API_TOKEN = os.environ.get('QUALTRICS_API_TOKEN')
QUALTRICS_SURVEY_ID = os.environ.get('QUALTRICS_SURVEY_ID')
QUALTRICS_DATACENTER = os.environ.get('QUALTRICS_DATACENTER')

# Define timezone for timestamps
central_tz = pytz.timezone("America/Chicago")

def mark_chatbot_complete(response_id):
    """
    Notify Qualtrics when interview completes.
    Logs all events but shows nothing to user.
    Check Render logs and transcript metadata for diagnostics.
    """
    # Log attempt
    print(f"[QUALTRICS] Attempting to mark completion for Response ID: {response_id}")
    
    # Check credentials (log but don't show user)
    if not all([QUALTRICS_API_TOKEN, QUALTRICS_SURVEY_ID, QUALTRICS_DATACENTER]):
        print("[QUALTRICS ERROR] Missing credentials in Render environment variables")
        print(f"[QUALTRICS DEBUG] Token exists: {bool(QUALTRICS_API_TOKEN)}")
        print(f"[QUALTRICS DEBUG] Survey ID exists: {bool(QUALTRICS_SURVEY_ID)}")
        print(f"[QUALTRICS DEBUG] Datacenter exists: {bool(QUALTRICS_DATACENTER)}")
        # Store failure in session state for transcript metadata
        st.session_state.qualtrics_status = "ERROR: Missing credentials"
        return False
    
    # Check Response ID (log but don't show user)
    if not response_id or response_id in ['NoUID', 'None', None]:
        print(f"[QUALTRICS ERROR] Invalid Response ID: {response_id}")
        st.session_state.qualtrics_status = f"ERROR: Invalid Response ID ({response_id})"
        return False
    
    # Attempt API call
    url = f"https://{QUALTRICS_DATACENTER}.qualtrics.com/API/v3/surveys/{QUALTRICS_SURVEY_ID}/responses/{response_id}"
    
    try:
        print(f"[QUALTRICS] Making API call to: {QUALTRICS_DATACENTER}.qualtrics.com")
        response = requests.put(
            url,
            headers={"X-API-TOKEN": QUALTRICS_API_TOKEN, "Content-Type": "application/json"},
            json={"embeddedData": {
                "ChatbotCompleted": "1",
                "ChatbotCompletionTimestamp": datetime.now(central_tz).isoformat()
            }}
        )
        response.raise_for_status()
        print(f"[QUALTRICS SUCCESS] ✓ Response ID {response_id} marked complete")
        print(f"[QUALTRICS DEBUG] API Response Code: {response.status_code}")
        # Store success in session state for transcript metadata
        st.session_state.qualtrics_status = "SUCCESS: Notified"
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[QUALTRICS ERROR] ✗ API call failed for Response ID {response_id}")
        print(f"[QUALTRICS DEBUG] Error details: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"[QUALTRICS DEBUG] Response body: {e.response.text}")
        # Store failure in session state for transcript metadata
        st.session_state.qualtrics_status = f"ERROR: {str(e)}"
        return False
# ===== CHANGE 2: QUALTRICS INTEGRATION END =====

# Capture UID from Qualtrics URL parameter - FIXED VERSION
try:
    # Get query parameters from the URL
    query_params = st.query_params
    
    # Check for various UID parameter names
    possible_uid_names = ["uid", "UID", "user_id", "userId", "participant_id", "ResponseID"]
    captured_response_id = None
    
    for param_name in possible_uid_names:
        uid_value = query_params.get(param_name)
        if uid_value is not None:
            # Handle case where query param might be a list
            if isinstance(uid_value, list) and len(uid_value) > 0:
                captured_response_id = uid_value[0]
            else:
                captured_response_id = str(uid_value)
            break
    
    # Store in session state with consistent naming
    st.session_state.response_id = captured_response_id
    
    # ===== NEW: CAPTURE RETURN URL =====
    return_url = query_params.get("return_url")
    if return_url is not None:
        st.session_state.return_url = return_url[0] if isinstance(return_url, list) else str(return_url)
    else:
        st.session_state.return_url = None
    # ===== END CAPTURE RETURN URL =====
    
except Exception as e:
    st.session_state.response_id = None
    st.session_state.return_url = None
    st.error(f"Error capturing Response ID: {str(e)}")

# Set page title and icon
st.set_page_config(page_title="Interview - Anthropic", page_icon=config.AVATAR_INTERVIEWER)

# Define Central Time (CT) timezone
# <<<< NOTE: Moved to Qualtrics section above (line 24) to avoid duplicate definition

# Get current date and time in CT
current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d_%H-%M-%S")

# Set the username with date and time - FIXED to properly use Response ID
if "username" not in st.session_state or st.session_state.username is None:
    model_prefix = "Claude"
    # FIXED: Use 'response_id' instead of 'qualtrics_uid'
    uid_part = st.session_state.get('response_id', 'NoUID')
    if uid_part is None:
        uid_part = 'NoUID'
    st.session_state.username = f"{model_prefix}_{uid_part}_{current_datetime}"
    st.session_state.interview_start_time = datetime.now(central_tz).strftime("%Y-%m-%d %H:%M:%S %Z")

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
            save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY)
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
            
            # ===== NEW: ENFORCE SINGLE QUESTION =====
            # Apply enforcement BEFORE displaying or saving the message
            if not any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                message_interviewer = enforce_single_question(message_interviewer)
            # ===== END ENFORCEMENT =====
                
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
                    display_message = config.CLOSING_MESSAGES[code]
                    st.session_state.messages.append({"role": "assistant", "content": display_message})
                    st.session_state.interview_active = False
                    st.markdown(display_message)
                    
                    # ===== NEW: AUTO-REDIRECT TO QUALTRICS =====
                    return_url = st.session_state.get('return_url')
                    if return_url:
                        # Build completion URL with ChatbotCompleted flag
                        separator = '&' if '?' in return_url else '?'
                        completion_url = f"{return_url}{separator}ChatbotCompleted=1"
                        
                        # Display redirect message and auto-redirect after 3 seconds
                        st.markdown("---")
                        st.success("🎉 Interview completed successfully!")
                        st.markdown(f"""
                        <p style="text-align: center; font-size: 16px; margin-top: 20px;">
                        <strong>Returning you to the survey...</strong><br>
                        You will be redirected in 3 seconds.
                        </p>
                        <meta http-equiv="refresh" content="3;url={completion_url}">
                        <p style="text-align: center; margin-top: 10px;">
                        If you are not redirected automatically, 
                        <a href="{completion_url}" style="color: #0066cc; font-weight: bold;">click here</a>.
                        </p>
                        """, unsafe_allow_html=True)
                    # ===== END AUTO-REDIRECT =====

                    # ===== CHANGE 3: NOTIFY QUALTRICS OF COMPLETION =====
                    # Silently attempt to notify Qualtrics (logs to Render, not visible to user)
                    response_id = st.session_state.get('response_id')
                    mark_chatbot_complete(response_id)  # Always call, even if None (for logging)
                    # ===== CHANGE 3: END =====

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
                        
                        # Create emergency local transcript with custom labels
                        emergency_file = f"emergency_transcript_{st.session_state.username}.txt"
                        try:
                            # Determine speaker labels
                            user_label = st.session_state.get('response_id', 'user')
                            if user_label is None or user_label == 'None':
                                user_label = 'user'
                            assistant_label = 'Claude'  # Since this is the Anthropic version
                            
                            with open(emergency_file, "w") as t:
                                for message in st.session_state.messages:
                                    if message.get('role') == 'system':
                                        continue
                                    
                                    # Use custom labels instead of generic roles
                                    if message['role'] == 'user':
                                        speaker_label = user_label
                                    elif message['role'] == 'assistant':
                                        speaker_label = assistant_label
                                    else:
                                        speaker_label = message['role']
                                    
                                    t.write(f"{speaker_label}: {message['content']}\n\n")
                            transcript_path = emergency_file
                            st.success(f"Created emergency transcript: {emergency_file}")
                        except Exception as e:
                            st.error(f"Failed to create emergency transcript: {str(e)}")

                    if transcript_path:
                        try:
                            save_interview_data_to_drive(transcript_path)
                        except Exception as e:
                            st.error(f"Failed to upload to Google Drive: {str(e)}")
