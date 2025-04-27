import json
import datetime
import logging
from . import jwt_token_auth
from datetime import datetime, timedelta
from odoo import http
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request


import json
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from odoo import http, fields, _
from dateutil.relativedelta import relativedelta # Needed for date calculations
import base64
import logging
import werkzeug.urls # For generating URL
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)
  
class GeneralLedger(http.Controller):
    @http.route('/trading/api/general_ledger', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_account_general_ledger(self, **kw):
        try:
            # Extract the request host URL
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            # Authenticate the request using JWT (custom authentication logic)
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)

            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            company_id = json_data.get('company_id')
            print("=========================================",company_id)
            if company_id:
                company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
                if not company:
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail", 
                            "data":{
                                "message": "Company not found"
                            }}),
                        headers=[
                            ('Content-Type', 'application/json')
                        ],
                    )
            
            # Extract raw data from the request body
    

                # Get filters from the request data
                filter_type = json_data.get('filter')  # 'daily', 'weekly', 'monthly', 'yearly', etc.
                from_date = json_data.get('from_date')
                to_date = json_data.get('to_date')

                # Determine the date range based on the filter type
                if from_date and to_date:
                    date_from = datetime.strptime(from_date, '%Y-%m-%d')
                    date_to = datetime.strptime(to_date, '%Y-%m-%d')
                else:
                    # Default to today if no date range is provided
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

                # Convert dates to string format for Odoo queries
                date_from_str = date_from.strftime('%Y-%m-%d') if date_from else None
                date_to_str = date_to.strftime('%Y-%m-%d') if date_to else None
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                # Search for move lines within the date range
                move_lines = request.env['account.move.line'].sudo().search([
                    ('company_id', '=', company.id), 
                    ('date', '>=', date_from_str),
                    ('date', '<=', date_to_str),
                ])
            
                # Group move lines by account_id
                grouped_data = {}
                for line in move_lines:
                    account_id = line.account_id.id  # Group by account_id
                    if account_id not in grouped_data:
                        grouped_data[account_id] = {
                            'account_id': line.account_id.name if line.account_id else None,
                            'move_lines': []
                        }
                    move_line_dict = {
                        'date': line.date.strftime('%Y-%m-%d') if line.date else None,
                        'date_range_fy_id': line.date_range_fy_id.name if line.date_range_fy_id else None,
                        'move_name': line.move_id.name if line.move_id else None,
                        'partner_id': line.partner_id.name if line.partner_id else None,
                        'name': line.name if line.name else None,
                        'debit': line.debit if line.debit else None,
                        'credit': line.credit if line.credit else None,
                        'balance': line.balance if line.balance else None,
                        'matching_number': line.matching_number if line.matching_number else None,
                        'invoice_date': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id and line.move_id.invoice_date else None,
                        'company_id': line.company_id.name if line.company_id else None,
                        'journal_id': line.journal_id.name if line.journal_id else None,
                        'account_id': line.account_id.name if line.account_id else None,
                        'ref': line.ref if line.ref else None,
                        'product_id': line.product_id.name if line.product_id else None,
                        'tax_ids': [tax.name for tax in line.tax_ids] if line.tax_ids else None,
                        'discount_date': line.discount_date.strftime('%Y-%m-%d') if line.discount_date else None,
                        'discount_amount_currency': line.discount_amount_currency if line.discount_amount_currency else None,
                        'tax_line_id': line.tax_line_id.name if line.tax_line_id else None,
                        'date_maturity': line.date_maturity.strftime('%Y-%m-%d') if line.date_maturity else None,
                        'amount_residual': line.amount_residual if line.amount_residual else None,
                        'amount_residual_currency': line.amount_residual_currency if line.amount_residual_currency else None,
                    }
                    grouped_data[account_id]['move_lines'].append(move_line_dict)

                # Convert grouped data into a list format for response
                final_data = list(grouped_data.values())



                # Return the final response
                return request.make_response(
                    json.dumps({                    
                    'status': 'success',
                    'data': {
                        'general_ledger': final_data,
                        'filter_applied': {
                            'filter_type': filter_type,
                            'from_date': date_from_str,
                            'to_date': date_to_str
                        }
                    }}),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': 'Company required'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
        except AccessError:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': 'Access Denied'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=403
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': str(e)
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )



