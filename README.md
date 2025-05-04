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
4. Copy
