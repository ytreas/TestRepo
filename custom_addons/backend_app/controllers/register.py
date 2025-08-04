import re
import json
import logging
from odoo import http
from odoo.http import Response, request
from odoo import http,api,SUPERUSER_ID
import datetime
from . import jwt_token_auth
import logging
import json
import re

_logger = logging.getLogger(__name__)

class RegisterAPI(http.Controller):

    @http.route('/api/register', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def register_user(self, **kw):
        try:
            data = json.loads(request.httprequest.data)

            name = data.get('name', '').strip()
            email = data.get('email', '').strip().lower()
            password = data.get('password', '').strip()
            mobile = data.get('mobile', '').strip()

            # === VALIDATIONS ===
            if not name or len(name) < 3:
                return _json_fail("Name must be at least 3 characters long", 400)

            if not re.match(r"^[A-Za-z\s]+$", name):
                return _json_fail("Name can only contain letters and spaces", 400)

            if not email:
                return _json_fail("Email is required", 400)

            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                return _json_fail("Invalid email format", 400)

            if not password or len(password) < 6:
                return _json_fail("Password must be at least 6 characters long", 400)

            if not re.match(r"^(?=.*[A-Za-z])(?=.*\d).+$", password):
                return _json_fail("Password must contain both letters and numbers", 400)

            if not mobile:
                return _json_fail("Mobile number is required", 400)

            if not re.match(r"^9\d{9}$", mobile):
                return _json_fail("Mobile number must start with 9 and be exactly 10 digits", 400)

            # === Check if email already exists ===
            existing_user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if existing_user:
                return _json_fail("Email is already registered", 409)

            # === Check if mobile already exists ===
            existing_mobile = request.env['res.users'].sudo().search([('mobile', '=', mobile)], limit=1)
            if existing_mobile:
                return _json_fail("Mobile number is already registered", 409)

            # === Create user ===
            user = request.env['res.users'].sudo().create({
                'name': name,
                'login': email,
                'email': email,
                'password': password,
                'company_id': request.env.company.id,
                'mobile': mobile,
            })
            import random
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            expiration = datetime.datetime.now() + datetime.timedelta(minutes=10)
            
            # Store OTP in the database
            user.sudo().write({
                'register_otp': otp,
                'register_otp_expiry': expiration
            })
            mail_values = {
                'subject': 'Registration Successful - Verify Your OTP',
                'body_html': f"""
                    <p>Hello {user.name},</p>
                    <p>Welcome to Kamauu! Your registration was successful.</p>
                    <p>Please verify your account using the OTP below:</p>
                    <h2 style="font-size: 24px; margin: 16px 0; text-align: center; padding: 10px; background-color: #f5f5f5; border-radius: 4px;">{otp}</h2>
                    <p>This OTP will expire in 10 minutes.</p>
                    <p>If you did not sign up for this account, please ignore this email.</p>
                    <p>Thank you,<br/>Kamauu Team</p>
                """,
                'email_from': 'info.flowgenic@gmail.com',
                'email_to': email,
            }

            # Create and send email
            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'message': 'OTP sent successfully. Please check your email to verify your account.',
                    'data': {
                        'user_id': user.id,
                        'name': user.name,
                        'email': user.email,
                        'mobile': user.mobile,
                    }
                }),
                headers=[("Content-Type", "application/json")],
                status=201
            )

        except Exception as e:
            _logger.error(f"Registration error: {e}")
            return _json_fail("Internal server error", 500)

    @http.route('/api/resend_register_otp', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def resend_register_otp(self, **kw):
        try:
            data = json.loads(request.httprequest.data)
            email = data.get('email', '').strip().lower()

            if not email:
                return _json_fail("Email is required", 400)

            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                return _json_fail("Invalid email format", 400)

            # === Find the user ===
            user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if not user:
                return _json_fail("User with this email does not exist", 404)

            # === Generate and store new OTP ===
            import random
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            expiration = datetime.datetime.now() + datetime.timedelta(minutes=10)

            user.sudo().write({
                'register_otp': otp,
                'register_otp_expiry': expiration
            })

            # === Email the new OTP ===
            mail_values = {
                'subject': 'Your OTP Has Been Resent - Kamauu Registration',
                'body_html': f"""
                    <p>Hello {user.name},</p>
                    <p>You requested a new OTP for account verification.</p>
                    <p>Use the OTP below to verify your account:</p>
                    <h2 style="font-size: 24px; margin: 16px 0; text-align: center; padding: 10px; background-color: #f5f5f5; border-radius: 4px;">{otp}</h2>
                    <p>This OTP will expire in 10 minutes.</p>
                    <p>If you did not request this, please ignore this message.</p>
                    <p>Thanks,<br/>Kamauu Team</p>
                """,
                'email_from': 'info.flowgenic@gmail.com',
                'email_to': email,
            }

            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'message': 'OTP resent successfully. Please check your email.',
                    'data': {
                        'user_id': user.id,
                        'email': user.email,
                        'name': user.name
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.error(f"Resend OTP error: {e}")
            return _json_fail("Internal server error", 500)


    @http.route("/api/register_validate_otp", type="http", auth="public", cors="*", methods=["POST"], csrf=False)
    def reset_password_validate_otp(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received OTP validation request from: {hosturl}")
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            email = json_data.get('email')
            otp = json_data.get('otp')
            
            if not email or not otp:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Email and OTP are required"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Find user with this email
            user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if not user:
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "No user found with this email"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Validate OTP
            if not user.register_otp or user.register_otp != otp:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Invalid OTP"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Check if OTP is expired
            now = datetime.datetime.now()
            if user.register_otp_expiry and user.register_otp_expiry < now:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "OTP has expired"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Generate a verification token that will be used for the password change
            # import uuid
            # verification_token = str(uuid.uuid4())
            
            # Store the verification token
            user.sudo().write({
                # 'reset_password_verification_token': verification_token,
                # Keep OTP valid for just 5 more minutes to complete the process
                'register_otp_expiry': datetime.datetime.now() + datetime.timedelta(minutes=5),
                'is_register_validated': True
            })
            
            return http.Response(
                status=200,
                response=json.dumps({
                    "status": "success",
                    "data": {
                        "message": "OTP validated successfully",
                        # "verification_token": verification_token
                    }
                }),
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in reset_password_validate_otp: {str(e)}")
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                content_type='application/json'
            )
    @http.route('/api/resend_reset_otp', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def resend_reset_password_otp(self, **kw):
        try:
            data = json.loads(request.httprequest.data)
            email = data.get('email', '').strip().lower()

            if not email:
                return _json_fail("Email is required", 400)

            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                return _json_fail("Invalid email format", 400)

            # === Find the user ===
            user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if not user:
                return _json_fail("User with this email does not exist", 404)

            # === Generate and store reset OTP ===
            import random
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            expiration = datetime.datetime.now() + datetime.timedelta(minutes=10)

            user.sudo().write({
                'reset_password_otp': otp,
                'reset_password_otp_expiry': expiration
            })

            # === Email the OTP ===
            mail_values = {
                'subject': 'Reset Password OTP - Kamauu',
                'body_html': f"""
                    <p>Hello {user.name},</p>
                    <p>You requested to reset your password. Please use the OTP below to proceed:</p>
                    <h2 style="font-size: 24px; margin: 16px 0; text-align: center; padding: 10px; background-color: #f5f5f5; border-radius: 4px;">{otp}</h2>
                    <p>This OTP will expire in 10 minutes.</p>
                    <p>If you did not request a password reset, please ignore this email.</p>
                    <p>Thank you,<br/>Kamauu Team</p>
                """,
                'email_from': 'info.flowgenic@gmail.com',
                'email_to': email,
            }

            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'message': 'Password reset OTP resent successfully. Please check your email.',
                    'data': {
                        'user_id': user.id,
                        'email': user.email,
                        'name': user.name
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.error(f"Resend Reset OTP error: {e}")
            return _json_fail("Internal server error", 500)




# Helper for JSON error responses
def _json_fail(message, status_code):
    return http.Response(
        json.dumps({'status': 'fail', 'message': message}),
        status=status_code,
        content_type='application/json'
    )
