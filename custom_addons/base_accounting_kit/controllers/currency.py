from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
from . import jwt_token_auth
import datetime
import logging
import json
from odoo.exceptions import ValidationError
import datetime
from nepali_datetime import date as nepali_date

_logger = logging.getLogger(__name__)

class Currency(http.Controller):
    @http.route('/trading/api/get_currency', auth='public',cors="*", methods=['GET'], csrf=False)
    def get_currency(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            currencies = request.env['res.currency'].sudo().search([('active', '=', True)])
            currency_details = []
            for currency in currencies:
                currency_details.append({
                    'id': currency.id,
                    'name': currency.name,
                    'symbol': currency.symbol,
                    'full_name': currency.full_name,
                })
            return request.make_response(
                json.dumps({"status": "success", "data": currency_details}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            return http.Response(
                status=500,  
                response=json.dumps({
                    "status": "fail", 
                    "data":{
                        "message": str(e)}
                    }),
                content_type="application/json"
            )