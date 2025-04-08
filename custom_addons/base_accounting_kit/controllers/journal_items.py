from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
import base64
from . import jwt_token_auth
from datetime import datetime, timedelta
import logging
import json
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class JournalItems(http.Controller):

    @http.route('/trading/api/get_journal_items', type='http',auth='none',cors="*", methods=['GET'], csrf=False)
    def get_journal_items(self, **kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Get data from the query parameters
            filter_type = request.params.get('filter')  # 'daily', 'weekly', 'monthly', 'yearly', 'custom'
            print ("filter type",filter_type)
            from_date = request.params.get('from_date')
            to_date = request.params.get('to_date')

            # Determine the date range based on filter type
            if filter_type == 'custom' and from_date and to_date:
                date_from = datetime.strptime(from_date, '%Y-%m-%d')
                date_to = datetime.strptime(to_date, '%Y-%m-%d')
            else:
                # Default to today if no custom range is provided
                date_to = datetime.now()
                if filter_type == 'daily':
                    date_from = date_to - timedelta(days=1)
                elif filter_type == 'weekly':
                    date_from = date_to - timedelta(weeks=1)
                elif filter_type == 'monthly':
                    date_from = date_to - timedelta(days=30)
                elif filter_type == 'yearly':
                    date_from = date_to - timedelta(days=365)
                else:
                    date_from = datetime.min  # No filtering, get all records

            # Convert dates to the format required by Odoo
            date_from_str = date_from.strftime('%Y-%m-%d')
            date_to_str = date_to.strftime('%Y-%m-%d')

            # Search for move lines within the date range
            move_lines = request.env['account.move.line'].sudo().search([
                ('date', '>=', date_from_str),
                ('date', '<=', date_to_str)
            ])

            account = kwargs.get('account_id')
            domain = []
            if account:
                domain.append(('account_id.id', '=', account))
            elif date_from_str and date_to_str:
                domain.append(('date', '>=', date_from_str),)
                domain.append(('date', '<=', date_to_str))
            

            journal_items = request.env['account.move.line'].sudo().search(domain)
            journal_items_details = []

            for journal_item in journal_items:
                journal_items_details.append({
                    'id': journal_item.id,
                    'fiscal_year': journal_item.date_range_fy_id.name,
                    'account': journal_item.account_id.name,
                    'debit': journal_item.debit,
                    'credit': journal_item.credit,
                    'date': journal_item.date.strftime('%Y-%m-%d %H:%M:%S'),
                    'journal': journal_item.journal_id.name,
                    'partner': journal_item.partner_id.name,
                    'ref': journal_item.ref if journal_item.ref else None,
                    'balance': journal_item.balance,
                })

            return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data':journal_items_details
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



