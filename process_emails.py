import json
from googleapiclient.discovery import build
import logging
import random
import traceback
import sys
import re
from base import fetch_emails_from_table
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from authorise import authenticate_gmail

# Configure logging
logging.basicConfig(level=logging.INFO)

def apply_rule(email, rule):
    for condition in rule['conditions']:
        field = condition['field']
        predicate = condition['predicate']
        value = condition['value']
        email_value = email.get(field)
        
        if field == 'date' and condition.get("units") is not None:
            if condition.get("units") not in ["days", "months"]:
                return False
            email_value = int(email_value)
            dt_object = datetime.fromtimestamp(email_value / 1000.0)
            current_time = datetime.now()
            difference = relativedelta(current_time, dt_object)
            if condition.get("units") == "days":
                converted_value = difference.days
                email_value = converted_value
            else:
                converted_value = difference.months
                email_value = converted_value
            value = int(value)

        if predicate == 'contains' and value not in email_value:
            return False
        if predicate == 'does_not_contain' and value in email_value:
            return False
        if predicate == 'equals' and value != email_value:
            return False
        if predicate == 'does_not_equal' and value == email_value:
            return False
        if predicate == 'less_than' and email_value >= value:
            return False
        if predicate == 'greater_than' and email_value <= value:
            return False
    return True

def process_rules(auth_resp, email, rules):
    try:
        return_rule_list = []
        for rule in rules['rules']:
            if rules['predicate'] == 'All' and all(apply_rule(email, rule) for rule in rules['rules']):
                return_rule_list.append(perform_actions(auth_resp, email, rule['actions']))
            elif rules['predicate'] == 'Any' and any(apply_rule(email, rule) for rule in rules['rules']):
                return_rule_list.append(perform_actions(auth_resp, email, rule['actions']))
        return return_rule_list
    except Exception:
        logging.error(f"Exception in process rules:  {traceback.format_exc()}")
        return []

def perform_actions(auth_resp, email, actions):
    service = build('gmail', 'v1', credentials=auth_resp)
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    filtered_labels = [label['name'] for label in labels 
                   if label['id'] not in ['TRASH', 'UNREAD', 'CHAT', 'SENT', 'SPAM', 'DRAFT', 'INBOX']]
    logging.info(f"Performing action on email from: {email['from']} subject: {email['subject']}")
    action_data = {
                "from_email": email["from"],
                "subject": email["subject"],
                "moved_action": [],
                "email_id":email['id']
            }
    for action in actions:
        if action == 'mark_as_read':
            service.users().messages().modify(userId='me', id=email['id'], body={'removeLabelIds': ['UNREAD']}).execute()
            action_data["moved_action"].append("READ")
            logging.info(f"Marked email from: {email['from']} with subject: {email['subject']} as read")
        if action == 'mark_as_unread':
            service.users().messages().modify(userId='me', id=email['id'], body={'addLabelIds': ['UNREAD']}).execute()
            action_data["moved_action"].append("UNREAD")
            logging.info(f"Marked email from: {email['from']} with subject: {email['subject']} as unread")
        if action == 'move_message':
            random_label = random.choice(filtered_labels)
            service.users().messages().modify(userId='me', id=email['id'], body={'addLabelIds': [random_label]}).execute()  # Modify as per your label ID
            action_data["moved_action"].append(random_label)
            logging.info(f"Moved email from: {email['from']} with subject: {email['subject']} to {random_label}" )
    return action_data

def process_emails(auth_resp, request_data):
    try:
        service = build('gmail', 'v1', credentials=auth_resp)
        email_id = service.users().getProfile(userId='me').execute()['emailAddress']
        emails = fetch_emails_from_table(email_id)
        return_data = []
        for email in emails:
            email_data = {
                'id': email[0],
                'from': email[1],
                'subject': email[2],
                'message': email[3],
                'date': email[4]
            }
            process_response = process_rules(auth_resp, email_data, request_data)
            if process_response and len(process_response) > 0 :
                return_data.append(process_response)
        return return_data
    except Exception:
        logging.error(f"Exception in process emails:  {traceback.format_exc()}")
        return None

def is_valid_email(email):
    # Simple regex for email validation
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def validate_rules(rules):
    try:
        allowed_fields = {'from', 'subject', 'message', 'date'}
        string_field_predicates = {'contains', 'does_not_contain', 'equals', 'does_not_equal'}
        date_field_predicates = {'less_than', 'greater_than'}
        allowed_actions = {'mark_as_read', 'move_message', 'mark_as_unread'}
        allowed_units = {'days', 'months'}

        # Check if predicate is either 'All' or 'Any'
        if rules.get("predicate") not in {"All", "Any"}:
            return {"status":False,"message":"Invalid predicate value. Must be 'All' or 'Any'."}

        rule_len = rules.get("rules", [])
        if len(rule_len) > 1:
            return {"status":False,"message":"Invalid rules in the Request. Please add only 1 set of rules."}

        for rule in rules.get("rules", []):
            conditions = rule.get("conditions", [])
            actions = rule.get("actions", [])

            # Check that conditions and actions are not empty
            if not conditions:
                return {"status":False,"message":"Conditions cannot be empty."}
            if not actions:
                return {"status":False,"message":"Actions cannot be empty."}

            for condition in conditions:
                field = condition.get("field")
                predicate = condition.get("predicate")
                value = condition.get("value")

                # Check field is valid
                if field not in allowed_fields:
                    return {"status":False,"message":f"Invalid field: {field}. Must be one of {allowed_fields}."}

                # Check predicate and value are present
                if not predicate:
                    return {"status":False,"message":f"Predicate cannot be empty for field {field}."}
                if value is None:  # value can be 0, so check for None specifically
                    return {"status":False,"message":f"Value cannot be empty for field {field}."}

                # Additional checks for date field
                if field == 'date':
                    if predicate not in date_field_predicates:
                        return {"status":False,"message":f"Invalid predicate for date field: {predicate}. Must be one of {date_field_predicates}."}
                    if not isinstance(value, int):
                        return {"status":False,"message":"Date field value must be an integer."}
                    if 'units' not in condition or condition['units'] not in allowed_units:
                        return {"status":False,"message":"Date conditions must include 'units' with value 'days' or 'months'."}

                # Additional checks for from field
                if field == 'from':
                    if predicate not in string_field_predicates:
                        return {"status":False,"message":f"Invalid predicate for field {field}: {predicate}. Must be one of {string_field_predicates}."}
                    if not isinstance(value, str) or not is_valid_email(value):
                        return {"status":False,"message":"The 'from' field must be a valid email address or a string."}

                # Additional checks for string fields
                if field in {'subject', 'message'}:
                    if predicate not in string_field_predicates:
                        return {"status":False,"message":f"Invalid predicate for field {field}: {predicate}. Must be one of {string_field_predicates}."}
                    if not isinstance(value, str):
                        return {"status":False,"message":f"The value for field {field} must be a string."}

            # Check that actions are valid
            for action in actions:
                if action not in allowed_actions:
                    return {"status":False,"message":f"Invalid action: {action}. Must be one of {allowed_actions}."}

        return {"status":True,"message":"Validation passed"}
    except Exception:
        return {"status":False,"message":"Validation Exception"}

def main():
    auth_resp = authenticate_gmail()
    if auth_resp is None:
        message = "Invalid Credentials"
        response = {
            "status": 401,
            "message": message
        }
        return response
    request_data = json.loads(sys.argv[1])
    return_data = process_emails(auth_resp,request_data)
    return return_data

if __name__ == '__main__':
    main()
