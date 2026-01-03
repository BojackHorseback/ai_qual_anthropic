# AI-led Interview Platform for Financial Education Research

**Qualitative Interviews on Visualizations in Online Compound Interest Education**

This platform conducts AI-led qualitative interviews about participants' experiences with visualizations in financial education.

## Study Overview

**IRB Protocol**: IRB25-1105 (Exempt, Category 3, approved 12/10/2025)

After completing an online educational intervention about compound interest, participants engage in an AI-led reflection interview to explore their learning experiences.

### Interview Topics
- Learning experiences with visual aids in personal finance
- How visualizations affect engagement and interest  
- How visualizations support comprehension and self-regulated learning
- Personal preferences for different visual formats
- Practical applications and design best practices

### Interview Protocol
The AI interviewer follows qualitative research best practices:
- Adaptive questioning based on participant responses
- Non-directive approach allowing participants to guide conversation
- One question at a time for natural dialogue flow
- Balanced coverage of research topics

## Technical Implementation

**Built with**:
- Streamlit (web interface)
- Anthropic Claude API (AI interviewer)
- Google Drive API (secure data storage)
- Qualtrics API
- Python 3.11

**AI Model**: claude-sonnet-4-20250514

## Qualtrics Integration

The platform integrates with Qualtrics to:
- Track participant Response IDs from survey URLs
- Link interview transcripts to survey data
- Automatically notify Qualtrics upon interview completion
- Trigger automated debriefing email workflows

Response IDs are captured from URL parameters (e.g., `?uid=${e://Field/ResponseID}`) and used as speaker labels in transcripts for data linking.

## Google Drive Integration

Interview transcripts are automatically uploaded to Google Drive for secure storage:
- Service account authentication for automated uploads
- Encrypted transfer and storage
- Organized folder structure for data management
- Weekly transfer to Box for long-term secure storage
- Access restricted to authorized research team only

Transcripts include metadata headers with:
- Response ID for data linking
- Interview timestamps
- Model information
- Qualtrics notification status

## Research Context

**Principal Investigator**: H. Chad Lane, University of Illinois Urbana-Champaign  
**Student Researcher**: Andrea Pellegrini  
**Dissertation Committee**: Robb Lindgren (Co-chair), Cherie Avent, Cynthia D'Angelo

This platform was developed to collect qualitative data about learners' experiences with visualizations in online financial education as part of an explanatory mixed methods dissertation study.

## Data Security

- IRB-compliant data handling procedures
- De-identification after data collection
- Service account credentials stored securely
- Manual review of transcripts to remove any inadvertent personally identifiable information
- Encrypted storage with restricted access

## Attribution

This platform builds upon the open-source interview framework by Geiecke and Jaravel (2024), modified for financial education research with Qualtrics integration and automated Google Drive storage.

**Citation (APA 7th):**

Geiecke, F., & Jaravel, X. (2024). Conversations at scale: Robust AI-led interviews with a simple open-source platform. *SSRN Electronic Journal*. https://doi.org/10.2139/ssrn.4974382

**Original Repository**: https://github.com/friedrichgeiecke/interviews

## Contact

**Andrea Pellegrini** (Student Researcher)  
Email: apelleg3@uillinois.edu  
University of Illinois Urbana-Champaign

**H. Chad Lane** (Principal Investigator)  
University of Illinois Urbana-Champaign

## Acknowledgments

Research supported by faculty funds from H. Chad Lane and Robb Lindgren, University of Illinois Urbana-Champaign.

---

*Last Updated: January 2026*  
*IRB Protocol: IRB25-1105*  
