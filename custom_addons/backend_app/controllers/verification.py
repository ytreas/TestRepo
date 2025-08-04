from odoo import http,fields
from odoo.http import request
# from datetime import datetime, timedelta, timezone
import datetime
import json
from . import jwt_token_auth
import logging
_logger = logging.getLogger(__name__)

class GemsAPI(http.Controller):
    @http.route("/api/reset_password/request_otp", type="http", auth="public", cors="*", methods=["POST"], csrf=False)
    def reset_password_request_otp(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received password reset OTP request from: {hosturl}")
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            email = json_data.get('email')
            if not email:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Email is required"
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
            
            # Generate a 6-digit OTP
            import random
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Set expiration time (10 minutes from now)
            expiration = datetime.datetime.now() + datetime.timedelta(minutes=10)
            
            # Store OTP in the database
            user.sudo().write({
                'reset_password_otp': otp,
                'reset_password_otp_expiry': expiration
            })
            
            # Send email directly without template
            mail_values = {
                'subject': 'Password Reset OTP',
                'body_html': f"""
                    <p>Hello {user.name},</p>
                    <p>We received a request to reset your password. Your OTP is:</p>
                    <h2 style="font-size: 24px; margin: 16px 0; text-align: center; padding: 10px; background-color: #f5f5f5; border-radius: 4px;">{otp}</h2>
                    <p>This OTP will expire in 10 minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <p>Thank you,<br/>Kamauu Team</p>
                """,
                'email_from': request.env.user.company_id.email or 'noreply@kamauu.com',
                'email_to': email,
            }
            
            # Create and send email
            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            
            return http.Response(
                status=200,
                response=json.dumps({
                    "status": "success",
                    "data": {
                        "message": "OTP sent to your email"
                    }
                }),
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in reset_password_request_otp: {str(e)}")
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
    @http.route("/api/reset_password/validate_otp", type="http", auth="public", cors="*", methods=["POST"], csrf=False)
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
            if not user.reset_password_otp or user.reset_password_otp != otp:
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
            if user.reset_password_otp_expiry and user.reset_password_otp_expiry < now:
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
                'reset_password_otp_expiry': datetime.datetime.now() + datetime.timedelta(minutes=5)
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

    @http.route("/api/reset_password/change_password", type="http", auth="public", cors="*", methods=["POST"], csrf=False)
    def reset_password_change(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received password change request from: {hosturl}")
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            email = json_data.get('email')
            new_password = json_data.get('new_password')
            # verification_token = json_data.get('verification_token')
            
            if not all([email, new_password]):
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Email, new password and verification token are required"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Password policy validation
            if len(new_password) < 8:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Password must be at least 8 characters long"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Find user with this email and verification token
            user = request.env['res.users'].sudo().search([
                ('login', '=', email),
            ], limit=1)
            
            if not user:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Invalid verification token"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Check if verification is still valid (OTP expiry serves as our session timeout)
            now = datetime.datetime.now()
            if user.reset_password_otp_expiry and user.reset_password_otp_expiry < now:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Verification session has expired"
                        }
                    }),
                    content_type='application/json'
                )
            
            # Change password and clear all reset tokens
            user.sudo().write({
                'password': new_password,
                'reset_password_otp': False,
                'reset_password_otp_expiry': False,
                # 'reset_password_verification_token': False
            })
            
            return http.Response(
                status=200,
                response=json.dumps({
                    "status": "success",
                    "data": {
                        "message": "Password has been successfully changed"
                    }
                }),
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in reset_password_change: {str(e)}")
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