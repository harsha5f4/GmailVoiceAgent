from app.nlp_processor import process_command, nlp
from app.gmail import GmailOperations
import re


from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")

@app.errorhandler(500)
def handle_internal_server_error(e):
    print(f"Server Error (500): {e}")
    response_text = "An unexpected server error occurred. Please try again later."
    return response_text, 500

@app.errorhandler(404)
def handle_not_found_error(e):
    print(f"Not Found (404): {e}")
    response_text = "The page or resource you requested was not found."
    return response_text, 404

try:
    gmail_ops = GmailOperations()
except Exception as e:
    print(f"Error initializing GmailOperations: {e}")
    gmail_ops = None

active_conversations = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def test_connect():
    print('Client connected to WebSocket!', request.sid)
    emit('status', {'message': 'Connected to Gmail Voice Agent backend.'})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected from WebSocket.', request.sid)

    if request.sid in active_conversations:
        del active_conversations[request.sid] 

@socketio.on('process_command_event')
def handle_command(data):
    command = data.get('command', '').strip().lower()
    sid = request.sid

    if not command:
        response_text = "No command received. Please try speaking or typing a command."
        emit('agent_response', {'text': response_text, 'type': 'error'}, room=sid)
        return

    print(f"[{sid}] Received command: {command}")

    if gmail_ops is None:
        response_text = "Backend is not configured correctly for Gmail operations. Please check server logs."
        emit('agent_response', {'text': response_text, 'type': 'error'}, room=sid)
        return
    
    if "cancel" in command or "never mind" in command:
        if sid in active_conversations:
            del active_conversations[sid]
            response_text = "Okay, I've cancelled the current operation. What else can I help with?"
            emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid)
            return
        
    if sid in active_conversations:
        current_conversation = active_conversations[sid]
        intent_type = current_conversation['intent']

        if intent_type == "SEND_EMAIL":
            if current_conversation['step'] == 'waiting_for_to':
                match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', command)
                recipient = match.group(0) if match else command
                
                if recipient:
                    current_conversation['to'] = recipient
                    current_conversation['step'] = 'waiting_for_subject'
                    response_text = f"Okay, sending to {recipient}. What should be the subject?"
                else:
                    response_text = "I couldn't understand the recipient. Please tell me who this email is for?"
                emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid) 

            elif current_conversation['step'] == 'waiting_for_subject':
                subject = command.strip()
                if subject:
                    current_conversation['subject'] = subject
                    current_conversation['step'] = 'waiting_for_body'
                    response_text = f"Subject is '{subject}'. What should the body of the email say?"
                else:
                    response_text = "I couldn't get the subject. Please tell me the subject?"
                emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid) 

            elif current_conversation['step'] == 'waiting_for_body':
                body = command.strip()
                if body:
                    current_conversation['body'] = body
                    
                    try:
                        gmail_ops.send_email(current_conversation['to'], current_conversation['subject'], current_conversation['body'])
                        response_text = "Email sent successfully!"
                        del active_conversations[sid]
                    except Exception as e:
                        response_text = f"Failed to send email: {str(e)}"
                        del active_conversations[sid]
                else:
                    response_text = "I couldn't get the body. What should the body of the email say?"
                emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid) 
            return 
        
    nlp_result = process_command(command)

    response_text = ""
    emails_data = []
    
    num_emails_to_fetch_explicitly = None 
    MAX_FETCH_LIMIT = 100 

    match_num = re.search(r'(\d+)\s*.*?\s*(?:emails?|mails?)', command) 
    
    if match_num:
        try:
            specified_num = int(match_num.group(1))
            
            if specified_num == 0:
                num_emails_to_fetch_explicitly = 5 
                emit('agent_response', {'text': "Please specify a number greater than zero. Fetching default 5 emails for now.", 'type': 'info'}, room=sid)
            elif specified_num > MAX_FETCH_LIMIT:
                num_emails_to_fetch_explicitly = MAX_FETCH_LIMIT
                emit('agent_response', {'text': f"I can only fetch up to {MAX_FETCH_LIMIT} emails for specific requests. Fetching {num_emails_to_fetch_explicitly} emails.", 'type': 'info'}, room=sid)
            else:
                num_emails_to_fetch_explicitly = specified_num 
                
        except ValueError:
            pass 

    if nlp_result["type"] == "READ_EMAIL" or nlp_result["type"] == "SEARCH_EMAIL":
        try:
            if num_emails_to_fetch_explicitly is not None:
                emails = gmail_ops.list_emails(nlp_result["parameters"]["query"], max_results=num_emails_to_fetch_explicitly) 
            else:
                emails = gmail_ops.list_emails(nlp_result["parameters"]["query"])
            
            if emails:
                intro_message = f"Okay, here are the top {len(emails)} emails I found:" if num_emails_to_fetch_explicitly else f"Okay, here are some emails I found ({len(emails)} in total):"
                emit('agent_response', {'text': intro_message, 'type': 'speaking_intro'}, room=sid)
                
                for idx, email in enumerate(emails, 1):
                    email_snippet = email.get('snippet', 'No snippet available.')
                    email_subject = email.get('subject', 'No subject.')
                    email_from = email.get('from', 'Unknown Sender')

                    email_output = f"Email {idx} from {email_from}: {email_subject} — {email_snippet}"
                    emails_data.append(email_output)
                emit('email_snippets', {'snippets': emails_data}, room=sid)
            else:
                response_text = "No emails found matching your query."
                emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid)
        except Exception as e:
            response_text = f"Failed to retrieve emails: {str(e)}"
            emit('agent_response', {'text': response_text, 'type': 'error'}, room=sid)

    
    elif nlp_result["type"] == "UNDERSTAND":
        category = nlp_result["parameters"]["category"]
        try:
            
            if num_emails_to_fetch_explicitly is not None:
                emails = gmail_ops.list_emails_by_category(category, max_results=num_emails_to_fetch_explicitly)
            else:
                emails = gmail_ops.list_emails_by_category(category)

            if emails:
                intro_message = f"Okay, here are the top {len(emails)} {category} emails I found:" if num_emails_to_fetch_explicitly else f"Okay, here are some {category} emails I found ({len(emails)} in total):"
                emit('agent_response', {'text': intro_message, 'type': 'speaking_intro'}, room=sid)

                for idx, email in enumerate(emails, 1):
                    email_snippet = email.get('snippet', 'No snippet available.')
                    email_subject = email.get('subject', 'No subject.')
                    email_from = email.get('from', 'Unknown Sender')

                    email_output = f"Email {idx} from {email_from}: {email_subject} — {email_snippet}"
                    emails_data.append(email_output)
                emit('email_snippets', {'snippets': emails_data}, room=sid)
            else:
                response_text = f"No {category} emails found matching your query."
                emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid)
        except Exception as e:
            response_text = f"Failed to retrieve {category} emails: {str(e)}"
            emit('agent_response', {'text': response_text, 'type': 'error'}, room=sid)


    elif nlp_result["type"] == "SEND_EMAIL":
        active_conversations[sid] = {
            'intent': 'SEND_EMAIL',
            'to': nlp_result["parameters"].get("to"),
            'subject': nlp_result["parameters"].get("subject"),
            'body': nlp_result["parameters"].get("body"),
            'step': ''
        }
        
        if not active_conversations[sid]['to']:
            active_conversations[sid]['step'] = 'waiting_for_to'
            response_text = "Okay, I can help send an email. Who is the recipient?"
        elif not active_conversations[sid]['subject']:
            active_conversations[sid]['step'] = 'waiting_for_subject'
            response_text = f"Okay, sending to {active_conversations[sid]['to']}. What should be the subject?"
        elif not active_conversations[sid]['body']:
            active_conversations[sid]['step'] = 'waiting_for_body'
            response_text = f"Okay, sending to {active_conversations[sid]['to']} with subject '{active_conversations[sid]['subject']}'. What should the body of the email say?"
        else:
            try:
                gmail_ops.send_email(active_conversations[sid]['to'], active_conversations[sid]['subject'], active_conversations[sid]['body'])
                response_text = "Email sent successfully!"
                del active_conversations[sid]
            except Exception as e:
                response_text = f"Failed to send email: {str(e)}"
                del active_conversations[sid]
        
        emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid)

    else:
        response_text = nlp_result.get("message", "Sorry, I did not understand that. What else can I help with?")
        emit('agent_response', {'text': response_text, 'type': 'info'}, room=sid)

    print(f"[{sid}] Sending response to frontend: {response_text}")

if __name__ == "__main__":
    print("Starting Flask-SocketIO server...")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)