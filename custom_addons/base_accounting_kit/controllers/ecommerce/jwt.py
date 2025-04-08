from odoo import http, _
from odoo.http import request, Response
import jwt
import datetime
from nepali_datetime import date as nepali_date
from odoo.exceptions import AccessDenied
import json
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "")
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
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user = request.env["res.users"].sudo().browse(payload["user_id"])
                return {"success": "Access granted", "user_id": user.id}
            except jwt.ExpiredSignatureError:
                return {"fail": "Token has expired"}
            except jwt.InvalidTokenError:
                return {"fail": "Invalid token"}
            except Exception as e:
                return {"fail": str(e)}
        else:
            return {"fail": "Token Required"}

    def validate_refresh_token(self, refresh_token):
        if refresh_token:
            try:
                payload = jwt.decode(
                    refresh_token, REFRESH_SECRET_KEY, algorithms=["HS256"]
                )
                user = payload["user_id"]
                user_id = request.env["res.users"].sudo().browse(user)

                return {
                    "success": True,
                    "data": {
                        "message": "Refresh token valid",
                        "user_id": payload["user_id"],
                        "email": user_id.login,
                        "company_id": user_id.company_id.id,
                    },
                }, 200
            except jwt.ExpiredSignatureError:
                return {
                    "success": False,
                    "message": "Refresh token has expired",
                }, 401
            except jwt.InvalidTokenError:
                return {
                    "success": False,
                    "data": {"message": "Invalid refresh token"},
                }, 401
            except Exception as e:
                return {"success": False, "message": str(e)}, 500
        else:
            return {
                "success": False,
                "data": {"message": "Refresh token required"},
            }, 400

    def generate_new_access_token(self, user_id, email, role, company_id):
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.now(datetime.timezone.utc) + ACCESS_TOKEN_EXPIRY,
            "email": email,
            "company_id": company_id,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    def authenticate_request(self, request):
        try:
            token = request.httprequest.headers.get("Authorization")
            if token and token.startswith("Bearer "):
                bearer_token = token[len("Bearer ") :]
            else:
                return {
                    "success": False,
                    "message": _("Authorization header missing or malformed"),
                }, 400
            payload = jwt.decode(bearer_token, SECRET_KEY, algorithms=["HS256"])
            company_id = payload.get("company_id")
            user_id = payload.get("user_id")
            status = JWTAuth().check_jwt(bearer_token)
            if status.get("success") != "Access granted":
                if status.get("fail") == "Token has expired":
                    return {
                        "success": False,
                        "message": "Access token expired, Please generate a new token",
                    }, 401
                else:
                    return {
                        "success": False,
                        "message": "Unauthorized access",
                    }, 400
            else:
                return {
                    "success": True,
                    "message": "Access granted",
                    "company_id": company_id,
                    "user_id": user_id,
                }, 200
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
            }, 400
