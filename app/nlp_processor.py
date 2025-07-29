import os, re, json
import spacy
from spacy.matcher import Matcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timedelta

try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')

matcher = Matcher(nlp.vocab)

CATEGORY_KEYWORDS = {
    'bank': [
        'HDFC', 'ICICI', 'SBI', 'Axis Bank', 'Kotak Mahindra', 'Yes Bank',
        'bank statement', 'transaction alert', 'credit card statement', 'debit card',
        'account balance', 'netbanking', 'mini statement', 'loan approval', 'fixed deposit',
        'passbook', 'fund transfer', 'payment confirmation', 'deposit', 'withdrawal', 'statement of account',
        'from:hdfcbank.com', 'from:icicibank.com', 'from:sbi.co.in', 'from:axisbank.com',
        '-recruitment', '-job', '-careers', '-hiring', '-PO', '-officer', '-apply', '-opening', '-opportunity', '-interview',
        '-from:lensa.com', '-from:jobalert@lensa.com', '-from:ratoonleaf.com', '-from:jobsincareer.com'
    ],
    'shopping': [
        'Amazon', 'Flipkart', 'Myntra', 'Meesho', 'Snapdeal', 'JioMart', 'Nykaa', 'Shopify', 'Paytm Mall', 'Ajio', 'Decathlon',
        'order confirmation', 'shipping update', 'delivery notification', 'e-commerce receipt', 'invoice for purchase',
        'return request', 'product received', 'your order has shipped', 'cart abandoned', 'purchase update',
        'product delivery', 'your order', 'thank you for your purchase', 'bill paid', 'payment successful',
        'from:amazon.in', 'from:amazon.com', 'from:flipkart.com', 'from:myntra.com', 'from:meesho.com',
        'from:nykaa.com', 'from:ajio.com', 'from:shopify.com',
        '-job', '-career', '-recruitment', '-hiring', '-interview', '-apply', '-position', '-opening', '-opportunity',
        '-resume', '-profile', '-data analyst', '-quality assurance', '-devops', '-engineer', '-consultant', '-manager',
        '-salary', '-work from home', '-full-time', '-part-time', '-urgent hiring', '-new job',
        '-from:lensa.com', '-from:jobalert@lensa.com', '-from:ratoonleaf.com', '-from:jobsincareer.com'
    ],
    'food': [
        'Zomato', 'Swiggy', 'Uber Eats', 'Domino\'s', 'KFC', 'Pizza Hut', 'McDonalds', 'Subway', 'Burger King', 'FoodPanda',
        'food order', 'food delivery', 'restaurant bill', 'menu update', 'takeaway order',
        'dineout reservation', 'eats order', 'bakery order', 'cake delivery', 'meal prep', 'coupon food',
        'from:zomato.com', 'from:swiggy.com', 'from:ubereats.com', 'from:dominos.com', 
        '-recruitment', '-job', '-careers', '-hiring', '-apply', '-jobsincareer.com'
    ],
    'travel': [
        'Indigo', 'MakeMyTrip', 'Goibibo', 'IRCTC', 'Vistara', 'Air India', 'SpiceJet', 'Priceline', 'Booking.com', 'Expedia', 'GoAir',
        'flight booking', 'hotel confirmation', 'train ticket', 'bus ticket', 'travel itinerary',
        'boarding pass', 'visa application', 'passport renewal', 'holiday package', 'tour confirmation', 'flight status',
        'from:goindigo.in', 'from:makemytrip.com', 'from:irctc.co.in', 'from:priceline.com', 'from:booking.com',
        '-job', '-career', '-recruitment', '-hiring', '-interview', '-apply', '-position', '-opening', '-opportunity',
        '-from:lensa.com', '-from:jobalert@lensa.com', '-from:ratoonleaf.com', '-from:jobsincareer.com',
        
        '-from:email.jcpenney.com', 
        '-from:jcpenney@email.jcpenney.com', 
        '-from:e.affirm.com' 
        
    ],
    'finance': [
        'electricity bill', 'water bill', 'loan statement', 'investment update', 'tax filing', 'salary slip',
        'fund transfer', 'EMI reminder', 'financial report', 'account statement', 'credit score',
        'mutual fund statement', 'insurance premium', 'policy renewal', 'payment confirmation', 'income tax return'
    ],
    
    
}

