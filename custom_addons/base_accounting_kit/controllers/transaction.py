from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
from datetime import datetime
import logging
import json
from odoo.exceptions import ValidationError
from . import jwt_token_auth
import jwt

_logger = logging.getLogger(__name__)

class Transaction(http.Controller):
    @http.route('/trading/api/get_transactions',type='http', auth='public', methods=['GET'], csrf=False)
    def get_transaction(self,**kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            payment_type = kwargs.get('payment_type')
            customer_id = kwargs.get('customer_id')
            date = kwargs.get('date')
            journal_id = kwargs.get('journal_id')
            payment_method_id = kwargs.get('payment_method_id')
            # payment_transaction_id = kwargs.get('payment_transaction')
            bank_reference = kwargs.get('bank_reference')
            cheque_reference = kwargs.get('cheque_reference')
            company_id = kwargs.get('company_id')
            state = kwargs.get('state')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')  
            
            domain = []

            if payment_type:
                domain.append(('payment_type', '=', payment_type))
            if customer_id:
                domain.append(('partner_id.id', '=', customer_id))
            if date:
                domain.append(('date', '=', date))
            if journal_id:
                domain.append(('journal_id.id', '=', journal_id))
            if payment_method_id:
                domain.append(('payment_method_line_id.id', '=', payment_method_id))
            # if payment_transaction_id:
            #     domain.append(('payment_transaction_id.id', '=', payment_transaction_id))
            if bank_reference:
                domain.append(('bank_reference', '=', bank_reference))
            if cheque_reference:
                domain.append(('cheque_reference', '=', cheque_reference))
            if company_id:
                domain.append(('company_id.id', '=', company_id))
            if state:
                domain.append(('state', '=', state))
            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))


            
            transactions = request.env['account.payment'].sudo().search(domain)

            transaction_details = []
            for transaction in transactions:
                transaction_details.append({
                    'id': transaction.id,
                    'name': transaction.name,
                    'payment_type': transaction.payment_type,
                    'customer_id': transaction.partner_id.id if transaction.partner_id.id else None,
                    'customer_name': transaction.partner_id.name if transaction.partner_id.name else None,
                    'date': transaction.date.strftime('%Y-%m-%d %H:%M:%S'),
                    'journal_id': transaction.journal_id.id,
                    'payment_method_id': transaction.payment_method_line_id.id,
                    'amount': transaction.amount,
                    # 'payment_transaction': transaction.payment_transaction_id.id if transaction.payment_transaction_id.id else None,
                    'bank_reference': transaction.bank_reference if transaction.bank_reference else None,
                    'cheque_reference': transaction.cheque_reference if transaction.cheque_reference else None,
                    'company_id': transaction.company_id.id if transaction.company_id.id else None,
                    'state': transaction.state
                })
            
            return request.make_response(
                    json.dumps({"status": "success", "data": transaction_details}),
                    headers=[("Content-Type", "application/json")]
                )   
        except Exception as e:
            print(f"ahsdgfhadshgaksdjhga")
            return request.make_response(
                json.dumps({"status": "fail", "message": str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/trading/api/create_transactions',type='http', auth='public', methods=['POST'], csrf=False)
    def create_transaction(self,**kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            company_id = auth_status['company_id']

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
            
            voucher_id = json_data.get('voucher_id')
            payment_type = json_data.get('payment_type')
            customer_id = json_data.get('customer_id')
            date = json_data.get('date')
            amount = json_data.get('amount')
            journal_id = json_data.get('journal_id')
            payment_method_id = json_data.get('payment_method_id')
            payment_transaction_id = json_data.get('payment_transaction')
            bank_reference = json_data.get('bank_reference')
            cheque_reference = json_data.get('cheque_reference')
            state = json_data.get('state')

            transaction_vals = {
                'voucher_id': voucher_id if voucher_id else None,
                'payment_type': payment_type,
                'partner_id': customer_id if customer_id else None,
                'date': date,
                'amount': amount,
                'journal_id': journal_id if journal_id else None,
                'payment_method_line_id': payment_method_id if payment_method_id else None,
                'payment_transaction_id': payment_transaction_id if payment_transaction_id else None,
                'bank_reference': bank_reference,
                'cheque_reference': cheque_reference,
                'state': state,
                'company_id': company_id,
            }
            
            transaction = request.env['account.payment'].sudo().create(transaction_vals)

            return request.make_response(
                    json.dumps({"status": "success", "data": {"id": transaction.id}}),
                    headers=[("Content-Type", "application/json")]
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