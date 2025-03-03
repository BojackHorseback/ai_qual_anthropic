import streamlit as st
import time
from utils import (
    check_password,
    check_if_interview_completed,
    save_interview_data,
)
import os
import config

# Load API library
if "gpt" in config.MODEL.lower():
    api = "openai"
    from openai import OpenAI
elif "claude" in config.MODEL.lower():
    api = "anthropic"
    import anthropic
else:
    raise ValueError("Model does not contain 'gpt' or 'claude'; unable to determine API.")

# Set page title and icon
st.set_page_config(page_title="Interview", page_icon=config.AVATAR_INTERVIEWER)

# Check if usernames and logins are enabled
if config.LOGINS:
    pwd_correct, username = check_password()
    if not pwd_correct:
        st.stop()
    else:
        st.session_state.username = username  # Set username after authentication
else:
    st.session_state.username = "testaccount"

# Ensure the username is initialized
if "username" not in st.session_state:
    st.session_state.username = "default_user"

# Create necessary directories
os.makedirs(config.TRANSCRIPTS_DIRECTORY, exist_ok=True)

# Initialize session state
st.session_state.setdefault("interview_active", True)
st.session_state.setdefault("messages", [])

# Store start time in session state
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

# Check if interview previously completed
if check_if_interview_completed(config.TRANSCRIPTS_DIRECTORY, st.session_state.username):
    st.session_state.interview_active = False
    st.markdown("Interview already completed.")

# Add 'Quit' button to dashboard
col1, col2 = st.columns([0.85, 0.15])
with col2:
    if st.session_state.interview_active and st.button("Quit", help="End the interview."):
        st.session_state.interview_active = False
        st.session_state.messages.append({"role": "assistant", "content": "You have cancelled the interview."})
        save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY, st.session_state.messages)

# Display previous conversation
for message in st.session_state.messages[1:]:
    avatar = config.AVATAR_INTERVIEWER if message["role"] == "assistant" else config.AVATAR_RESPONDENT
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Load API client
if api == "openai":
    client = OpenAI(api_key=st.secrets["API_KEY"])
    api_kwargs = {"stream": True}
elif api == "anthropic":
    client = anthropic.Anthropic(api_key=st.secrets["API_KEY"])
    api_kwargs = {"system": config.SYSTEM_PROMPT}

api_kwargs.update({
    "messages": st.session_state.messages,
    "model": config.MODEL,
    "max_tokens": config.MAX_OUTPUT_TOKENS,
})
if config.TEMPERATURE is not None:
    api_kwargs["temperature"] = config.TEMPERATURE

# Initialize first system message if history is empty
if not st.session_state.messages:
    st.session_state.messages.append({"role": "system", "content": config.SYSTEM_PROMPT})
    
    with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
        stream = client.chat.completions.create(**api_kwargs)
        message_interviewer = st.write_stream(stream)
    
    st.session_state.messages.append({"role": "assistant", "content": message_interviewer})

# Main chat if interview is active
if st.session_state.interview_active:
    if message_respondent := st.chat_input("Your message here"):
        st.session_state.messages.append({"role": "user", "content": message_respondent})
        
        with st.chat_message("user", avatar=config.AVATAR_RESPONDENT):
            st.markdown(message_respondent)
        
        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            message_placeholder = st.empty()
            message_interviewer = ""
            
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
            
            if not any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                message_placeholder.markdown(message_interviewer)
                st.session_state.messages.append({"role": "assistant", "content": message_interviewer})

        # Save interview transcript and upload to Google Drive
        save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY, st.session_state.messages)
        
        for code in config.CLOSING_MESSAGES.keys():
            if code in message_interviewer:
                st.session_state.messages.append({"role": "assistant", "content": message_interviewer})
                st.session_state.interview_active = False
                st.markdown(config.CLOSING_MESSAGES[code])
                save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY, st.session_state.messages)
