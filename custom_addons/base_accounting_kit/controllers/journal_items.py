from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
import base64
from . import jwt_token_auth
from datetime import datetime, timedelta
import logging
import json
from odoo.exceptions import ValidationError,AccessError

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

    @http.route('/trading/api/get_account_journal', type='http',auth='public',cors="*", methods=['GET'], csrf=False) # Changed auth to public as per original
    def get_account_journal(self, **kwargs):
        try:
            # 1. Authenticate Request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # 2. Get Filters from Query Parameters
            # company_id_str = auth_status['data'].get('company_id')
            journal_type = request.params.get('type') # Optional: filter by journal type (e.g., 'sale', 'purchase', 'bank', 'cash')

            # 3. Construct Domain
            domain = []
            company_id = None

            # Company Filter Logic (similar to the example provided)
            # if company_id_str:
            #     try:
            #         company_id = int(company_id_str)
            #         # domain.append(('company_id', '=', company_id))
            #         # If hierarchy is needed:
            #         # domain.extend(['|', ('company_id', '=', False), ('company_id', 'parent_of', [company_id])])

            #     except (ValueError, TypeError):
            #          return request.make_response(
            #             json.dumps({
            #                 'status': 'fail',
            #                 'data': {'message': 'Invalid Company ID provided.'}
            #             }),
            #             headers=[('Content-Type', 'application/json')],
            #             status=400
            #         )
            # else:
            #      # If no company_id is provided, filter by user's allowed companies
            #      domain.append(('company_id', 'in', request.env.user.company_ids.ids))


            # Suitable Journal IDs Filter (Example: Filter by type if provided)
            # 'suitable_journal_ids' usually implies filtering based on context or type.
            # Here, we'll filter by the 'type' parameter if it's given.
            if journal_type:
                # Validate journal_type against allowed values if necessary
                allowed_types = ['sale', 'purchase', 'cash', 'bank', 'general', 'situation']
                if journal_type in allowed_types:
                    domain.append(('type', '=', journal_type))
                else:
                    # Optional: Return error for invalid type
                    pass # Silently ignore invalid type for now

            # The example domain `[('id', 'in', suitable_journal_ids)]` would be used
            # if you had a pre-computed list of allowed journal IDs.
            # If filtering by type covers the requirement, this part isn't needed.
            # If you *do* have a list `suitable_journal_ids`, add:
            # domain.append(('id', 'in', suitable_journal_ids))

            _logger.info(f"Searching account.journal with domain: {domain}")

            # 4. Search for Journals
            # Use current user's environment to respect access rights
            journals = request.env['account.journal'].search(domain)

            # 5. Format Results
            journal_details = []
            for journal in journals:
                journal_details.append({
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                    'company_id': journal.company_id.id,
                    'company_name': journal.company_id.name,
                    'currency_id': journal.currency_id.id if journal.currency_id else None,
                    'currency_name': journal.currency_id.name if journal.currency_id else None,
                    'default_account_id': journal.default_account_id.id if journal.default_account_id else None,
                    'default_account_name': journal.default_account_id.name if journal.default_account_id else None,
                    'active': journal.active,
                })

            # 6. Return Response
            return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': journal_details,
                        'filter_applied': { # Include applied filters
                            'company_id': company_id,
                            'type': journal_type
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status= 200
                )

        except AccessError:
             return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Access Denied. Please check permissions.'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )
        except Exception as e:
            _logger.error(f"Error occurred in get_account_journal: {e}", exc_info=True)
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