class ProfitLossController(http.Controller):
    @http.route('/trading/api/profit_loss_data', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def profit_loss_data(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)

            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )

            # Get raw data from the HTTP request
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            # Extract filter parameters from the request body
            filter_type = json_data.get('filter')  # 'daily', 'weekly', 'monthly', 'yearly'
            from_date = json_data.get('from_date')
            to_date = json_data.get('to_date')
            company_id = json_data.get('company_id')  # Add company filtering
            print(f"filter_type: {filter_type}")

            # Determine the date range based on filter type
            if from_date and to_date:
                date_from = datetime.strptime(from_date, '%Y-%m-%d')
                date_to = datetime.strptime(to_date, '%Y-%m-%d')
            else:
                # Default to today if no custom range provided
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

            # Build search domain with optional company filtering
            domain = [('date', '>=', date_from_str), ('date', '<=', date_to_str)]
            if company_id and company_id is not 1:
                domain.append(('company_id.id', '=', company_id))

            # Fetch account moves
            moves = request.env['account.move'].sudo().search(domain)

            # Fetch income and expense accounts with company filtering
            income_accounts = request.env['account.account'].sudo().search([
                ('internal_group', '=', 'income'),
                ('company_id.id', '=', company_id)
            ] if company_id and company_id is not 1 else [('internal_group', '=', 'income')])

            expense_accounts = request.env['account.account'].sudo().search([
                ('internal_group', '=', 'expense'),
                ('company_id.id', '=', company_id)
            ] if company_id and company_id is not 1 else [('internal_group', '=', 'expense')])

            income_account_ids = income_accounts.mapped('id')
            expense_account_ids = expense_accounts.mapped('id')


            accounts = {}
            for move in moves:
                for line in move.line_ids:
                    account_id = line.account_id.id
                    if account_id in income_account_ids or account_id in expense_account_ids:
                        if account_id not in accounts:
                            accounts[account_id] = {
                                'account_name': line.account_id.name,
                                'account_code': line.account_id.code,
                                'debit': 0.0,
                                'credit': 0.0,
                                'balance': 0.0
                            }
                        accounts[account_id]['debit'] += line.debit
                        accounts[account_id]['credit'] += line.credit
                        accounts[account_id]['balance'] = accounts[account_id]['credit'] - accounts[account_id]['debit']

            report_data = {
                'income': {
                    'details': [
                        {
                            'account_code': info['account_code'],
                            'account_name': info['account_name'],
                            'credit': round(info['credit'], 2),
                            'debit': round(info['debit'], 2),
                            'balance': round(info['balance'], 2)
                        }
                        for account_id, info in accounts.items() if account_id in income_account_ids
                    ],
                    'total_credit': round(sum(info['credit'] for account_id, info in accounts.items() if account_id in income_account_ids), 2),
                    'total_debit': round(sum(info['debit'] for account_id, info in accounts.items() if account_id in income_account_ids), 2),
                    'total_balance': round(sum(info['balance'] for account_id, info in accounts.items() if account_id in income_account_ids), 2)
                },
                'expense': {
                    'details': [
                        {
                            'account_code': info['account_code'],
                            'account_name': info['account_name'],
                            'credit': round(info['credit'], 2),
                            'debit': round(info['debit'], 2),
                            'balance': round(info['balance'], 2)
                        }
                        for account_id, info in accounts.items() if account_id in expense_account_ids
                    ],
                    'total_credit': round(sum(info['credit'] for account_id, info in accounts.items() if account_id in expense_account_ids), 2),
                    'total_debit': round(sum(info['debit'] for account_id, info in accounts.items() if account_id in expense_account_ids), 2),
                    'total_balance': round(sum(info['balance'] for account_id, info in accounts.items() if account_id in expense_account_ids), 2)
                },
                'net profit/loss': round(
                    sum(info['credit'] - info['debit'] for account_id, info in accounts.items() if account_id in income_account_ids) -
                    sum(info['debit'] - info['credit'] for account_id, info in accounts.items() if account_id in expense_account_ids),
                    2
                )
            }

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': report_data
                    }),
                headers=[('Content-Type', 'application/json')]
            )

        except AccessError as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'message': str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=403
            )
        except UserError as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'message': str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'message': str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )



