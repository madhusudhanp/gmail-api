import mysql.connector
import os
import traceback

from dotenv import load_dotenv
load_dotenv()

DB_CONFIG = {
    'user': os.getenv('MY_DB_USER'),
    'password': os.getenv('MY_DB_PASSWORD'),
    'host': os.getenv('MYSQL_HOST'),
    'database': os.getenv('MY_DB_NAME')
}


def fetch_emails_from_table(email_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    # cursor.execute('''SELECT emails.id,sender,subject,body,date,user_id 
    #                FROM emails join users on users.id = emails.user_id 
    #                where users.email_id="'+email_id+'"''')
    query = '''
        SELECT emails.id, sender, subject, body, date, user_id
        FROM emails
        JOIN users ON users.id = emails.user_id
        WHERE users.email_id = %s
    '''
    cursor.execute(query, (email_id,))
    emails = cursor.fetchall()
    cursor.close()
    conn.close()
    return emails

def store_emails(email_data):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        insert_query = '''
        INSERT INTO emails (id, sender, subject, body, date, user_id) 
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE sender = VALUES(sender), subject = VALUES(subject), body = VALUES(body), date = VALUES(date), user_id = VALUES(user_id) '''

        email_values = [
            (
                email['id'], email['from'], email['subject'], email['body'], email['date'], email['user_id']
            ) for email in email_data
        ]
        cursor.executemany(insert_query, email_values)

        conn.commit()
        cursor.close()
        conn.close()
        return {"status":True}
    except Exception:
        print("Exception in storing the email data: "+traceback.format_exc())
        return {"status":False,"message":traceback.format_exc()}


def create_emails_table():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS emails (
                      id VARCHAR(255) PRIMARY KEY,
                      sender VARCHAR(255),
                      subject TEXT,
                      body LONGTEXT,
                      date BIGINT,
                      user_id INT
                    )''')
    conn.commit()
    cursor.close()
    conn.close()

def create_user_table():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        email_id VARCHAR(255) NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    cursor.close()
    conn.close()

def fetch_user(email_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('SELECT id, email_id, password FROM users where email_id="'+email_id+'"' )
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    return user_data

def store_user(email_id, hashed_password):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    insert_query = '''
        INSERT INTO users (email_id, password, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
        '''
    cursor.execute(insert_query, (email_id, hashed_password))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id