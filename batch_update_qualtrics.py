#!/usr/bin/env python3
"""
Batch Update Qualtrics - Delayed Background Job
================================================

This script runs on a schedule (e.g., daily) to:
1. Fetch completed interview transcripts from Google Drive
2. Extract Response IDs from transcript filenames
3. Update Qualtrics with ChatbotCompleted=1 for each Response ID
4. Optionally send debriefing emails

Run this HOURS after interviews complete to give Qualtrics time to process responses.
Recommended schedule: Daily at 2 AM or every 6 hours
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import re

# ==================== CONFIGURATION ====================

# Qualtrics Configuration (from environment variables or config file)
QUALTRICS_API_TOKEN = os.environ.get('QUALTRICS_API_TOKEN')
QUALTRICS_SURVEY_ID = os.environ.get('QUALTRICS_SURVEY_ID')
QUALTRICS_DATACENTER = os.environ.get('QUALTRICS_DATACENTER', 'illinois')

# Google Drive Configuration
GDRIVE_FOLDER_ID = os.environ.get('GDRIVE_FOLDER_ID')  # Your transcripts folder
GDRIVE_CREDENTIALS_JSON = os.environ.get('GDRIVE_CREDENTIALS_JSON')  # Service account JSON

# Processing Configuration
LOOKBACK_DAYS = 7  # How many days back to check for new transcripts
RATE_LIMIT_DELAY = 2  # Seconds between API calls to avoid rate limiting
MAX_RETRIES = 3  # Retry attempts for failed API calls
DRY_RUN = False  # Set to True to test without making actual API calls

# Email Configuration (optional)
SEND_EMAILS = os.environ.get('SEND_DEBRIEFING_EMAILS', 'false').lower() == 'true'
EMAIL_API_KEY = os.environ.get('EMAIL_API_KEY')  # SendGrid, Mailgun, etc.

# ==================== HELPER FUNCTIONS ====================

def log(message, level="INFO"):
    """Simple logging with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def extract_response_id_from_filename(filename):
    """
    Extract Response ID from transcript filename.
    Expected format: Claude_R_xxxxxxxxxxxxx_2024-01-07_12-34-56.txt
    """
    pattern = r'(R_[A-Za-z0-9]+)'
    match = re.search(pattern, filename)
    if match:
        return match.group(1)
    return None

