import traceback
import logging

from flask import Flask, request
from flask_restx import Api, Resource, fields
from functools import wraps
from process_emails import process_emails, validate_rules
from authorise import authenticate_gmail, verify_credentials

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__)
api = Api(app, version='1.0', title='GMAIL API', description='A simple GMAIL API')

# Basic Authentication decorator
def basic_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        username = auth.username
        password = auth.password
        auth_details = verify_credentials(username,password)
        if not auth or not auth_details:
            return {'message': 'Unauthorized access'}, 401
        return f(*args, **kwargs)
    return decorated

ns = api.namespace('process_emails', description='Perform Email Operations')

rules_model = api.model('Rule', {
    'predicate': fields.String(required=True, description='The predicate type', enum=['All', 'Any']),
    'conditions': fields.List(fields.Nested(api.model('Condition', {
        'field': fields.String(required=True, description='The field to check', enum=['from', 'subject', 'body', 'date']),
        'predicate': fields.String(required=True, description='The predicate to use', enum=['contains', 'does_not_contain', 'equals', 'does_not_equal', 'less_than', 'greater_than']),
        'value': fields.Raw(required=True, description='The value to compare against'),
        'units': fields.String(description='The units of time for date comparison', enum=['days', 'months']),
    }))),
    'actions': fields.List(fields.String(required=True, description='The actions to perform', enum=['mark_as_read', 'mark_as_unread', 'move_message']))
})

@ns.route('/process')
class EmailProcessor(Resource):
    @ns.expect(rules_model)
    @ns.response(200, 'Emails processed successfully')
    @ns.response(500, 'Internal Server Error')
    @ns.doc(security='basicAuth')
    @basic_auth_required
    def post(self):
        """Process emails based on requested rules"""
        request_data = request.json

        validate_response = validate_rules(request_data)
        if validate_response.get("status") is False:
            return {'message': validate_response.get("message")}, 400
        try:
            auth_resp = authenticate_gmail()
            if auth_resp is None:
                message = "Invalid GMAIL Credentials"
                response = {
                    "status": 401,
                    "message": message
                }
                return response, 401
            result = process_emails(auth_resp,request_data)
            if result is None:
                return {'error': "Something went wrong.", 'output': "ERROR"}, 500
            return {'message': 'Emails processed successfully', 'output': result}, 200
        except Exception as e:
            return {'error': str(e), 'output': traceback.format_exc()}, 500

if __name__ == '__main__':
    app.run(debug=True)
