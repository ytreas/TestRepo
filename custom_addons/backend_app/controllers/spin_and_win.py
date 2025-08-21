from odoo import http, fields
from odoo.http import request
import json, random
from datetime import datetime, timedelta, timezone
from . import jwt_token_auth
import logging
_logger = logging.getLogger(__name__)

class SpinAPI(http.Controller):

    @http.route('/api/spin_and_win', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def spin_and_win(self, **kwargs):
        """
        POST API for Spin and Win (Hardcoded prizes + daily spin limit).
        Daily limit: 10 spins per user (Nepali Time UTC+4:45)
        """
        try:
            # 1. Authenticate
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user_id = auth_status.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)

            # 2. Hardcoded prize list (total 99% chance + 1% no win auto)
            prizes = [
                {"amount": 10, "chance": 14},
                {"amount": 20, "chance": 14},
                {"amount": 30, "chance": 14},
                {"amount": 40, "chance": 14},
                {"amount": 50, "chance": 14},
                {"amount": 60, "chance": 14},
                {"amount": 70, "chance": 14},
                {"amount": 1000, "chance": 1}  # jackpot
            ]

            # 3. Check daily spin limit (Nepali time)
            now_utc = datetime.now(timezone.utc)
            nepali_now = now_utc + timedelta(hours=4, minutes=45)
            nepali_start_of_day = datetime(nepali_now.year, nepali_now.month, nepali_now.day, tzinfo=nepali_now.tzinfo)
            nepali_start_of_day_utc = nepali_start_of_day - timedelta(hours=4, minutes=45)

            today_spins = request.env['gem.logs'].sudo().search_count([
                ('user_id', '=', user.id),
                ('change_type', '=', 'spin_win'),
                ('date', '>=', nepali_start_of_day_utc)
            ])

            if today_spins >= 100:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Daily spin limit reached (10 spins per day)'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # 4. Weighted random selection
            choices = [p['amount'] for p in prizes]
            weights = [p['chance'] for p in prizes]

            if sum(weights) < 100:
                choices.append(0)
                weights.append(100 - sum(weights))

            selected_amount = random.choices(choices, weights=weights, k=1)[0]

            # Log the spin attempt
            # request.env['gem.logs'].sudo().create({
            #     'user_id': user.id,
            #     'change_type': 'spin_attempt',
            #     'gems_changed': 0,
            #     'date': fields.Datetime.now(),
            # })

            # 5. Update user gems if win
            if selected_amount > 0:
                user.write({'gems': user.gems + selected_amount})

                # Log win separately
                request.env['gem.logs'].sudo().create({
                    'user_id': user.id,
                    'change_type': 'spin_win',
                    'gems_changed': selected_amount,
                    'date': fields.Datetime.now(),
                })

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'prize_won': selected_amount,
                        'total_gems': user.gems,
                        'message': f'You won {selected_amount} gems!' if selected_amount > 0 else 'Better luck next time!'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.exception("Unexpected error in spin_and_win API")
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': f'Unexpected server error: {str(e)}'}}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

class ConnectDotAPI(http.Controller):

    @http.route('/api/connect_dot', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def connect_dot(self, **kwargs):
        """
        POST API for Connect Dot game.
        - Gives user 10 gems per successful connect.
        - Limit: 10 connects per day (Nepali Time UTC+4:45).
        """
        try:
            # 1. Authenticate
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user_id = auth_status.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)

            # 2. Time check for daily limit (Nepali time)
            now_utc = datetime.now(timezone.utc)
            nepali_now = now_utc + timedelta(hours=4, minutes=45)
            nepali_start_of_day = datetime(nepali_now.year, nepali_now.month, nepali_now.day, tzinfo=nepali_now.tzinfo)
            nepali_start_of_day_utc = nepali_start_of_day - timedelta(hours=4, minutes=45)

            today_connects = request.env['gem.logs'].sudo().search_count([
                ('user_id', '=', user.id),
                ('change_type', '=', 'connect_dot'),
                ('date', '>=', nepali_start_of_day_utc)
            ])

            if today_connects >= 10:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Daily connect limit reached (10 per day)'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # 3. Award gems
            gems_to_add = 10
            user.write({'gems': user.gems + gems_to_add})

            # 4. Log the connect
            request.env['gem.logs'].sudo().create({
                'user_id': user.id,
                'change_type': 'connect_dot',
                'gems_changed': gems_to_add,
                'date': fields.Datetime.now(),
            })

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'gems_added': gems_to_add,
                        'total_gems': user.gems,
                        'message': f'You earned {gems_to_add} gems!'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.exception("Unexpected error in connect_dot API")
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': f'Unexpected server error: {str(e)}'}}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
