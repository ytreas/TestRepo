from odoo import http
from odoo.http import request,Response
import jwt
import datetime
from nepali_datetime import date as nepali_date
from odoo.exceptions import AccessDenied
import json
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")
REFRESH_TOKEN_EXPIRY = datetime.timedelta(
    days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRY_days", 30))
)
ACCESS_TOKEN_EXPIRY = datetime.timedelta(
    days=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRY_days", 7))
)

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
                user = payload['user_id']
                user_id = request.env['res.users'].sudo().browse(user)
                for group in user_id:
                    if group.name == 'Trade Admin Access':
                        role = 'admin'
                        break
                    elif group.name == 'Trade User Access':
                        role = 'user'
                        break
                    else:
                        role = 'none'
                return {
                    'status': 'success',
                    'data': {
                        'message': 'Refresh token valid',
                        'user_id': payload['user_id'],
                        'email': user_id.login,
                        'role': role,
                        'company_id': user_id.company_id.id
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

    
    def generate_new_access_token(self, user_id, email, role, company_id):
        payload = {
            'user_id': user_id,
            'exp': datetime.datetime.now(datetime.timezone.utc) + ACCESS_TOKEN_EXPIRY,
            'email': email,
            'role': role,
            'company_id': company_id
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    def authenticate_request(self, request):
        print("request", request)
        token = request.httprequest.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            bearer_token = token[len("Bearer "):]
        else:
            return {
                'status': 'fail',
                'data': {'message': 'Authorization header missing or malformed'}
            }, 400
        payload = jwt.decode(bearer_token, SECRET_KEY, algorithms=['HS256'])
        email = payload.get('email')
        role = payload.get('role')
        company_id = payload.get('company_id')
        user_id = payload.get('user_id')
        status = JWTAuth().check_jwt(bearer_token)
        # password = payload['password']
        # credentials = {
        #     'login': email,
        #     'type': 'password',
        #     'password': password
        # }
        # uid = request.env['res.users'].sudo().authenticate(
        #     request.db,
        #     credentials,
        #     user_agent_env=request.env
        # )
        # if not uid:
        #     return {'fail': 'Invalid credentials'}
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
            return {
                'status': 'success',
                'data': {'message': 'Access granted'},
                'role': role,
                'user_id': user_id,
                'company_id': company_id
            }, 200
