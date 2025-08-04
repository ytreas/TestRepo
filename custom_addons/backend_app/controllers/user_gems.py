from odoo import http,fields
from odoo.http import request
from datetime import datetime, timedelta, timezone
import json
from . import jwt_token_auth
import logging
_logger = logging.getLogger(__name__)

class GemsAPI(http.Controller):

    @http.route('/api/claim_gems', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def claim_gems(self, **kwargs):
        try:
            print("Claim Gems API called")
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            print("Auth Status:", auth_status)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user_id = auth_status.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)


            now_utc = datetime.now(timezone.utc)
            gmt_plus_445 = now_utc + timedelta(hours=4, minutes=45)
            today_date = gmt_plus_445.date()
            today_weekday = today_date.weekday()  # Monday = 0, Sunday = 6

            # Fix: map to Sun (0) - Sat (6)
            sunday_based_index = (today_weekday + 1) % 7

            last_claim = user.last_gem_claim_date
            streak = user.gems_streak or 0

            # Load claimed days this week
            try:
                claimed_days = json.loads(user.claimed_days_json or '{}')
            except json.JSONDecodeError:
                claimed_days = {}
            print(f"Claimed Days: {claimed_days}")
            if not last_claim:
                reset_streak = True
            else:
                last_claim_local = last_claim.astimezone(timezone(timedelta(hours=4, minutes=45)))
                last_claim_date = last_claim_local.date()
                delta_days = (today_date - last_claim_date).days
                full_week_status = {str(i): claimed_days.get(str(i), False) for i in range(7)}

                if delta_days == 0:
                    return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data': {
                                'message': 'You already claimed your gems today.',
                                'weekly_claim_status': full_week_status
                            }
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )
                elif delta_days == 1:
                    reset_streak = False
                else:
                    reset_streak = True

            if reset_streak:
                streak = 0
                claimed_days = {}  # reset the week's claims

            streak += 1

            reward_table = [10, 20, 30, 40, 50, 60, 100]
            reward = reward_table[streak - 1] if streak <= 7 else 10
            if streak > 7:
                streak = 1  # reset streak after 7th day

            # Update claimed day
            claimed_days[str(sunday_based_index)] = True  # mark current day as claimed
            print(f"Updated Claimed Days: {claimed_days}")
            print("user",user.id)
            user.write({
                'gems': user.gems + reward,
                'gems_streak': streak,
                'last_gem_claim_date': now_utc.replace(tzinfo=None),
                'claimed_days_json': json.dumps(claimed_days)
            })
            print(f"User {user.name} claimed {reward} gems. New total: {user.gems}")
            # Log the gem reward
            request.env['gem.logs'].sudo().create({
                'user_id': user.id,
                'change_type': 'claim',
                'gems_changed': reward,
                'date': fields.Datetime.now(),
            })

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': f'{reward} gems claimed successfully.',
                        'total_gems': user.gems,
                        'streak': streak,
                        'weekly_claim_status': {
                            'sun': claimed_days.get("0", False),
                            'mon': claimed_days.get("1", False),
                            'tue': claimed_days.get("2", False),
                            'wed': claimed_days.get("3", False),
                            'thu': claimed_days.get("4", False),
                            'fri': claimed_days.get("5", False),
                            'sat': claimed_days.get("6", False),
                        }
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            return http.Response(
                status=500,
                response=json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': str(e)
                    }
                }),
                content_type="application/json"
            )

    @http.route('/api/gems_status', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def gems_status(self, **kwargs):
        try:
            print("Gems Status API called")
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            print("Auth Status:", auth_status)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user_id = auth_status.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)

            # Load claimed days
            try:
                claimed_days = json.loads(user.claimed_days_json or '{}')
            except json.JSONDecodeError:
                claimed_days = {}

            weekly_claim_status = {
                'sun': claimed_days.get("0", False),
                'mon': claimed_days.get("1", False),
                'tue': claimed_days.get("2", False),
                'wed': claimed_days.get("3", False),
                'thu': claimed_days.get("4", False),
                'fri': claimed_days.get("5", False),
                'sat': claimed_days.get("6", False),
            }

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'total_gems': user.gems,
                        'streak': user.gems_streak or 0,
                        'weekly_claim_status': weekly_claim_status
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            return http.Response(
                status=500,
                response=json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': str(e)
                    }
                }),
                content_type="application/json"
            )

    @http.route('/api/gem_logs', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def get_gem_logs(self, **kwargs):
        """
        API to get gem logs for the authenticated user
        Optional POST data:
        {
            "date_from": "2025-07-01",  # optional
            "date_to": "2025-07-25"     # optional
        }
        """
        try:
            # 1. Authenticate using JWT
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user_id = auth_status.get('user_id')
            env = request.env(user=user_id)

            # 2. Parse input JSON
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Invalid JSON format'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # 3. Build domain filters
            domain = [('user_id', '=', user_id)]
            date_from_str = data.get('date_from')
            date_to_str = data.get('date_to')

            if date_from_str:
                try:
                    date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                    domain.append(('date', '>=', date_from))
                except ValueError:
                    return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data': {'message': 'Invalid date_from format. Use YYYY-MM-DD'}
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

            if date_to_str:
                try:
                    date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                    domain.append(('date', '<=', date_to))
                except ValueError:
                    return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data': {'message': 'Invalid date_to format. Use YYYY-MM-DD'}
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

            # 4. Query logs
            logs = env['gem.logs'].sudo().search(domain, order='date desc')

            log_data = [{
                'id': log.id,
                'change_type': log.change_type,
                'gems_changed': log.gems_changed,
                'date': log.date.strftime('%Y-%m-%d %H:%M:%S')
            } for log in logs]

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'logs': log_data,
                        'count': len(log_data)
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.exception("Unexpected error in gem log API")
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {'message': f'Unexpected server error: {str(e)}'}
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/api/gem_logs', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def get_gem_logs(self, **kwargs):
        """
        API to get paginated gem logs for the authenticated user
        Optional POST data:
        {
            "date_from": "2025-07-01",  # optional
            "date_to": "2025-07-25",    # optional
            "page": 1,                  # optional, default 1
            "limit": 20                 # optional, default 20
        }
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
            env = request.env(user=user_id)

            # 2. Parse JSON
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Invalid JSON format'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # 3. Extract and validate pagination
            page = int(data.get('page', 1))
            limit = int(data.get('limit', 20))
            if page < 1 or limit < 1:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Page and limit must be >= 1'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            offset = (page - 1) * limit

            # 4. Build domain
            domain = [('user_id', '=', user_id)]
            date_from_str = data.get('date_from')
            date_to_str = data.get('date_to')

            if date_from_str:
                try:
                    date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                    domain.append(('date', '>=', date_from))
                except ValueError:
                    return request.make_response(
                        json.dumps({'status': 'fail', 'data': {'message': 'Invalid date_from format. Use YYYY-MM-DD'}}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

            if date_to_str:
                try:
                    date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                    domain.append(('date', '<=', date_to))
                except ValueError:
                    return request.make_response(
                        json.dumps({'status': 'fail', 'data': {'message': 'Invalid date_to format. Use YYYY-MM-DD'}}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

            # 5. Query with pagination
            total_logs = env['gem.logs'].sudo().search_count(domain)
            logs = env['gem.logs'].sudo().search(domain, order='date desc', offset=offset, limit=limit)

            log_data = [{
                'id': log.id,
                'change_type': log.change_type,
                'gems_changed': log.gems_changed,
                'date': log.date.strftime('%Y-%m-%d %H:%M:%S')
            } for log in logs]

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'logs': log_data,
                        'count': len(log_data),
                        'total': total_logs,
                        'page': page,
                        'limit': limit,
                        'pages': (total_logs + limit - 1) // limit
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.exception("Unexpected error in gem log API")
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': f'Unexpected server error: {str(e)}'}}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
