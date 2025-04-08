from odoo.http import request,Response
from odoo import http,api,SUPERUSER_ID
from odoo.exceptions import AccessDenied
import datetime
import jwt
from odoo.exceptions import AccessError
from datetime import date
import logging
import json
from werkzeug.exceptions import BadRequest
import datetime

_logger = logging.getLogger(__name__)
from . import jwt_token_auth

SECRET_KEY = 'top_secret_key_5456cs3gVdbDfdfhbSr8vdfdsm'
REFRESH_SECRET_KEY = 'top_secret_key_fghfgh5654dfgfdgfdfhbSr8vdfdsm'
REFRESH_TOKEN_EXPIRY = datetime.timedelta(days=30)
ACCESS_TOKEN_EXPIRY = datetime.timedelta(days=7) 

class AuthAPI(http.Controller):

    def handle_error(self, exception):
        if isinstance(exception, AccessError):
            return http.Response(
                status=403,
                response=json.dumps({"status": "fail", "message": "Access Denied"}),
                content_type="application/json"
            )

    @http.route('/payroll/api/login', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def login(self, **kw):

        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)
        
        email = json_data.get('email')
        password = json_data.get('password')

        try:
            uid = request.session.authenticate(request.db, email, password)
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                for group in user.groups_id:
                    if group.name == 'Trade Admin Access':
                        role = 'admin'
                        break
                    elif group.name == 'Trade User Access':
                        role = 'user'
                        break
                    else:
                        role = 'none'
                        
                # Generate access token
                access_payload = {
                    'user_id': user.id,
                    'exp': datetime.datetime.now(datetime.timezone.utc) + ACCESS_TOKEN_EXPIRY,
                    'email': email,
                    'password': password,
                    'role': role
                }
                access_token = jwt.encode(access_payload, SECRET_KEY, algorithm='HS256')

                # Generate refresh token
                refresh_payload = {
                    'user_id': user.id,
                    'exp': datetime.datetime.now(datetime.timezone.utc) + REFRESH_TOKEN_EXPIRY
                }
                refresh_token = jwt.encode(refresh_payload, REFRESH_SECRET_KEY, algorithm='HS256')


                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': {
                            'access_token': access_token,
                            'role': role,
                            # 'refresh_token': refresh_token
                        }
                    }),
                    headers=[
                        ('Content-Type', 'application/json')
                        ],
                    status=200
                )
        
        except AccessDenied:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': 'Invalid Credentials'
                    }
                }),
                headers=[   
                    ('Content-Type', 'application/json')],
                status=400
            )
    
    @http.route('/payroll/api/refresh_token', type='http',auth='public',cors="*", csrf=False, methods=['GET'])
    def refresh_token(self, **kw):
        try:
            # Get the refresh token from the request headers
            refresh_token = request.httprequest.headers.get("Refresh-Token")
            print("here", refresh_token)
            
            if not refresh_token:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Refresh token required"
                        }
                    }),
                    content_type="application/json"
                )

            # Validate the refresh token
            refresh_status, status_code = jwt_token_auth.JWTAuth.validate_refresh_token(self, refresh_token)

            if refresh_status['status'] == 'success':
                user_id = refresh_status['data']['user_id']
                # Generate a new access token
                new_access_token = jwt_token_auth.JWTAuth.generate_new_access_token(self, user_id)

                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': {
                            'access_token': new_access_token
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )
            else:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': refresh_status['data']['message']
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

        except Exception as e:
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                content_type="application/json"
            )


    @http.route('/payroll/api/get_user_details', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def get_user_details(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )
            
            token = request.httprequest.headers.get("Authorization")       
            if token and token.startswith("Bearer "):
                bearer_token = token[len("Bearer "):]
            else:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "No Authorization token provided"
                        }
                    }),
                    content_type="application/json"
                )
            payload = jwt.decode(bearer_token, SECRET_KEY, algorithms=['HS256'])
            email = payload.get('email')
            password = payload.get('password')     
            uid = request.session.authenticate(request.db, email, password)
            if not uid:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Invalid access token"
                        }
                    }),
                    content_type="application/json"
                )
            user = request.env['res.users'].sudo().browse(uid)
            user_details = []
            user_details.append({
                        'name': user.name if user.name else None,
                        'email': user.email if user.email else None,
                        'contact': user.contact if user.contact else None,
                        'pan_vat': user.pan_vat if user.pan_vat else None,
                        'national_id': user.national_id if user.national_id else None,
                        'address': user.address if user.address else None,
                        'company': user.company_id.name if user.company_id.name else None,
            })
            return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data':{
                                'message': user_details
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status= 200
                )
        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': 'Internal server error',
                        'details': str(e)
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    # @http.route('/payroll/api/logout', type='json', auth='public', csrf=False, methods=['POST'])
    # def logout(self, **kwargs):
    #     token = request.httprequest.headers.get('Authorization')
    #     user = ProtectedController.validate_token(token)
        
    #     if user:
    #         user.sudo().write({'token': False})
    #         return {'success': 'Logout successful'}
    #     return {'error': 'Invalid token'}, 401
# testing

# class ProductController(http.Controller):
#     @http.route("/payroll/api/get_products", type="http", methods=["GET"], csrf=False)
#     def get_product(self, **kw):
#         try:
#             hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
#             _logger.info(f"Received request from: {hosturl}")

#             company_id = kw.get('company_id')
#             if not company_id:
#                 return {"status": "error", "message": "company_id is required"}

#             company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
#             if not company:
#                 return {"status": "error", "message": "Company not found"}

#             _logger.info(f"Company: {company.name}")

#             products = request.env["product.template"].sudo().search([('company_id', '=', int(company_id))])
#             data = []
#             for product in products:
#                 # category_names = [cat.name for cat in product.categ_id]
#                 data.append(
#                     {
#                         "id": product.id,
#                         "name": product.name,
#                         'cost_price': product.standard_price,
#                         'sales_price': product.list_price,
#                         # "category": category_names,
#                     }
#                 )
#             return request.make_response(
#                 json.dumps({"status": "success", "data": data}),
#                 headers=[("Content-Type", "application/json")]
#             )
#         except Exception as e:
#             _logger.error(f"Error: {str(e)}")
#             return {"status": "error", "message": str(e)}

