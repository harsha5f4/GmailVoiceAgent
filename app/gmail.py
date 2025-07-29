import os
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from datetime import datetime, timedelta


from app.nlp_processor import CATEGORY_KEYWORDS 


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

class GmailOperations:
    def __init__(self):
        self.service = self._authenticate_gmail()
        print("--- GmailOperations class initialized successfully! ---") 

    def _authenticate_gmail(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error loading credentials.json: {e}")
                    print("Please ensure credentials.json is in the same directory and is correctly formatted.")
                    print("You can download it from Google Cloud Console (APIs & Services -> Credentials -> OAuth Client ID -> Desktop app).")
                    exit() 
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return build('gmail', 'v1', credentials=creds)

    def list_emails(self, query='in:inbox', max_results=50):
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            emails_data = []
            if not messages:
                return []
            else:
                for message in messages:
                    msg = self.service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                    payload = msg['payload']
                    headers = payload.get('headers', [])
                    
                    
                    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
                    sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
                    
                    snippet = msg.get('snippet', 'No snippet available.')
                    
                    emails_data.append({
                        'id': message['id'],
                        'subject': subject,
                        'from': sender,
                        'snippet': snippet
                    })
                return emails_data
        except Exception as e:
            print(f"An error occurred while listing emails: {e}")
            
            return [] 

    def send_email(self, to, subject, body):
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            print(f"Email sent to {to} with subject '{subject}'")
            return True
        except Exception as e:
            print(f"An error occurred while sending email: {e}")
            return False 

    
    def list_emails_by_category(self, category, max_results=20): 
        
        print(f"DEBUG: list_emails_by_category received category: '{category}'") 
        category_keywords = CATEGORY_KEYWORDS.get(category.lower(), [])
        print(f"DEBUG: list_emails_by_category found keywords: {category_keywords}") 

        if not category_keywords:
            print(f"No keywords found for category: '{category}' in CATEGORY_KEYWORDS. Returning empty list.")
            return [] 

        positive_terms = []
        negative_terms = []

        for kw in category_keywords:
            if kw.startswith('-'):
                
                actual_kw = kw[1:] 
                if actual_kw.startswith('from:') or actual_kw.startswith('subject:'):
                    negative_terms.append(f"-{actual_kw}") 
                elif ' ' in actual_kw: 
                    negative_terms.append(f'-"{actual_kw}"')
                else:
                    negative_terms.append(f"-{actual_kw}") 
            else:
                
                if kw.startswith('from:') or kw.startswith('subject:'):
                    positive_terms.append(kw)
                elif ' ' in kw: 
                    positive_terms.append(f'"{kw}"')
                else:
                    positive_terms.append(kw)
        
        query_parts = []
        if positive_terms:
            query_parts.append(f"({' OR '.join(positive_terms)})")
        if negative_terms:
            query_parts.append(' '.join(negative_terms)) 

        
        final_query = f"{' AND '.join(query_parts)} in:inbox" if query_parts else "in:inbox"

        print(f"Gmail Query Used for category '{category}': {final_query}")

        return self.list_emails(query=final_query, max_results=max_results)