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
            # EXCEPT for the final summary/rating question which must stay intact
            if not any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                # Don't enforce if this is the summary + rating question
                # Check for key phrases that indicate we're in the conclusion
                is_conclusion = (
                    "To conclude" in message_interviewer or
                    "how well does" in message_interviewer.lower() or
                    "1 = poorly" in message_interviewer or
                    "scale of 1" in message_interviewer.lower()
                )
    
                if not is_conclusion:
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
                    
                    # ===== SHOW DEBRIEF AND AUTO-REDIRECT TO QUALTRICS =====
                    st.markdown("---")
                    st.success("✅ Interview Complete!")
                    
                    # IRB-required debrief language
                    st.markdown("""
                    <div style="line-height: 1.6; color: #333;">
                    <h1 style="color: #13294B; border-bottom: 4px solid #13294B; padding-bottom: 12px; margin-bottom: 25px; margin-top: 20px;">Debriefing</h1>

                    <p style="margin-bottom: 20px;"><strong>Research Participant:</strong></p>

                    <p style="margin-bottom: 20px;">During this study, you were asked to complete an online course about compound interest that included a goal-setting activity, educational content, interactive visualizations, and a reflection interview with an AI-enabled Chatbot about your learning experience. You were told that the purpose of the study was to test the effectiveness of visual media in teaching compound interest to improve financial education program design.</p>

                    <h2 style="color: #13294B; border-bottom: 3px solid #13294B; padding-bottom: 10px; margin-bottom: 15px; margin-top: 35px;">The Complete Study Design</h2>

                    <p style="margin-bottom: 15px;">This study tested how different approaches to goal-setting with visualizations affect learning about compound interest. You were randomly assigned to one of three groups:</p>

                    <ul style="margin: 0 0 30px 0; padding-left: 20px;">
                        <li style="margin-bottom: 10px;"><strong>Approach-focused group:</strong> Content emphasizing the benefits and growth potential of compound interest.</li>
                        <li style="margin-bottom: 10px;"><strong>Avoidance-focused group:</strong> Content highlighting potential losses from not understanding compound interest.</li>
                        <li style="margin-bottom: 10px;"><strong>Neutral group:</strong> Content focused on outcomes without emotional language.</li>
                    </ul>

                    <p style="margin-bottom: 30px;">All groups learned the same core compound interest concepts and saw the same visuals. The difference was how the textual information was presented in the goal-setting activity.</p>

                    <h2 style="color: #13294B; border-bottom: 3px solid #13294B; padding-bottom: 10px; margin-bottom: 15px; margin-top: 35px;">Why We Didn't Tell You This Initially</h2>

                    <p style="margin-bottom: 30px;">We did not provide complete information about the randomization and specific comparisons being made because knowing these details might have influenced how you interacted with the visualizations or how you responded during the reflection activity. For the research to provide valid insights about which approaches work best, it was important that you engaged with the materials without being influenced by knowledge of what was being compared.</p>

                    <h2 style="color: #13294B; border-bottom: 3px solid #13294B; padding-bottom: 10px; margin-bottom: 15px; margin-top: 35px;">Questions or Concerns</h2>

                    <p style="margin-bottom: 15px;">If you have any questions, concerns, or complaints about this study, or if you feel you have been harmed by this research, please contact:</p>

                    <p style="margin-bottom: 25px;">The Principal Investigator, H Chad Lane, at <a style="color: #1B75BB; text-decoration: none;" href="mailto:hclane@illinois.edu?subject=Viz%20in%20SRL%20Study%20-%20Debriefing%20Question">hclane@illinois.edu</a><br>
                    or the Study Contact, Andrea Pellegrini, at <a style="color: #1B75BB; text-decoration: none;" href="mailto:apelleg3@uillinois.edu?subject=Viz%20in%20SRL%20Study%20-%20Debriefing%20Question">apelleg3@uillinois.edu</a></p>

                    <h3 style="color: #13294B; margin: 30px 0 15px 0;">Reminder of Your Right to Withdraw</h3>

                    <div style="background: #E8F4F8; border-left: 4px solid #1B75BB; padding: 20px; border-radius: 4px; margin-bottom: 25px;">
                    <p style="margin-bottom: 15px;">We would like to remind you that your participation in this research is completely voluntary. It is up to you to decide whether or not to continue participating in this study. If you decide to withdraw from the research at this time, we will destroy any data collected about you during this study. The decision to withdraw from this research will involve no penalty or loss of any benefits to which you are otherwise entitled. This will not affect your relationship with the investigator.</p>

                    <p style="margin: 0;"><strong>If you would like to withdraw from this study, please let the investigator know by March 1, 2025.</strong> After this date, the data cleaning process should be complete, and any personal information connecting you to the data will be completely deleted making it difficult to remove data associated with your participation.</p>
                    </div>

                    <p style="margin-bottom: 15px;"><strong>Institutional Review Board:</strong> If you have any questions about your rights as a research subject, including concerns, complaints, or to offer input, you may call the Office for the Protection of Research Subjects (OPRS) at 217-333-2670 or e-mail OPRS at <a style="color: #1B75BB; text-decoration: none;" href="mailto:irb@illinois.edu">irb@illinois.edu</a>.</p>

                    <p style="margin-bottom: 25px;">If you would like to complete a brief survey to provide OPRS feedback about your experiences as a research participant, please complete the <a target="_blank" style="color: #1B75BB; text-decoration: none;" rel="noopener" href="https://redcap.healthinstitute.illinois.edu/surveys/?s=47X9T4NE4X">OPRS Online Feedback Form</a> or through a link on the OPRS website: <a target="_blank" style="color: #1B75BB; text-decoration: none;" rel="noopener" href="https://oprs.research.illinois.edu/">https://oprs.research.illinois.edu/</a>. You will have the option to provide feedback or concerns anonymously or you may provide your name and contact information for follow-up purposes.</p>

                    <p style="margin-bottom: 20px;">Again, please accept our appreciation for your participation in this study.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Now redirect back to Qualtrics to close the survey
                    return_url = st.session_state.get('return_url')
                    if return_url:
                        separator = '&' if '?' in return_url else '?'
                        completion_url = return_url + separator + "ChatbotCompleted=1"
                        
                        st.info("📋 Thank you for reading the debriefing. You will be redirected back to close the survey in 10 seconds...")
                        
                        # Auto-redirect using meta refresh
                        redirect_html = f'<meta http-equiv="refresh" content="10;url={completion_url}">'
                        st.markdown(redirect_html, unsafe_allow_html=True)
                        
                        # Manual link as backup
                        manual_link = f'<p style="text-align: center; margin-top: 10px;">If you are not automatically redirected, <a href="{completion_url}" style="color: #0066cc; font-weight: bold;">click here to complete the survey</a>.</p>'
                        st.markdown(manual_link, unsafe_allow_html=True)
                    else:
                        st.info("✅ You may now close this window. Your participation is complete.")
                        
                    # ===== END DEBRIEF AND AUTO-REDIRECT =====

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