READ_PATTERNS = [
    [{'LOWER': {'IN': ['read', 'get', 'fetch', 'show', 'study', 'tell', 'see']}}, {'OP': '*'}, {'LOWER': {'IN': ['email', 'emails', 'messages', 'mails']}}],
    [{'LOWER': {'IN': ['read', 'get', 'fetch', 'show', 'study', 'tell', 'see']}}, {'OP': '*'}, {'LOWER': 'from'}, {'POS': 'PROPN', 'OP': '+'}],
]

SEARCH_PATTERNS = [
    [{'LOWER': {'IN': ['search', 'find', 'look', 'check']}}, {'OP': '*'}, {'LOWER': {'IN': ['email', 'emails', 'messages', 'mails']}}],
]

SEND_PATTERNS = [
    [{'LOWER': {'IN': ['send', 'write', 'compose']}}, {'OP': '*'}, {'LOWER': {'IN': ['email', 'emails', 'mail']}}],
]


UNDERSTAND_PATTERNS = [
    [{'LOWER': {'IN': ['show', 'get', 'find', 'search', 'check']}}, {'LOWER': 'my', 'OP': '?'}, {'LOWER': {'IN': list(CATEGORY_KEYWORDS.keys())}}, {'LOWER': {'IN': ['mails', 'emails', 'messages', 'receipts', 'statements', 'orders']}, 'OP': '?'}],
    [{'LOWER': {'IN': list(CATEGORY_KEYWORDS.keys())}}, {'LOWER': {'IN': ['mails', 'emails', 'messages', 'receipts', 'statements', 'orders']}}],
    [{'LOWER': {'IN': ['show', 'get', 'find', 'search', 'check']}}, {'LOWER': 'my', 'OP': '?'}, {'POS': 'PROPN', 'OP': '+'}, {'LOWER': {'IN': ['mails', 'emails', 'messages', 'orders']}, 'OP': '?'}],
    [{'POS': 'PROPN', 'OP': '+'}, {'LOWER': {'IN': ['mails', 'emails', 'messages', 'orders']}}]
]


for p in READ_PATTERNS: matcher.add("READ_EMAIL", [p])
for p in SEARCH_PATTERNS: matcher.add("SEARCH_EMAIL", [p])
for p in SEND_PATTERNS: matcher.add("SEND_EMAIL", [p])
for p in UNDERSTAND_PATTERNS: matcher.add("UNDERSTAND", [p])


INTENT_EXAMPLES = {
    "READ_EMAIL": [
        "read my latest emails", "get emails from Harsha", "fetch unread mails", "show emails about project",
        "tell me my sent mails", "read my spam folder", "see my mails", "read 5 emails", "show 10 mails"
    ],
    "SEARCH_EMAIL": [
        "search for emails from Alex", "find messages about deadline", "check emails with attachment",
        "look for emails", "search drafts", "find 7 emails about sales"
    ],
    "SEND_EMAIL": [
        "send an email to John about meeting", "write mail to Sarah saying I'm late", "compose an email"
    ],
    "UNDERSTAND": [
        "show my bank mails", "get shopping emails", "find food messages", "check my travel mails",
        "personal emails", "finance emails", "work emails", "show my bank emails",
        "show me my shopping receipts", "find my bank statements", "show me my food orders",
        "check Amazon mails", "show me my flight tickets", "find promotions", "show me bank alerts",
        "get Priceline mails", "show me my Flipkart orders", "what are my job alerts", "show me career emails",
        "show 5 shopping mails", "get 3 travel emails"
    ]
}

vectorizer = TfidfVectorizer(lowercase=True)
intents, examples = [], []
for intent, intent_examples_list in INTENT_EXAMPLES.items():
    for ex in intent_examples_list:
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


