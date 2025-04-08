from odoo.http import Response, request
from odoo import http,api,SUPERUSER_ID
import datetime
from . import jwt_token_auth
from datetime import date
import logging
import json

_logger = logging.getLogger(__name__)

class setLanguage(http.Controller): 
    @http.route("/trading/api/set_language", type="http",cors="*", auth="public", methods=["POST"], csrf=False)
    def set_language(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")

            token = request.httprequest.headers.get("Authorization")
            if token and token.startswith("Bearer "):
                bearer_token = token[len("Bearer "):]
        
            status = jwt_token_auth.JWTAuth.check_jwt(self, bearer_token)
        

            if status.get("success") != 'Access granted':
                return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "Unauthorized Access"
                        }}),
                    content_type='application/json'
                )
            

            company_id = kw.get('company_id')
            if not company_id:
                return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "Company Required"
                        }}),
                    content_type='application/json'
                )
            

            company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
            if not company:
                return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "Company Not Found"
                        }}),
                    content_type='application/json'
                )
            

            _logger.info(f"Company: {company.name}")

            language = kw.get('language')
            _logger.error(f"Language: {language}")
            target_language = 'ne_NP' if language == 'Nepal/नेपाली' else 'en_US' if language == 'English (US)' else None
            _logger.error(f"Erfdgfgfgror: {target_language}")
            if not language:
                return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "Language is required"
                        }}),
                    content_type='application/json'
                )
            

            users = request.env["res.users"].sudo().search([('company_id', '=', int(company_id))])
            users.sudo().write({'lang': target_language})

            # return(json.dumps({"status": "success"}))
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"success",
                        "data":{
                            "message": "Change successfully"
                        }}),
                    content_type='application/json'
                )
            

        except Exception as e:
            # _logger.error(f"Error: {str(e)}")
            # return {"status": "error", "message": str(e)}
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
            