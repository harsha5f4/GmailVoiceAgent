
import os, re, json
from datetime import datetime, timedelta
import spacy
from spacy.matcher import Matcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity




try:
    nlp = spacy.load('en_core_web_sm')
except:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')

matcher = Matcher(nlp.vocab)


READ_PATTERNS = [
    [{'LOWER': {'IN': ['read', 'get', 'fetch', 'show', 'study', 'tell']}}, {'OP': '*'}, {'LOWER': {'IN': ['email', 'emails', 'messages', 'mails']}}],
    [{'LOWER': {'IN': ['read', 'get', 'fetch', 'show', 'study', 'tell']}}, {'OP': '*'}, {'LOWER': 'from'}, {'POS': 'PROPN', 'OP': '+'}],
]

SEARCH_PATTERNS = [
    [{'LOWER': {'IN': ['search', 'find', 'look', 'check']}}, {'OP': '*'}, {'LOWER': {'IN': ['email', 'emails', 'messages', 'mails']}}],
]

SEND_PATTERNS = [
    [{'LOWER': {'IN': ['send', 'write', 'compose']}}, {'OP': '*'}, {'LOWER': {'IN': ['email', 'emails', 'mail']}}],
]

for p in READ_PATTERNS: matcher.add("READ_EMAIL", [p])
for p in SEARCH_PATTERNS: matcher.add("SEARCH_EMAIL", [p])
for p in SEND_PATTERNS: matcher.add("SEND_EMAIL", [p])

INTENT_EXAMPLES = {
    "READ_EMAIL": [
        "read my latest emails", "get emails from Harsha", "fetch unread mails", "show emails about project",
        "tell me my sent mails", "read my spam folder"
    ],
    "SEARCH_EMAIL": [
        "search for emails from Alex", "find messages about deadline", "check emails with attachment",
        "look for emails received yesterday", "search drafts"
    ],
    "SEND_EMAIL": [
        "send an email to John about meeting", "write mail to Sarah saying I'm late", "compose an email"
    ],
}

vectorizer = TfidfVectorizer(lowercase=True)
intents, examples = [], []
for intent, intent_examples in INTENT_EXAMPLES.items():
    for ex in intent_examples:
        intents.append(intent)
        examples.append(ex)
vectorizer.fit(examples)


def classify_intent(text):
    doc = nlp(text)
    matches = matcher(doc)
    if matches:
        return nlp.vocab.strings[matches[0][0]]
    sim = cosine_similarity(vectorizer.transform([text]), vectorizer.transform(examples))[0]
    if max(sim) > 0.3:
        return intents[sim.argmax()]
    return "UNKNOWN"


def extract_sender(doc, text):
    m = re.search(r'from\s+([^\s]+)', text, re.IGNORECASE)
    return m.group(1).strip() if m else None

def extract_subject(doc, text):
    m = re.search(r'(about|regarding|subject)\s+(.*)', text, re.IGNORECASE)
    return m.group(2).strip() if m else None

def extract_content(doc, text):
    m = re.search(r'saying\s+(.*)', text, re.IGNORECASE)
    return m.group(1).strip() if m else None

def extract_labels_and_filters(text):
    labels = []
    q = []

    folders = ['sent', 'spam', 'draft', 'important', 'starred', 'unread']
    for f in folders:
        if f in text:
            if f in ['sent', 'draft', 'spam']:
                labels.append(f"in:{f}")
            else:
                labels.append(f"is:{f}")

    if "attachment" in text or "pdf" in text:
        q.append("has:attachment")

    if "yesterday" in text:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
        q.append(f"after:{yesterday}")

    if "today" in text:
        today = datetime.now().strftime("%Y/%m/%d")
        q.append(f"after:{today}")

    match = re.search(r'from\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', text)
    if match:
        month, year = match.groups()
        date_str = datetime.strptime(f"1 {month} {year}", "%d %B %Y").strftime("%Y/%m/%d")
        q.append(f"after:{date_str}")

    if "last week" in text:
        last_week = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")
        q.append(f"after:{last_week}")

    return " ".join(labels + q)
    


def process_command(command):
    doc, text = nlp(command.lower().strip()), command.lower().strip()
    intent = classify_intent(text)

    base_query = []

    folder_query = extract_labels_and_filters(text)
    if folder_query:
        base_query.append(folder_query)

    
    sender = extract_sender(doc, text)
    if sender:
        base_query.append(f"from:{sender}")

    subject = extract_subject(doc, text)
    if subject:
        base_query.append(f"subject:{subject}")

    full_query = " ".join(base_query).strip()

    if intent == "READ_EMAIL":
        return {"type": "READ_EMAIL", "parameters": {"query": full_query}}

    elif intent == "SEARCH_EMAIL":
        return {"type": "SEARCH_EMAIL", "parameters": {"query": full_query}}

    elif intent == "SEND_EMAIL":
        return {
            "type": "SEND_EMAIL",
            "parameters": {
                "to": sender if sender else None,
                "subject": subject if subject else None,
                "body": extract_content(doc, text) if extract_content(doc, text) else None
            }
        }

    return {"type": "UNKNOWN", "message": f"Could not understand: '{command}'"}