def extract_number_of_emails(text):
    doc = nlp(text)
    for token in doc:
        if token.like_num:
            try:
                return int(token.text)
            except ValueError:
                pass 
    return None



def detect_category_for_understand(text):
    text_lower = text.lower()
    
    for category_name in CATEGORY_KEYWORDS.keys():
        if category_name in text_lower or (category_name.replace('_', ' ') in text_lower and '_' in category_name):
            return category_name
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        positive_keywords = [kw for kw in keywords if not kw.startswith('-') and not kw.startswith('from:')]
    
        if any(kw.lower() in text_lower for kw in positive_keywords if len(kw) > 3 or kw in ['HDFC', 'SBI', 'KFC', 'IRCTC', 'Amazon', 'Flipkart', 'Priceline', 'Zomato', 'Swiggy', 'Lensa', 'Affirm', 'JCPenney']):
            return category
            
    return None

def extract_sender(text):
    m = re.search(r'(?:from|by)\s+([a-zA-Z0-9._%+-]+(?:[\s.]?[a-zA-Z0-9._%+-]+)*(?:\s*<[a-zA-Z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}>)?)', text, re.IGNORECASE)
    if m:
        email_match = re.search(r'<([a-zA-Z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})>', m.group(1))
        if email_match:
            return email_match.group(1)
        return m.group(1).strip()
    
    return None

def extract_subject(text):
    m = re.search(r'(?:about|regarding|subject is)\s+(.+)', text, re.IGNORECASE)
    return m.group(1).strip() if m else None

def extract_content(text):
    m = re.search(r'saying\s+(.+)', text, re.IGNORECASE)
    return m.group(1).strip() if m else None

def extract_labels_and_filters(text):
    labels = []
    q_parts = []
    
    folders = ['inbox', 'sent', 'spam', 'draft', 'important', 'starred', 'unread', 'trash']
    for f in folders:
        if f in text:
            if f in ['sent', 'draft', 'spam', 'trash']:
                labels.append(f"in:{f}")
            else:
                labels.append(f"is:{f}")

    if "attachment" in text or "pdf" in text or "with attachment" in text:
        q_parts.append("has:attachment")

    return " ".join(labels + q_parts)
    

def process_command(command):
    text = command.lower().strip()
    
    intent = classify_intent(text)
    
    parameters = {}
    
    num_emails = extract_number_of_emails(text)
    if num_emails:
        parameters['max_results'] = num_emails

    if intent == "UNDERSTAND":
        category = detect_category_for_understand(text)
        if category:
            parameters['category'] = category
            return {"type": "UNDERSTAND", "parameters": parameters}
        else:
            return {"type": "UNKNOWN", "message": "I recognized a category request, but couldn't identify the specific category. Can you be more precise? For example, 'show bank mails' or 'find shopping emails'."}

    elif intent == "READ_EMAIL" or intent == "SEARCH_EMAIL":
        base_query_parts = []
        
        folder_filter_query = extract_labels_and_filters(text)
        if folder_filter_query:
            base_query_parts.append(folder_filter_query)

        sender = extract_sender(text)
        if sender:
            if '@' in sender:
                base_query_parts.append(f"from:{sender}")
            else:
                base_query_parts.append(f"from:\"{sender}\"")
        
        subject = extract_subject(text)
        if subject:
            base_query_parts.append(f"subject:({subject})")

        if not base_query_parts:
            if 'max_results' not in parameters:
                base_query_parts.append(text) 
            else:
                pass 
            
        parameters["query"] = " ".join(base_query_parts).strip()
        
        return {"type": intent, "parameters": parameters}

    elif intent == "SEND_EMAIL":
        parameters["to"] = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        parameters["to"] = parameters["to"].group(0) if parameters["to"] else None
        parameters["subject"] = extract_subject(text)
        parameters["body"] = extract_content(text)
        
        return {"type": "SEND_EMAIL", "parameters": parameters}

    return {"type": "UNKNOWN", "message": f"Sorry, I did not understand '{command}'. What else can I help with?"}
