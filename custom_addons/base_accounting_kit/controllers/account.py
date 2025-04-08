from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
import base64
from . import jwt_token_auth
import datetime
import logging
import json
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class Account(http.Controller):

    @http.route('/trading/api/get_accounts', type='http', auth='public',cors="*", methods=['GET'], csrf=False)
    def get_accounts(self,**kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            account_type = kwargs.get('type')
            business_type = kwargs.get('business_type_id')
            domain = []
            if account_type:
                domain.append(('account_type', '=', account_type))
            if business_type:
                domain.append('|')
                domain.append(('business_type.id', '=', business_type))
                domain.append(('business_type', '=', 'All'))
            else:
                domain.append(('business_type','=', 'All'))
            accounts = request.env['account.account'].sudo().search(domain)
            accounts_details = []

            for account in accounts:
                accounts_details.append({
                    'id': account.id,
                    'name': account.name,
                    'code': account.code,
                    'type': account.account_type,
                    'business type' : account.business_type.name if account.business_type else None,
                    'company': account.company_id.name if isinstance(account.company_id, request.env['res.company'].__class__) else None,
                })

            return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': accounts_details
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status= 200
                )
        
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'Internal server error'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )
        
    @http.route('/trading/api/create_account', type='http', auth='public',cors="*", methods=['POST'], csrf=False)
    def create_account(self,**kwargs):
        try:   
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            if 'allowed_company_ids' not in request.env.context:
                allowed_company_ids = request.env.user.company_ids.ids 
                request.env.context = dict(request.env.context, allowed_company_ids=allowed_company_ids)
            else:
                allowed_company_ids = request.env.context['allowed_company_ids']
            if not allowed_company_ids:
                _logger.debug("allowed_company_ids context is not set or empty.")
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'Context "allowed_company_ids" not set'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )
            
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            account_name = json_data.get('name')
            account_code = json_data.get('code')
            account_type = json_data.get('type')
            business_type = json_data.get('business_type_id')
            company = json_data.get('company_id')
        
            if not account_name or not account_code or not account_type or not company or not business_type:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'All fields are required'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            company_id = request.env['res.company'].sudo().search([('id', '=', company)], limit=1)
            
            if not company_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'Invalid company'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            account_vals = {
                'name': account_name,
                'code': account_code,
                'account_type': account_type,
                'business_type': business_type,
                'company_id': company_id.id
            }
    
            account = request.env['account.account'].sudo().create(account_vals)
    
            return request.make_response(
                        json.dumps({
                            'success': 'Account created',
                            'account_id': account.id,
                            'name' : account.name,
                            'code' : account.code,
                            'account_type' : account.account_type,
                            'business_type' : account.business_type.name,
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=200
                    )    
        
        except ValidationError as ve:
                _logger.error(f"Validation error: {ve}")
                return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data':{
                                    'message': str(ve)
                                   }
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )
    
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': str(e)
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )
        
    @http.route("/trading/api/get_account_type",type="http",cors="*",auth="public",methods=["GET"],csrf=False)
    def get_account_type(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            records = request.env['account.account'].sudo().search([])

            account_types = list(set([record.account_type for record in records]))

            return request.make_response(
                json.dumps({"status":"success","data": account_types}),
                headers=[("Content-Type","application/json")]
            )

        except Exception as e:
                return http.Response(
                        status=401,
                        response=json.dumps({
                            "status":"fail",
                            "data":{
                                "message": str(e)
                            }}),
                        content_type='application/json'
                    )
            
            