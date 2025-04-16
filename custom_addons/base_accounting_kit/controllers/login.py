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
from dotenv import load_dotenv
import os
load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")
REFRESH_TOKEN_EXPIRY = datetime.timedelta(
    days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRY_days", 30))
)
ACCESS_TOKEN_EXPIRY = datetime.timedelta(
    days=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRY_days", 7))
)

class AuthAPI(http.Controller):

    def handle_error(self, exception):
        if isinstance(exception, AccessError):
            return http.Response(
                status=403,
                response=json.dumps({"status": "fail", "message": "Access Denied"}),
                content_type="application/json"
            )

    @http.route('/trading/api/login', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
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
                    if group.name == 'Settings':
                        role = 'admin'
                        break
                    else:
                        role = 'user'
                # Check if this is the first login
                is_first_login = user.is_first_login
                
                # If it's the first login, update the flag
                if is_first_login:
                    user.sudo().write({'is_first_login': False})        
                # Generate access token
                related_register_id = request.env['company.register'].sudo().search([('email', '=', email)]).id
                access_payload = {
                    'user_id': user.id,
                    'exp': datetime.datetime.now(datetime.timezone.utc) + ACCESS_TOKEN_EXPIRY,
                    'email': email,
                    'password': password,
                    'role': role,
                    'company_id': user.company_id.id,
                    'register_id': related_register_id if related_register_id else None
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
                            'company_id': user.company_id.id,
                            'register_id': related_register_id if related_register_id else None,
                            'refresh_token': refresh_token,
                            'is_first_login': is_first_login
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
    
    @http.route('/trading/api/refresh_token', type='http',auth='public',cors="*", csrf=False, methods=['GET'])
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
                email = refresh_status['data']['email']
                role = refresh_status['data']['role']
                company_id = refresh_status['data']['company_id']
                print("the company_id is", company_id)
                # Generate a new access token
                new_access_token = jwt_token_auth.JWTAuth.generate_new_access_token(self, user_id, email, role, company_id)
                refresh_payload = {
                    'user_id': user_id,
                    'exp': datetime.datetime.now(datetime.timezone.utc) + REFRESH_TOKEN_EXPIRY
                }
                new_refresh_token = jwt.encode(refresh_payload, REFRESH_SECRET_KEY, algorithm='HS256')

                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': {
                            'access_token': new_access_token,
                            'refresh_token': new_refresh_token
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


    @http.route('/trading/api/get_user_details', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
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
                        'name_np': user.name_np if user.name_np else None,
                        'email': user.email if user.email else None,
                        # 'contact': user.contact if user.contact else None,
                        # 'pan_vat': user.pan_vat if user.pan_vat else None,
                        # 'national_id': user.national_id if user.national_id else None,
                        # 'address': user.address if user.address else None,
                        'company': user.company_id.name if user.company_id.name else None,
                        'company_id' : user.company_id.id if user.company_id.id else None,
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

    # @http.route('/trading/api/logout', type='json', auth='public', csrf=False, methods=['POST'])
    # def logout(self, **kwargs):
    #     token = request.httprequest.headers.get('Authorization')
    #     user = ProtectedController.validate_token(token)
        
    #     if user:
    #         user.sudo().write({'token': False})
    #         return {'success': 'Logout successful'}
    #     return {'error': 'Invalid token'}, 401


# class ProductController(http.Controller):
#     @http.route("/trading/api/get_products", type="http", methods=["GET"], csrf=False)
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

    @http.route('/yatroo/api/login', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def yatrooLogin(self):
        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)
        
        # Get mobile and password from the request data
        mobile = json_data.get('mobile')
        password = json_data.get('password')
        
        try:
            # Search for user by mobile number
            user = request.env['res.users'].sudo().search([('mobile', '=', mobile)], limit=1)
            if user:
                # Authenticate using the user's login (username) and password
                uid = request.session.authenticate(request.db, user.login, password)
                if uid:
                    role = 'none'
                    for group in user.groups_id:
                        if group.name == 'Trade Admin Access':
                            role = 'admin'
                            break
                        elif group.name == 'Trade User Access':
                            role = 'user'
                            break
                        
                    # Generate access token
                    access_payload = {
                        'user_id': user.id,
                        'exp': datetime.datetime.now(datetime.timezone.utc) + ACCESS_TOKEN_EXPIRY,
                        'mobile': mobile,
                        'role': role,
                        'company_id': user.company_id.id
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
                                'refresh_token': refresh_token
                            }
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=200
                    )
                else:
                    # Invalid password or authentication failure
                    return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data': {
                                'message': 'Invalid Credentials'
                            }
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=401
                    ) 
            else:
                # User not found with the given mobile number
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'User not found with the given mobile number'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
    
        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': 'An error occurred during authentication',
                    'details': str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

class PublicReportController(http.Controller):

    @http.route('/report/public/pdf/<string:report_name>/<int:order_id>', type='http', auth="public")
    def public_pdf_report(self, report_name, order_id, **kwargs):
        try:
            # Debugging log
            _logger.info(f"Fetching report: {report_name} for order ID: {order_id}")

            # Ensure `report_name` is valid
            report = request.env['ir.actions.report'].sudo().search(
                [('report_name', '=', report_name)], limit=1
            )
            if not report:
                return request.not_found()

            # Generate the PDF (Ensure order_id is passed as a list)
            pdf, _ = report._render_qweb_pdf(report,[order_id])  # Ensure list format

            # Create response with proper headers
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', str(len(pdf))),
                ('Content-Disposition', f'inline; filename="{report_name}.pdf"')
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)

        except Exception as e:
            _logger.error(f"Error generating PDF for {report_name}: {str(e)}")
            return request.make_response(
                str(e), headers=[('Content-Type', 'text/plain')], status=500
            )