class AccountReport(http.Controller):

    def handle_error(self, exception):
        if isinstance(exception, AccessError):
            return http.Response(
                status=403,
                response=json.dumps({"status": "fail", "message": "Access Denied"}),
                content_type="application/json"
            )
    @http.route('/trading/api/trial_balance', type='http', auth='public', csrf=False, cors="*", methods=['GET'])   
    def trial_balance(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)

            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            filter_type = json_data.get('filter')  # 'daily', 'weekly', 'monthly', 'yearly'
            from_date = json_data.get('from_date')
            to_date = json_data.get('to_date')
            company_id = json_data.get('company_id')  # Get company ID for filtering

            print(f"filter_type: {filter_type}")

            # Determine the date range based on filter type
            if from_date and to_date:
                date_from = datetime.strptime(from_date, '%Y-%m-%d')
                date_to = datetime.strptime(to_date, '%Y-%m-%d')
            else:
                # Default to today if no custom range provided
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

            # Build search domain with optional company filtering
            domain = [('date', '>=', date_from_str), ('date', '<=', date_to_str)]
            if company_id:
                domain.append(('company_id.id', '=', company_id))

            # Search for moves within the date range and company filter
            moves = request.env['account.move'].sudo().search(domain)

   
            # moves = request.env['account.move'].sudo().search([])


            trial_balance_data = {}

            # Process journal entries to calculate debits and credits
            for move in moves:
                for line in move.line_ids:
                    account_id = line.account_id.id
                    if account_id not in trial_balance_data:
                        trial_balance_data[account_id] = {
                            'date': move.date.strftime('%Y-%m-%d'),
                            'date_bs': move.date_bs if move.date_bs else None,
                            'account_name': line.account_id.name,
                            'account_code': line.account_id.code,
                            'debit': 0.0,
                            'credit': 0.0
                        }
                    # Update debit and credit balances
                    trial_balance_data[account_id]['debit'] += line.debit
                    trial_balance_data[account_id]['credit'] += line.credit

            # Format the trial balance response
            formatted_trial_balance = {
                    'trial_balance': [
                        {
                            'date':info['date'],
                            'date_bs':info['date_bs'],
                            'account_name': info['account_name'],
                            'account_code': info['account_code'], 
                            'debit': round(info['debit'], 2),
                            'credit': round(info['credit'], 2),
                            'balance': round(info['debit'] - info['credit'], 2)
                        }
                        for  info in trial_balance_data.values()
                    ]
                }

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': formatted_trial_balance
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
                    ('Content-Type', 'application/json')
                ],
                status=400
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': str(e)
                    }
                }),
                headers=[
                    ('Content-Type', 'application/json')
                ],
                status=500
            )
    
    @http.route('/trading/api/day_book', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def day_book(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)

            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            filter_type = json_data.get('filter')  # 'daily', 'weekly', 'monthly', 'yearly', 'custom'
            from_date = json_data.get('from_date')
            to_date = json_data.get('to_date')
            company_id = json_data.get('company_id')  # Extract company ID for filtering

            print(f"filter_type: {filter_type}")

            # Determine date range
            date_to = datetime.now()
            if from_date and to_date:
                date_from = datetime.strptime(from_date, '%Y-%m-%d')
                date_to = datetime.strptime(to_date, '%Y-%m-%d')
            else:
                if filter_type == 'daily':
                    date_from = date_to - timedelta(days=1)
                elif filter_type == 'weekly':
                    date_from = date_to - timedelta(weeks=1)
                elif filter_type == 'monthly':
                    date_from = date_to - timedelta(days=30)
                elif filter_type == 'yearly':
                    date_from = date_to - timedelta(days=365)
                else:
                    date_from = datetime.min

            # Convert dates to string
            date_from_str = date_from.strftime('%Y-%m-%d')
            date_to_str = date_to.strftime('%Y-%m-%d')

            # Build search domain with optional company filtering
            domain = [('date', '>=', date_from_str), ('date', '<=', date_to_str)]
            if company_id:
                domain.append(('company_id.id', '=', company_id))

            # Fetch day book data with company filtering
            moves = request.env['account.move'].sudo().search(domain)


            # Organize data by date
            day_book_data = {}
            for move in moves:
                move_date = move.date
                move_date_str = move_date.strftime('%Y-%m-%d')  # Convert date to string
                if move_date_str not in day_book_data:
                    day_book_data[move_date_str] = []
                
                for line in move.line_ids:
                    day_book_data[move_date_str].append({
                        'journal': move.journal_id.name,
                        'reference': move.ref if move.ref else None,
                        'account_name': line.account_id.name,
                        'account_code': line.account_id.code,
                        'move':line.move_name,
                        'label':line.name if line.name else None,
                        'partner':line.partner_id.name if line.partner_id.name else None,
                        'debit': round(line.debit, 2),
                        'credit': round(line.credit, 2),
                        'balance': round(line.balance, 2) if line.balance else None
                    })

            # Prepare formatted response
            formatted_day_book ={
                    'day_book': [
                        {'date': date, 'entries': entries}
                        for date, entries in sorted(day_book_data.items())
                    ]
                }

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': formatted_day_book
                    }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except AccessDenied:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': 'Invalid Credentials'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

        except ValueError as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': f'Value Error: {str(e)}'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': f'An unexpected error occurred: {str(e)}'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    @http.route('/trading/api/balance_sheet', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def balance_sheet(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)

            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )

            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            filter_type = json_data.get('filter')
            from_date = json_data.get('from_date')
            to_date = json_data.get('to_date')
            company_id = json_data.get('company_id')  # Get company ID for filtering (optional)
            
            date_to = datetime.now()
            if from_date and to_date: 
                try:
                    date_from = datetime.strptime(from_date, '%Y-%m-%d')
                    date_to = datetime.strptime(to_date, '%Y-%m-%d')
                except ValueError as e:
                    raise ValueError(f'Invalid date format: {str(e)}')
            else:
                if filter_type == 'daily':
                    date_from = date_to - timedelta(days=1)
                elif filter_type == 'weekly':
                    date_from = date_to - timedelta(weeks=1)
                elif filter_type == 'monthly':
                    date_from = date_to - timedelta(days=30)
                elif filter_type == 'yearly':
                    date_from = date_to - timedelta(days=365)
                else:
                    date_from = datetime.min

            # Convert dates to string
            date_from_str = date_from.strftime('%Y-%m-%d')
            date_to_str = date_to.strftime('%Y-%m-%d')

            # Function to calculate balance for an account on a specific date
            def get_account_details(account_id):
                domain = [
                    ('account_id', '=', account_id),
                    ('date', '>=', date_from_str),
                    ('date', '<=', date_to_str),
                ]
                if company_id:
                    domain.append(('company_id', '=', company_id))
                
                move_lines = request.env['account.move.line'].sudo().search(domain)
                debit = sum(move_line.debit for move_line in move_lines)
                credit = sum(move_line.credit for move_line in move_lines)
                balance = round(debit - credit, 2)
                return debit, credit, balance

            # Fetch all accounts (filter by company_id if provided)
            domain = []
            if company_id:
                domain.append(('company_id', '=', company_id))
            
            accounts = request.env['account.account'].sudo().search(domain)
            account_dict = {}
            groups = {}

            # Organize accounts into categories
            for account in accounts:
                debit, credit, balance = get_account_details(account.id)

                if balance != 0: 
                    account_dict[account.id] = {
                        'account_name': account.name,
                        'account_code': account.code,
                        'balance': balance,
                        'debit': round(debit, 2),
                        'credit': round(credit, 2),
                    }

                    internal_group = account.internal_group
                    if internal_group not in groups:
                        groups[internal_group] = {'total': 0, 'accounts': []}
                    
                    groups[internal_group]['total'] += balance
                    groups[internal_group]['accounts'].append(account_dict[account.id])

            # Prepare the hierarchical format
            hierarchical_data = []
            for group, data in groups.items():
                hierarchical_data.append({
                    'group_name': group,
                    'total_assets': round(data['total'], 2),
                    'accounts': data['accounts']
                })

            # Prepare formatted response
            formatted_balance_sheet = {
                'balance_sheet': hierarchical_data
            }
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': formatted_balance_sheet
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )
        except ValueError as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': f'Value Error: {str(e)}'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': f'An unexpected error occurred: {str(e)}'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/trading/api/aged_partner_balance', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def aged_partner_balance(self, **kw):
        """
        API to generate Aged Partner Balance report (Receivable or Payable)
        Required POST data:
        {
            "date_from": "2025-04-25", # Analysis date (required)
            "period_length": 30,        # Period length in days (required)
            "result_selection": "customer", # "customer", "supplier", or "customer_supplier" (required)
            "target_move": "posted",    # "all" or "posted" (required)
            "company_id": 1,            # Company ID (default: from JWT token)
            "journal_ids": [1,2,3]      # Journal IDs to include (optional, default: all)
        }
        """
        hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

        try:
            # 1. Authenticate Request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            request_uid = request.session.uid or auth_status.get('user_id')
            user_company_id = auth_status.get('company_id')
            
            # 2. Parse Request Data
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Invalid JSON data'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            required_fields = ['date_from', 'period_length', 'result_selection', 'target_move']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': f'Missing required fields: {", ".join(missing_fields)}'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            # Get date as string and convert it to date object (not the other way around)
            date_from = data['date_from']  # Keep original string version for later use
            
            # Convert string to date object for the wizard
            # try:
            #     # date_from = fields.Date.from_string(date_from_str)
            # except ValueError:
            #     return request.make_response(
            #         json.dumps({
            #             'status': 'fail',
            #             'data': {'message': 'Invalid date format. Use YYYY-MM-DD'}
            #         }),
            #         headers=[('Content-Type', 'application/json')],
            #         status=400
            #     )
                
            # Period length validation
            period_length = int(data['period_length'])
            if period_length <= 0:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Period length must be greater than 0'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            # Result selection validation
            result_selection = data['result_selection']
            if result_selection not in ['customer', 'supplier', 'customer_supplier']:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Result selection must be one of: customer, supplier, customer_supplier'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            # Target move validation
            target_move = data['target_move']
            if target_move not in ['all', 'posted']:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Target move must be one of: all, posted'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            # Company validation
            company_id = data.get('company_id', user_company_id)
            
            # Journals (optional)
            journal_ids = data.get('journal_ids', [])
            if not isinstance(journal_ids, list):
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Journal IDs must be a list of integers'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # 5. Create Wizard 
            env = request.env(user=request_uid)
            company = env['res.company'].browse(company_id)
            
            # Get all journals if none specified
            if not journal_ids:
                journal_ids = env['account.journal'].search([]).ids
                
            wizard_vals = {
                'date_from': date_from,  # Date object, not string
                'period_length': period_length,
                'result_selection': result_selection,
                'target_move': target_move,
                'company_id': company_id,
                'journal_ids': [(6, 0, journal_ids)],
            }
            
            # Create wizard and call check_report to get the report action
            print('wizard_vals:', wizard_vals)
            wizard = env['account.aged.trial.balance'].sudo().create(wizard_vals)
            report_action = wizard.check_report()
            print('report_action:', report_action)
            # 6. Generate the PDF using the report information from check_report
            report_name = report_action.get('report_name')
            if not report_name:
                report_name = 'base_accounting_kit.report_agedpartnerbalance'
                
            report_data = report_action.get('data', {})
            
            # CRITICAL FIX: Set the active_model and active_id in the environment context
            # This ensures the report's _get_report_values method has the context it needs
            ctx = dict(env.context,
                    active_model='account.aged.trial.balance',
                    active_id=wizard.id,
                    active_ids=[wizard.id],
                    discard_logo_check=True)  # Add discard_logo_check flag
            env_with_context = env(context=ctx)
            print('env_with_context:', env_with_context)
            # Get and render the report with the correct context
            pdf_content, content_type = env_with_context['ir.actions.report'].sudo()._render_qweb_pdf(
                report_name, 
                wizard.ids, 
                data=report_data
            )
            print('pdf_content:', pdf_content)
            
            if not pdf_content:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Failed to generate PDF report'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )
                
            # 7. Store the PDF as an attachment
            # safe_date = date_from.strftime('%Y%m%d')
            attachment_name = f"aged_partner_balance_{result_selection}_{date_from}.pdf"
            
            attachment = env['ir.attachment'].sudo().create({
                'name': attachment_name,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'account.aged.trial.balance',
                'res_id': wizard.id,
                'mimetype': 'application/pdf',
            })
            
            # 8. Generate Download URL
            base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
            file_url = f"/web/content/{attachment.id}?download=true"
            download_url = werkzeug.urls.url_join(base_url, file_url)
            
            # 9. Return Success Response with download link
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': f'Aged Partner Balance report generated successfully',
                        'report_type': result_selection,
                        'analysis_date': date_from,
                        'period_length': period_length,
                        'download_url': download_url
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )
            # return request.make_response(
            #     pdf_content,
            #     headers=[
            #         ('Content-Type', 'application/pdf'),
            #         ('Content-Disposition', f'attachment; filename="{attachment_name}"')
            #     ]
            # )
            
        except (ValueError, TypeError) as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': f'Invalid parameter format: {str(e)}'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
            
        except UserError as ue:
            # Handle specific UserError exceptions from wizard validation
            _logger.warning(f"UserError in aged partner balance: {str(ue)}")
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': str(ue)}
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
            
        except Exception as e:
            _logger.exception("Error generating Aged Partner Balance report")
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': f'An unexpected error occurred: {str(e)}'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )