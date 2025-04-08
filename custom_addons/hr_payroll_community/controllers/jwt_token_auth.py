from odoo import http
from odoo.http import request,Response
import jwt
import datetime
from nepali_datetime import date as nepali_date
from odoo.exceptions import AccessDenied
import json

SECRET_KEY = 'top_secret_key_5456cs3gVdbDfdfhbSr8vdfdsm'
REFRESH_SECRET_KEY = 'top_secret_key_fghfgh5654dfgfdgfdfhbSr8vdfdsm'
ACCESS_TOKEN_EXPIRY = datetime.timedelta(hours=1) 
class JWTAuth(http.Controller):
    def check_jwt(self, token):
        if token:   
            try:
                print("here")
                payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                user = request.env['res.users'].sudo().browse(payload['user_id'])
                return {'success': 'Access granted', 'user_id': user.id}
            except jwt.ExpiredSignatureError:
                return {'fail': 'Token has expired'}   
            except jwt.InvalidTokenError:
                return {'fail': 'Invalid token'}
            except Exception as e:
                return {'fail': str(e)}
        else:
            return {'fail': 'Token Required'}

    def validate_refresh_token(self, refresh_token):
        if refresh_token:
            try:
                payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=['HS256'])
                return {
                    'status': 'success',
                    'data': {
                        'message': 'Refresh token valid',
                        'user_id': payload['user_id']
                    }
                }, 200
            except jwt.ExpiredSignatureError:
                return {
                    'status': 'fail',
                    'data': {
                        'message': 'Refresh token has expired'
                    }
                }, 401
            except jwt.InvalidTokenError:
                return {
                    'status': 'fail',
                    'data': {
                        'message': 'Invalid refresh token'
                    }
                }, 401
            except Exception as e:
                return {
                    'status': 'fail',
                    'data': {
                        'message': str(e)
                    }
                }, 500
        else:
            return {
                'status': 'fail',
                'data': {
                    'message': 'Refresh token required'
                }
            }, 400

    
    def generate_new_access_token(self, user_id):
        payload = {
            'user_id': user_id,
            'exp': datetime.datetime.now(datetime.timezone.utc) + ACCESS_TOKEN_EXPIRY  # Set the expiration time
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    def authenticate_request(self, request):
        print("request", request)
        token = request.httprequest.headers.get("Authorization")
        print("token",token)
        if token and token.startswith("Bearer "):
            bearer_token = token[len("Bearer "):]
        else:
            return {
                'status': 'fail',
                'data': {'message': 'Authorization header missing or malformed'}
            }, 400
        payload = jwt.decode(bearer_token, SECRET_KEY, algorithms=['HS256'])
        email = payload.get('email')
        password = payload.get('password')
        role = payload.get('role')
        status = JWTAuth().check_jwt(bearer_token)
        if status.get("success") != 'Access granted':
            if status.get('fail') == 'Token has expired':
                return {
                    'status': 'fail',
                    'data': {'message': 'Access token expired, Please generate a new token'}
                }, 401
            else:
                return {
                    'status': 'fail',
                    'data': {'message': 'Unauthorized access'}
                }, 400
        else:
            uid = request.session.authenticate(request.db, email, password)
            if not uid:
                return {
                    'status': 'fail',
                    'data': {'message': 'Invalid access token'}
                }, 400
            return {
                'status': 'success',
                'data': {'message': 'Access granted'},
                'role': role
            }, 200
# testing