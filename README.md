#### 1. Create a Python virtual environment
```
python3 -m venv venv
```
#### 2. Install Dependencies
```
pip3 install -r requirements.txt
```
#### 3. Create a database and add the database name, username, password and host in the .env
```
CREATE DATABASE gmail_api_project; 
MY_DB_USER=''
MY_DB_PASSWORD=''
MY_DB_NAME='gmail_api_project'
MYSQL_HOST='localhost'
```
#### 4. Running the Flask Application
```
python3 app.py
```
**_NOTE:_** The Flask application will start running on http://localhost:5000.
#### 5. To fetch the emails from the gmail account and store it in table
```
python3 fetch_emails.py
```
#### 6. To process the emails which are stored in the table
```
Import the postman collection from the project files and make a call with the rules in the body.
Add the username and password in the Authorization which you will get in the response of step 4.
```
#### Running Unit Tests
```
pytest test.py
```
#### Generate Code Coverage Report
```
pytest --cov -cov-report=html test.py
```
