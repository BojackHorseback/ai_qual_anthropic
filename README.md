# AI-led Interview Platform for Financial Education Research

**Explanatory Mixed Methods Study of Visualizations in Online Compound Interest Education**

This platform conducts AI-led qualitative interviews about participants' experiences with visualizations in financial education. Built using Streamlit and Anthropic's Claude API.

## Study Overview

Participants complete an online compound interest course with embedded visualizations, then engage in an AI-led reflection interview about their learning experience. The interview focuses on:

- Learning experiences with visual aids in finance
- How visuals affect engagement and interest  
- How visuals support comprehension and self-regulation
- Personal preferences for different visual formats
- Practical applications and design insights

## Quick Setup

### Prerequisites
- Python 3.11
- Anthropic API key
- Google Drive API credentials (for data storage)

### Installation
1. Clone this repository
2. Create `/code/.streamlit/secrets.toml` and add: `API_KEY = "your_anthropic_api_key_here"`
3. Set up Google Drive credentials (see below)
4. Install dependencies: `conda env create -f interviewsenv.yml`
5. Activate environment: `conda activate interviews`
6. Run: `streamlit run interview.py`

## Google Drive Setup

1. Create a Google Cloud Project and enable Google Drive API
2. Create a service account and download credentials JSON
3. Place credentials at `/etc/secrets/service-account.json`
4. Update `FOLDER_ID` in `utils.py` with your Google Drive folder ID
5. Share the folder with the service account email

## Qualtrics Integration

The system captures Response IDs from Qualtrics URLs for participant tracking:

### URL Format
```
https://your-app.com/?uid=${e://Field/ResponseID}
```

### Data Output
- **Filename**: `Claude_R_2bKz8vXmPqT9nQ4L_2025-09-09_14-30-45.txt`
- **Speaker Labels**: Response ID replaces generic "user:" labels
- **Metadata**: Complete tracking information for research analysis

### Example Transcript
```
=== INTERVIEW METADATA ===
API: anthropic
Model: claude-3-5-sonnet-20240620
Username: Claude_R_2bKz8vXmPqT9nQ4L_2025-09-09_14-30-45
UID: R_2bKz8vXmPqT9nQ4L
========================

R_2bKz8vXmPqT9nQ4L: I found the bar charts really helpful for understanding compound growth.

Claude: What specifically about those bar charts made them effective for you?
```

## Interview Protocol

The AI interviewer follows a structured protocol designed for qualitative research:

- **Adaptive questioning**: One question at a time, builds on responses
- **Balanced coverage**: Ensures all research topics are addressed naturally
- **Non-directive approach**: Lets participants guide the conversation
- **Self-regulated learning focus**: Explores engagement, interest, and metacognition

## Research Context

This platform was developed for IRB-approved research (IRB25-0433) investigating how visualizations influence self-regulated learning in financial education. 

**Principal Investigator**: H. Chad Lane, University of Illinois Urbana-Champaign  
**Student Researcher**: Andrea Pellegrini

## Technical Details

- **Framework**: Streamlit
- **AI Model**: Anthropic Claude
- **Data Storage**: Google Drive (secure, encrypted)
- **Response ID Integration**: Full Qualtrics compatibility
- **Custom Speaker Labels**: Response IDs replace generic labels

## Attribution

This platform builds upon the open-source interview framework by Geiecke & Jaravel (2024), significantly modified for financial education research: