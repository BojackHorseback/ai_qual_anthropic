# Code for "Conversations at Scale: Robust AI-led Interviews with a Simple Open-Source Platform" - Claude Version

There are two options to explore the AI-led interviews discussed in the paper.

## Option 1: Online notebook

To try own ideas for interviews within minutes and without the need to install Python, see https://colab.research.google.com/drive/1sYl2BMiZACrOMlyASuT-bghCwS5FxHSZ (requires to obtain an API key)

## Option 2: Full platform

To install Python and set up the full interview platform locally (takes around 1h from scratch), see the following steps.

The interview platform is built using the library `streamlit` and the Anthropic API.

- Download miniconda from https://docs.anaconda.com/miniconda/miniconda-install/ and install it (skip if `conda` is already installed)
- Obtain an API key from https://www.anthropic.com/api
- Download this repository
- In the repository folder on your computer, create a file `/code/.streamlit/secrets.toml` and add your API key: `API_KEY = "your_anthropic_api_key_here"`
- Set up Google Drive credentials for file storage (see below)
- In the config.py, you can select a language model and adjust the interview outline
- In Terminal (Mac) or Anaconda Prompt (Windows), navigate to the folder `code` with `cd` (if unclear, briefly look up basic Linux command line syntax for navigating to folders)
- Once in the `code` folder, create the environment from the .yml file by writing `conda env create -f interviewsenv.yml` and confirming with enter (this installs Python and all libraries necessary to run the platform; only needs to be done once)
- Activate the environment with `conda activate interviews`
- Start the platform with `streamlit run interview.py`

## Setting up Google Drive for file storage

This version automatically saves interview transcripts to Google Drive. To set up:

1. Create a Google Cloud Project at https://console.cloud.google.com/
2. Enable the Google Drive API for your project
3. Create a service account and download the credentials JSON file
4. Copy the credentials file to `/etc/secrets/service-account.json` or update the path in `utils.py`
5. Create a folder in Google Drive and note its ID (the long string in the URL when viewing the folder)
6. Update the `FOLDER_ID` in `utils.py` with your Google Drive folder ID
7. Share the folder with the service account email (found in the credentials JSON)

## Qualtrics Integration

This version captures UID from the Qualtrics URL for tracking:

### How it works:
1. When participants click the interview link from Qualtrics, the UID is captured from the URL
2. The username format becomes: `Anthropic_UID_YYYY-MM-DD_HH-MM-SS`
3. All files are saved with metadata including the UID
4. At interview completion, files are saved without displaying any IDs

### URL Parameters:
The system checks for these parameter names:
- `uid`
- `UID`
- `user_id`
- `userId`
- `participant_id`

### File Output:
- **Filename**: `Anthropic_UID_YYYY-MM-DD_HH-MM-SS.txt`
- **File Content**: Includes metadata header with:
  - Username
  - UID
  - Save time (Central Time)
  - Full conversation transcript

## Paper and citation

The paper is available at https://ssrn.com/abstract=4974382 and can be cited with the following bibtex entry:

```
@article{geieckejaravel2024,
  title={Conversations at Scale: Robust AI-led Interviews with a Simple Open-Source Platform},
  author={Geiecke, Friedrich and Jaravel, Xavier},
  url={https://ssrn.com/abstract=4974382},
  year={2024}
}
```
