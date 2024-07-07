#### 1. Create a Python virtual environment
```
python3 -m venv venv
```
#### 2. Install Dependencies
```
pip3 install -r requirements.txt
```
#### 3. Running the Flask Application
```
python3 app.py
```
**_NOTE:_** The Flask application will start running on http://localhost:5000.
#### 4. To fetch the emails from the gmail account and store it in table
```
python3 fetch_emails.py
```
#### 5. To process the emails which are stored in the table
```
Import the postman collection from the project files and make a call with the rules in the body.
```
#### Running Unit Tests
```
pytest test.py
```
#### Generate Code Coverage Report
```
pytest --cov --cov-report=html test.py
```
