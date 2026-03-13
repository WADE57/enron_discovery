import os
import email
from datetime import datetime
from core.models import Employee, Email
from django.core.management.base import BaseCommand

def parse_email_file(filepath):
    with open(filepath, 'rb') as f:
        msg = email.message_from_binary_file(f)
    
    # Extraction des informations
    from_addr = msg.get('from', '')
    to_addr = msg.get('to', '')
    subject = msg.get('subject', '')
    date_str = msg.get('date', '')
    
    # Extraction du corps
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    return {
        'from': from_addr,
        'to': to_addr,
        'subject': subject,
        'date': date_str,
        'body': body
    }