 # Gmail Voice Agent
Gmail Voice Agentt is a browser-based application that enables users to read, search, and send Gmail messages using voice or text commands. Built using Flask (Python) for backend and HTML/CSS/JS for frontend, the app integrates Google Gmail API and NLP (Natural Language Processing) to provide seamless voice-driven interaction.

# Features
-  **Voice and text input** from the browser (mic & send button supported)
-  **Natural Language Processing (NLP)** using spaCy, regex, and scikit-learn
-  **Gmail API Integration** (read, search, send emails securely)
-  **Real-time communication** using Flask routes (backend) and JS fetch calls (frontend)
-  **Voice Output** (responses spoken via browser’s TTS API)
-  **Command understanding**: Handles multiple intents like:
  - Read unread emails
  - Search emails from Harsha(sender)
  - Send email to Harsha(sender)..etc

# Tech Stack
- **Backend**: Python with Flask for handling routes and server logic
- **Frontend**: HTML, JavaScript, and CSS for interactive UI
- **NLP**: spaCy, scikit-learn, and regex for intent extraction and classification
- **Gmail Integration**: Gmail API with OAuth2 for secure email access (read/search/send)
- **Voice Input**: Web Speech API (browser-based speech recognition)
- **Voice Output**: Text-to-Speech using browser's Speech Synthesis API
- **Authentication**: Google’s InstalledAppFlow for user authorization

# Authentication Set up :
1. Enable Gmail API from Google Cloud Console
    -> Create Project-> Enable Gmail API -> Configure OAuth -> Download credentials.json
2. Download `credentials.json`
3. Place it in the project folder
4. First time run will trigger browser login
5. Token stored in `token.json` after first login

# Requirements
- Install the following before running:
    pip install flask
    pip install google-api-python-client
    pip install google-auth
    pip install google-auth-oauthlib
    pip install spacy
    pip install scikit-learn
    pip install pyttsx3

# How to Run 
- Run Flask server
    python app.py
- Open browser
    Visit http://localhost:5000
- Use mic or input box to issue commands like:

    "Search emails from dice"
    "Send email to Harsha"
    "Read top 10 mails"
    "Read linkedin mails"



