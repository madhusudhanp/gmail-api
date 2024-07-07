import base64
import logging

from googleapiclient.discovery import build
from authorise import authenticate_gmail, generate_password, hash_password
from base import store_emails, create_emails_table, create_user_table, fetch_user, store_user


# Configure logging
logging.basicConfig(level=logging.INFO)

def fetch_emails(service, user_id):
    results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    messages = results.get('messages', [])
    email_data = []
    messages = messages[0:10]
    for msg in messages:
        msg_id = msg['id']
        msg = service.users().messages().get(userId='me', id=msg_id).execute()
        email = {
            'id': msg['id'],
            'from': '',
            'subject': '',
            'body': '',
            'date': msg['internalDate'],
            'user_id': user_id
        }
        for header in msg['payload']['headers']:
            if header['name'] == 'From':
                email['from'] = header['value']
            elif header['name'] == 'Subject':
                email['subject'] = header['value']
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    email['body'] = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        email_data.append(email)
        logging.info(f"Fetched email from: {email['from']} with subject: {email['subject']}")
    return email_data

def main():
    creds = authenticate_gmail()
    if creds is None:
        message = "Invalid Credentials"
        response = {
            "status": 401,
            "message": message
        }
        logging.info(f"Authentication failed: {message}")
        return response
    service = build('gmail', 'v1', credentials=creds)
    create_emails_table()
    create_user_table()
    email = service.users().getProfile(userId='me').execute()['emailAddress']
    user_data = fetch_user(email)
    user_id = None
    random_password = None
    if not user_data:
        random_password = generate_password()
        hashed_password = hash_password(random_password)
        user_id = store_user(email, hashed_password)
    else:
        user_id = user_data[0]
    if user_id is None:
        logging.info(f"Not able to create the user: {email}")
        return False
    email_data = fetch_emails(service, user_id)
    if len(email_data) > 0:
        result = store_emails(email_data)
        if result and result.get("status") is True:
            logging.info(f"Stored the email data in table from mail id: {str(email_data[0]['id'])} to mail id: {str(email_data[len(email_data)-1]['id'])}")
        else:
            logging.info(f"Could not store the email data in table. Error message: {str(result.get('message'))}")
    else:
        logging.info(f"No emails from the inbox")
    logging.info(f"Please store this email and password for processing the email: {email} password: {random_password}")
if __name__ == '__main__':
    main()
