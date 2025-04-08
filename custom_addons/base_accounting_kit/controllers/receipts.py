from odoo import http
from odoo.http import request
import json
import logging
import jwt
from . import jwt_token_auth
from datetime import datetime

_logger = logging.getLogger(__name__)

class AccountMoveController(http.Controller):

    @http.route('/api/account/receipt', type='http', auth='public',cors="*", methods=['GET'], csrf=False)
    def get_account_moves(self, **kwargs):
        
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Filter account moves based on any provided criteria (optional)
            domain = []
            if 'state' in kwargs:
                domain.append(('state', '=', kwargs.get('state')))
            if 'payment_state' in kwargs:
                domain.append(('payment_state', '=', kwargs.get('payment_state')))
            if 'partner' in kwargs:
                domain.append(('invoice_partner_display_name', 'ilike', kwargs.get('partner')))
            account_moves = request.env['account.move'].sudo().search(domain)
            if not account_moves:
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'No account moves found'}),
                    headers={'Content-Type': 'application/json'},
                    status=404
                )

            # Prepare the response
            account_move_data = []
            for move in account_moves:
                move_data = { 
                    'name': move.name,
                    'invoice_partner_display_name': move.invoice_partner_display_name,
                    'invoice_date_due': move.invoice_date_due.strftime('%Y-%m-%d') if move.invoice_date_due else None,
                    'date_range_fy_id': move.date_range_fy_id.name if move.date_range_fy_id else None,
                    'ref': move.ref if move.ref else None,
                    'activity_ids': [activity.id for activity in move.activity_ids] if move.activity_ids else None,
                    'amount_untaxed_signed': move.amount_untaxed_signed,
                    'amount_total_signed': move.amount_total_signed,
                    'payment_state': move.payment_state,
                    'state': move.state,
                }
                account_move_data.append(move_data)

            # Return the response
            return request.make_response(
                json.dumps({'status': 'success', 'data': account_move_data}),
                headers={'Content-Type': 'application/json'},
                status=200
            )

        except Exception as e:
            _logger.error(f"Error fetching account moves: {e}")
            return request.make_response(
                json.dumps({'status': 'fail', 'message': f'Error fetching account moves: {str(e)}'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )
