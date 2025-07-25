import os
import base64
from google.oauth2.credentials import Credentials 
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import pickle 

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

class GmailOperations:
    def __init__(self):
        creds = None
        
        if os.path.exists('token.pickle'): 
            with open('token.pickle', 'rb') as token: 
                creds = pickle.load(token) 

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token: 
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)

    def list_emails(self, query, max_results=50):
        result = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = result.get('messages', [])
        emails = []
        for msg in messages:
            txt = self.service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            headers = payload.get('headers', [])
            subject, sender = '', ''
            for d in headers:
                if d['name'] == 'From':
                    sender = d['value']
                if d['name'] == 'Subject':
                    subject = d['value']
            snippet = txt.get('snippet', '')
            emails.append({
                'from': sender,
                'subject': subject,
                'snippet': snippet
            })
        return emails

    def send_email(self, to, subject, body):
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        send_message = self.service.users().messages().send(userId="me", body=create_message).execute()
        return send_message