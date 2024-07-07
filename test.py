import pytest
import random
import string
import bcrypt
from unittest.mock import call
from authorise import generate_password, hash_password, verify_password, verify_credentials
from process_emails import is_valid_email,validate_rules,apply_rule
from base import store_user, store_emails

# Mock for fetch_user function used in verify_credentials
@pytest.fixture
def mock_fetch_user(mocker):
    return mocker.patch('authorise.fetch_user')

def test_generate_password():
    password = generate_password()
    assert len(password) == 8

def test_hash_password():
    password = 'testpassword'
    hashed_password = hash_password(password)
    assert bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def test_verify_password():
    password = 'testpassword'
    hashed_password = hash_password(password)
    assert verify_password(password, hashed_password)
    assert not verify_password('wrongpassword', hashed_password)

def test_verify_credentials(mock_fetch_user):
    password = 'testpassword'
    hashed_password = hash_password(password)
    mock_fetch_user.return_value = (1, 'user@example.com', hashed_password)
    
    assert verify_credentials('user@example.com', password)
    assert not verify_credentials('user@example.com', 'wrongpassword')
    mock_fetch_user.return_value = None
    assert not verify_credentials('nonexistent@example.com', password)

def test_is_valid_email():
    assert is_valid_email('test@example.com')
    assert not is_valid_email('invalid-email')

def test_validate_rules():
    rules = {
        "predicate": "All",
        "rules": [
            {
                "conditions": [
                    {"field": "from", "predicate": "equals", "value": "test@example.com"}
                ],
                "actions": ["mark_as_read"]
            }
        ]
    }
    assert validate_rules(rules) == {"status": True, "message": "Validation passed"}
    
    invalid_rules = {
        "predicate": "InvalidPredicate",
        "rules": [
            {
                "conditions": [
                    {"field": "from", "predicate": "equals", "value": "test@example.com"}
                ],
                "actions": ["mark_as_read"]
            }
        ]
    }
    assert validate_rules(invalid_rules) == {"status": False, "message": "Invalid predicate value. Must be 'All' or 'Any'."}

    invalid_rules = {
        "predicate": "All",
        "rules": [
            {
                "conditions": [
                    {"field": "date", "predicate": "less_than", "value": 1, "units": "day"}
                ],
                "actions": ["mark_as_read"]
            }
        ]
    }
    assert validate_rules(invalid_rules) == {"status": False, "message": "Date conditions must include 'units' with value 'days' or 'months'."}

    invalid_rules = {
        "predicate": "All",
        "rules": [
            {
                "conditions": [
                              ],
                "actions": ["mark_as_read"]
            }
        ]
    }
    assert validate_rules(invalid_rules) == {"status": False, "message": "Conditions cannot be empty."}
    invalid_rules = {
        "predicate": "All",
        "rules": [
            {
                "conditions": [
                    {"field": "from", "predicate": "contains", "value": "no-reply@accounts.google.com"}
                              ],
                "actions": []
            }
        ]
    }
    assert validate_rules(invalid_rules) == {"status": False, "message": "Actions cannot be empty."}

    invalid_rules = {
        "predicate": "All",
        "rules": [
            {
                "conditions": [
                    {"field": "date", "predicate": "less_than", "value": "1", "units": "days"}
                ],
                "actions": ["mark_as_read"]
            }
        ]
    }
    assert validate_rules(invalid_rules) == {"status": False, "message": "Date field value must be an integer."}

    invalid_rules = {
        "predicate": "All",
        "rules": [
            {
                "conditions": [
                    {"field": "message", "predicate": "contains", "value": 123}
                ],
                "actions": ["mark_as_read"]
            }
        ]
    }
    assert validate_rules(invalid_rules) == {"status": False, "message": "The value for field message must be a string."}

def test_apply_rule():
    email = {
        "from": "test@example.com",
        "subject": "Hello",
        "message": "This is a test",
        "date": 1609459200000
    }
    rule = {
        "conditions": [
            {"field": "from", "predicate": "equals", "value": "test@example.com"}
        ]
    }
    assert apply_rule(email, rule)
    
    rule = {
        "conditions": [
            {"field": "from", "predicate": "equals", "value": "wrong@example.com"}
        ]
    }
    assert not apply_rule(email, rule)

def test_store_user(mocker):
    # Mock database connection and cursor
    mock_conn = mocker.patch('mysql.connector.connect')
    mock_cursor = mock_conn.return_value.cursor.return_value
    
    # Mock execute method to simulate insertion
    mock_cursor.lastrowid = 1  # Simulate the returned user_id
    mock_execute = mock_cursor.execute
    
    # Call the function with mock data
    email_id = 'test@example.com'
    hashed_password = '$2b$12$R8Z2T5I1Tm2HhiBnV0f68e2YlFr3GumOnUqbsw2EG5jX1E3Jv6qDm'
    user_id = store_user(email_id, hashed_password)
    
    # Print out actual calls for debugging
    print("Actual calls to execute:", mock_execute.call_args_list)
    
    # Assert database interaction
    insert_query = 'INSERT INTO users (email_id, password, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())'
    insert_query = '''
        INSERT INTO users (email_id, password, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
        '''
    expected_call = call(insert_query, (email_id, hashed_password))
    
    # Print expected call for comparison
    print("Expected call:", expected_call)
    
    assert mock_execute.call_count == 1
    assert mock_execute.call_args == expected_call  # Check if the expected call matches the actual call
    
    # Assert return value
    assert user_id == 1  # Simulated user_id returned from cursor.lastrowid

def test_store_emails(mocker):
    # Mock database connection and cursor
    mock_conn = mocker.patch('mysql.connector.connect')
    mock_cursor = mock_conn.return_value.cursor.return_value

    # Mock data to be inserted
    email_data = [
        {
            'id': '1',
            'from': 'sender@example.com',
            'subject': 'Test Subject',
            'body': 'Test Body',
            'date': 1234567890,
            'user_id': 1
        },
        {
            'id': '2',
            'from': 'another@example.com',
            'subject': 'Another Subject',
            'body': 'Another Body',
            'date': 987654321,
            'user_id': 2
        }
    ]

    # Call the function with mock data
    result = store_emails(email_data)
    
    # Assert database interaction
    insert_query = '''
    INSERT INTO emails (id, sender, subject, body, date, user_id) 
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE sender = VALUES(sender), subject = VALUES(subject), body = VALUES(body), date = VALUES(date), user_id = VALUES(user_id) '''

    email_values = [
        (
            email['id'], email['from'], email['subject'], email['body'], email['date'], email['user_id']
        ) for email in email_data
    ]

    normalized_insert_query = normalize_sql(insert_query)

    # Print actual calls for debugging
    print("Actual calls to executemany:", mock_cursor.executemany.call_args_list)
    
    # Assert that executemany was called with the correct query and values
    actual_call_args = mock_cursor.executemany.call_args_list[0]
    actual_query = normalize_sql(actual_call_args[0][0])
    actual_values = actual_call_args[0][1]
    # Print expected and actual normalized queries for debugging
    print("Normalized expected query:", normalized_insert_query)
    print("Normalized actual query:", actual_query)
    
    assert actual_query == normalized_insert_query
    assert actual_values == email_values
    
    # Assert return value
    assert result == {"status": True}

def normalize_sql(sql):
    """Remove extra spaces and newlines from the SQL query for comparison."""
    return ' '.join(sql.split())