def get_google_drive_service():
    """Initialize Google Drive API service"""
    try:
        if GDRIVE_CREDENTIALS_JSON:
            # Load credentials from environment variable (JSON string)
            creds_dict = json.loads(GDRIVE_CREDENTIALS_JSON)
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        else:
            # Load from file (for local testing)
            credentials = Credentials.from_service_account_file(
                'service-account-key.json',
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        
        service = build('drive', 'v3', credentials=credentials)
        log("✓ Connected to Google Drive API")
        return service
    except Exception as e:
        log(f"✗ Failed to connect to Google Drive: {str(e)}", "ERROR")
        return None

def get_recent_transcripts(service, days_back=7):
    """
    Fetch list of transcript files from Google Drive folder
    that were modified in the last N days.
    """
    try:
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_iso = cutoff_date.isoformat() + 'Z'
        
        # Query for files in the folder modified after cutoff
        query = f"'{GDRIVE_FOLDER_ID}' in parents and modifiedTime > '{cutoff_iso}' and trashed=false"
        
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="files(id, name, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        log(f"✓ Found {len(files)} transcripts from last {days_back} days")
        return files
    except Exception as e:
        log(f"✗ Failed to fetch transcripts: {str(e)}", "ERROR")
        return []

def update_qualtrics_response(response_id, retry_count=0):
    """
    Update a single Qualtrics response with ChatbotCompleted field.
    Returns: (success: bool, status: str)
    """
    url = f"https://{QUALTRICS_DATACENTER}.qualtrics.com/API/v3/surveys/{QUALTRICS_SURVEY_ID}/responses/{response_id}"
    headers = {
        "X-API-TOKEN": QUALTRICS_API_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "embeddedData": {
            "ChatbotCompleted": "1",
            "ChatbotCompletionTimestamp": datetime.now().isoformat()
        }
    }
    
    if DRY_RUN:
        log(f"[DRY RUN] Would update {response_id}", "DEBUG")
        return (True, "DRY_RUN")
    
    try:
        # First, verify the response exists (GET request)
        get_response = requests.get(url, headers={"X-API-TOKEN": QUALTRICS_API_TOKEN})
        
        if get_response.status_code == 404:
            log(f"  Response {response_id} not found in Qualtrics (404)", "WARN")
            return (False, "NOT_FOUND")
        elif get_response.status_code != 200:
            log(f"  Unexpected status {get_response.status_code} for {response_id}", "WARN")
            return (False, f"HTTP_{get_response.status_code}")
        
        # Response exists, now update it
        put_response = requests.put(url, headers=headers, json=payload)
        put_response.raise_for_status()
        
        log(f"  ✓ Successfully updated {response_id}")
        return (True, "SUCCESS")
        
    except requests.exceptions.RequestException as e:
        log(f"  ✗ API error for {response_id}: {str(e)}", "ERROR")
        
        # Retry logic
        if retry_count < MAX_RETRIES:
            retry_delay = RATE_LIMIT_DELAY * (2 ** retry_count)  # Exponential backoff
            log(f"  Retrying in {retry_delay}s... (attempt {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(retry_delay)
            return update_qualtrics_response(response_id, retry_count + 1)
        else:
            return (False, f"ERROR: {str(e)}")

def send_debriefing_email(response_id, email_address):
    """
    Send debriefing email to participant (optional).
    Implement this based on your email service (SendGrid, Mailgun, etc.)
    """
    if not SEND_EMAILS or not EMAIL_API_KEY:
        return
    
    # TODO: Implement email sending
    # This is a placeholder - customize based on your email service
    log(f"  [EMAIL] Would send debriefing to {email_address} for {response_id}", "DEBUG")
    pass

# ==================== MAIN PROCESSING ====================

def process_transcripts():
    """
    Main processing function:
    1. Connect to Google Drive
    2. Fetch recent transcripts
    3. Extract Response IDs
    4. Update Qualtrics for each ID
    """
    log("=" * 60)
    log("STARTING BATCH QUALTRICS UPDATE")
    log("=" * 60)
    
    # Validate configuration
    if not all([QUALTRICS_API_TOKEN, QUALTRICS_SURVEY_ID, QUALTRICS_DATACENTER]):
        log("✗ Missing Qualtrics credentials in environment variables", "ERROR")
        log("  Required: QUALTRICS_API_TOKEN, QUALTRICS_SURVEY_ID, QUALTRICS_DATACENTER", "ERROR")
        sys.exit(1)
    
    if not GDRIVE_FOLDER_ID:
        log("✗ Missing GDRIVE_FOLDER_ID in environment variables", "ERROR")
        sys.exit(1)
    
    log(f"Configuration:")
    log(f"  Survey ID: {QUALTRICS_SURVEY_ID}")
    log(f"  Datacenter: {QUALTRICS_DATACENTER}")
    log(f"  Lookback: {LOOKBACK_DAYS} days")
    log(f"  Dry Run: {DRY_RUN}")
    log("")
    
    # Connect to Google Drive
    drive_service = get_google_drive_service()
    if not drive_service:
        log("✗ Cannot proceed without Google Drive connection", "ERROR")
        sys.exit(1)
    
    # Fetch recent transcripts
    log(f"Fetching transcripts from last {LOOKBACK_DAYS} days...")
    transcripts = get_recent_transcripts(drive_service, LOOKBACK_DAYS)
    
    if not transcripts:
        log("No transcripts found. Exiting.")
        return
    
    # Extract Response IDs
    log("")
    log("Extracting Response IDs from filenames...")
    response_ids = []
    for file in transcripts:
        filename = file['name']
        response_id = extract_response_id_from_filename(filename)
        if response_id:
            response_ids.append({
                'response_id': response_id,
                'filename': filename,
                'modified_time': file.get('modifiedTime', 'unknown')
            })
            log(f"  Found: {response_id} in {filename}")
        else:
            log(f"  Skipped: {filename} (no Response ID found)", "WARN")
    
    log("")
    log(f"Found {len(response_ids)} Response IDs to process")
    
    if not response_ids:
        log("No Response IDs to process. Exiting.")
        return
    
    # Update Qualtrics for each Response ID
    log("")
    log("Updating Qualtrics responses...")
    log("-" * 60)
    
    stats = {
        'success': 0,
        'not_found': 0,
        'error': 0,
        'already_updated': 0
    }
    
    for idx, item in enumerate(response_ids, 1):
        response_id = item['response_id']
        log(f"[{idx}/{len(response_ids)}] Processing {response_id}...")
        
        success, status = update_qualtrics_response(response_id)
        
        if success:
            stats['success'] += 1
        elif status == 'NOT_FOUND':
            stats['not_found'] += 1
        else:
            stats['error'] += 1
        
        # Rate limiting
        if idx < len(response_ids):  # Don't sleep after last one
            time.sleep(RATE_LIMIT_DELAY)
    
    # Summary
    log("")
    log("=" * 60)
    log("BATCH UPDATE COMPLETE")
    log("=" * 60)
    log(f"Total processed: {len(response_ids)}")
    log(f"  ✓ Successfully updated: {stats['success']}")
    log(f"  ⚠ Not found in Qualtrics: {stats['not_found']}")
    log(f"  ✗ Errors: {stats['error']}")
    log("")
    
    if stats['not_found'] > 0:
        log("Note: 'Not found' responses may indicate:")
        log("  - Qualtrics still processing (try again later)")
        log("  - Response ID from test/preview (not saved)")
        log("  - Wrong Survey ID in configuration")
        log("  - Response was deleted")

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    try:
        process_transcripts()
    except KeyboardInterrupt:
        log("Interrupted by user", "WARN")
        sys.exit(0)
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
