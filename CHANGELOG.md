# Changelog - Response ID Integration Fixes

## Version: Response ID Integration v2.0

### Summary of Changes

This update fixes critical issues with Qualtrics Response ID integration and implements custom speaker labels in interview transcripts.

### Issues Fixed

#### 1. **Username Generation Bug (interview.py)**
- **Problem**: Code was trying to access `st.session_state.get('qualtrics_uid', 'NoUID')` but the Response ID was stored as `'response_id'`
- **Result**: All usernames ended with `'NoUID'` regardless of actual Response ID
- **Fix**: Changed to `st.session_state.get('response_id', 'NoUID')`

#### 2. **Generic Speaker Labels (utils.py)**
- **Problem**: Transcripts used generic `user:` and `assistant:` labels
- **Result**: Difficult to identify specific participants in research analysis
- **Fix**: Implemented custom speaker labels using actual Response IDs

#### 3. **Missing Response ID Support**
- **Problem**: ResponseID parameter was captured but not properly utilized
- **Result**: Inconsistent data tracking between Qualtrics and transcripts
- **Fix**: Full Response ID integration in filenames, metadata, and speaker labels

### Files Changed

#### 1. `interview.py`
```python
# BEFORE (Line ~58)
uid_part = st.session_state.get('qualtrics_uid', 'NoUID')

# AFTER (Line ~58)
uid_part = st.session_state.get('response_id', 'NoUID')
if uid_part is None:
    uid_part = 'NoUID'
```

#### 2. `utils.py`
- Added `get_speaker_labels()` function for consistent label determination
- Updated `save_interview_data()` to use custom speaker labels
- Updated `save_interview_data_to_drive()` to use custom speaker labels
- Enhanced emergency transcript creation with custom labels

### New Features

#### Custom Speaker Labels
- **User messages**: Now labeled with actual Qualtrics Response ID (e.g., `R_2bKz8vXmPqT9nQ4L:`)
- **AI messages**: Now labeled with model name (`Claude:` or `ChatGPT:`)
- **Fallback protection**: If no Response ID captured, falls back to `user:`

#### Enhanced Metadata
- Response ID now appears in both filename and transcript metadata
- Consistent tracking between local files and Google Drive uploads
- Backward compatibility with existing data

### Example Output

#### Before Fix:
```
Filename: Claude_NoUID_2025-09-09_14-30-45.txt

user: Hello, I'm interested in learning about compound interest.
assistant: Hello! I'm excited to help you learn about compound interest...
```

#### After Fix:
```
Filename: Claude_R_2bKz8vXmPqT9nQ4L_2025-09-09_14-30-45.txt

R_2bKz8vXmPqT9nQ4L: Hello, I'm interested in learning about compound interest.
Claude: Hello! I'm excited to help you learn about compound interest...
```

### Supported URL Parameters

The system now properly captures Response IDs from any of these URL parameters:
- `uid` ← Works with your Qualtrics setup
- `UID` 
- `user_id`
- `userId`
- `participant_id`
- `ResponseID`

### Implementation Instructions

1. **Replace `interview.py`** with the fixed version
2. **Replace `utils.py`** with the updated version  
3. **Test with Qualtrics URL**: `https://aiqual2.onrender.com/?uid=test123`
4. **Verify filename includes Response ID**: Check that generated files have format `Claude_test123_YYYY-MM-DD_HH-MM-SS.txt`
5. **Verify transcript labels**: Confirm transcripts show Response ID as speaker label

### Research Benefits

1. **Direct Participant Identification**: No need to cross-reference metadata files
2. **Quality Assurance**: Easy to spot failed Response ID captures
3. **Automated Analysis Ready**: Can filter by specific Response IDs
4. **Model Distinction**: Clear separation between different AI models

### Testing Checklist

- [ ] Username includes Response ID when accessed via Qualtrics URL
- [ ] Transcript speaker labels show Response ID instead of "user"
- [ ] Google Drive uploads maintain custom labels
- [ ] Emergency transcripts use custom labels
- [ ] Fallback to "user" works when no Response ID present
- [ ] Metadata header includes correct Response ID

### Version History

- **v1.0**: Initial Qualtrics integration (had bugs)
- **v2.0**: Fixed Response ID bugs and added custom speaker labels