from odoo import http, fields
from odoo.http import request
import json
from datetime import datetime, timedelta, timezone
from . import jwt_token_auth
import re

class GemPaymentAPI(http.Controller):

    @http.route('/api/create_withdraw_payment', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def create_withdraw_payment(self, **kwargs):
        try:
            print("Create Withdraw Payment API called")
            # Authenticate request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user_id = auth_status.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)
            
            # Get request data
            try:
                request_data = json.loads(request.httprequest.data)
            except:
                request_data = request.params
            
            gems = int(request_data.get('gems', 0))
            amount = float(request_data.get('amount', 0))
            phone = request_data.get('phone', '')
            payment_provider = request_data.get('payment_provider')
            
            # Validate input
            if gems <= 0:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Gems must be a positive number'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            if amount <= 0:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Amount must be positive'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            if not phone:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Phone number is required'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Additional phone number validations
            if not phone.isdigit():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Phone number must contain only digits'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            if len(phone) != 10:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Phone number must be exactly 10 digits long'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            if not phone.startswith('9'):
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Phone number must start with 9'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            # Check user has enough gems
            if user.gems < gems:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Insufficient gems balance'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Create withdrawal payment
            payment = request.env['gem.payment'].sudo().create({
                'user_id': user.id,
                'gems': -gems,  # Negative for withdrawals
                'amount': amount,
                'phone': phone,
                'payment_provider': payment_provider,
                'status': 'pending',
            })
            
            # Deduct gems immediately
            user.write({'gems': user.gems - gems})
            
            # Create gem log
            request.env['gem.logs'].sudo().create({
                'user_id': user.id,
                'change_type': 'withdraw',
                'gems_changed': -gems,
                'date': fields.Datetime.now(),
            })
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Withdrawal request created successfully',
                        'payment_id': payment.id,
                        # 'reference': payment.name,
                        'remaining_gems': user.gems
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
                    'data': {'message': str(e)}
                }),
                content_type="application/json"
            )

    @http.route('/api/get_withdraw_payments', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def get_withdraw_payments(self, **kwargs):
        try:
            print("Get Withdraw Payments API called")
            # Authenticate request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user_id = auth_status.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)
            
            # Get optional filters
            status = kwargs.get('status')
            limit = int(kwargs.get('limit', 10))
            offset = int(kwargs.get('offset', 0))
            
            # Build domain
            domain = [('user_id', '=', user.id), ('gems', '<', 0)]  # Only withdrawals
            if status:
                domain.append(('status', '=', status))
                
            # Query payments
            payments = request.env['gem.payment'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='create_date desc'
            )
            
            # Format response
            payment_data = []
            for payment in payments:
                payment_data.append({
                    'id': payment.id,
                    # 'reference': payment.name,
                    'gems': payment.gems,  # Return positive number
                    'amount': payment.amount,
                    'status': payment.status,
                    'date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else None,
                    'phone': payment.phone
                })
                
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'payments': payment_data,
                        'total': len(payment_data),
                        'remaining_gems': user.gems
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
                    'data': {'message': str(e)}
                }),
                content_type="application/json"
            )

    @http.route('/api/approve_withdraw_payment', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def approve_withdraw_payment(self, **kwargs):
        try:
            print(f"Approve Withdraw Payment API called")
            # Authenticate request (admin only)
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            print(f"Auth Status: {auth_status}")
            # Check if user has admin privileges
            user_id = auth_status.get('user_id')
            admin_user = request.env['res.users'].sudo().browse(user_id)
            if not admin_user.has_group('base.group_system'):  # Adjust to your admin group
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Only administrators can approve withdrawals'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )
            print(f"Admin User: {admin_user.name} (ID: {admin_user.id})")
            try:
                request_data = json.loads(request.httprequest.data)
            except:
                request_data = request.params
            print(f"Request Data: {request_data}")
            payment_id = int(request_data.get('id'))
            print(f"Payment ID: {payment_id}")
            if not payment_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Payment ID is required'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            # Get the payment record
            payment = request.env['gem.payment'].sudo().browse(payment_id)
            if not payment.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Payment not found'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Validate payment status
            if payment.status != 'pending':
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': f'Payment is already {payment.status}'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Validate it's a withdrawal (negative gems)
            if payment.gems >= 0:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Only withdrawal payments can be approved'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Check if user still has enough gems (in case balance changed)
            user = payment.user_id
            gems_to_deduct = abs(payment.gems)

            # Process the approval
            payment.write({
                'status': 'completed',
                'payment_date': fields.Datetime.now()
            })
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': f'Withdrawal of {gems_to_deduct} gems approved',
                        'payment_id': payment.id,
                        # 'reference': payment.name,
                        'user_id': user.id,
                        'user_remaining_gems': user.gems - gems_to_deduct
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
                    'data': {'message': str(e)}
                }),
                content_type="application/json"
            )

    @http.route('/api/reject_withdraw_payment', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def reject_withdraw_payment(self, **kwargs):
        try:
            print(f"Reject Withdraw Payment API called")
            # Authenticate request (admin only)
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Check if user has admin privileges
            user_id = auth_status.get('user_id')
            admin_user = request.env['res.users'].sudo().browse(user_id)
            if not admin_user.has_group('base.group_system'):  # Adjust to your admin group
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Only administrators can reject withdrawals'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )

            # Get the payment record
            try:
                request_data = json.loads(request.httprequest.data)
            except:
                request_data = request.params
            
            payment_id = int(request_data.get('id'))
            if not payment_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Payment ID is required'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            payment = request.env['gem.payment'].sudo().browse(payment_id)
            if not payment.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Payment not found'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Validate payment status
            if payment.status != 'pending':
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': f'Payment is already {payment.status}'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Validate it's a withdrawal (negative gems)
            if payment.gems >= 0:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Only withdrawal payments can be rejected'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            user = payment.user_id
            gems_to_refund = abs(payment.gems)

            # Process the rejection
            payment.write({
                'status': 'failed',
                'payment_date': fields.Datetime.now()
            })

            # Refund gems back to user
            user.write({'gems': user.gems + gems_to_refund})

            # Create gem log entry for refund
            request.env['gem.logs'].sudo().create({
                'user_id': user.id,
                'change_type': 'withdraw_rejected',
                'gems_changed': gems_to_refund,
                'date': fields.Datetime.now(),
            })

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': f'Withdrawal of {gems_to_refund} gems rejected and refunded',
                        'payment_id': payment.id,
                        'user_id': user.id,
                        'user_new_balance': user.gems,
                        'refunded_gems': gems_to_refund
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
                    'data': {'message': str(e)}
                }),
                content_type="application/json"
            )

    @http.route('/api/get_payment_withdraw_admin_pending', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def get_payment_withdraw_admin(self, **kwargs):
        try:
            print("Admin Get Withdraw Payments API called")
            # Authenticate request (admin only)
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Check if user has admin privileges
            user_id = auth_status.get('user_id')
            admin_user = request.env['res.users'].sudo().browse(user_id)
            if not admin_user.has_group('base.group_system'):  # Adjust to your admin group
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Only administrators can access this endpoint'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )

            # Optional filter by specific user
            user_filter = [('user_id', '=', int(kwargs['user_id']))] if kwargs.get('user_id') else []
            
            # Get ALL pending withdrawals (no limit)
            payments = request.env['gem.payment'].sudo().search(
                [('gems', '<', 0), ('status', '=', 'pending')] + user_filter,
                order='create_date desc'
            )
            
            # Format response with proper datetime serialization
            payment_data = []
            for payment in payments:
                payment_data.append({
                    'id': payment.id,
                    'gems': abs(payment.gems),
                    'amount': payment.amount,
                    'phone': payment.phone,
                    'status': payment.status,
                    'date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else None,
                    'created_date': payment.create_date.strftime('%Y-%m-%d %H:%M:%S') if payment.create_date else None,
                    'user': {
                        'id': payment.user_id.id,
                        'name': payment.user_id.name
                    }
                })
                
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'payments': payment_data,
                        'total': len(payment_data)
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
                    'data': {'message': str(e)}
                }),
                content_type="application/json"
            )

    @http.route('/api/get_payment_withdraw_admin_all', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def get_payment_withdraw_admin_all(self, **kwargs):
        try:
            print("Admin Get Withdraw Payments API called")
            # Authenticate request (admin only)
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Check if user has admin privileges
            user_id = auth_status.get('user_id')
            admin_user = request.env['res.users'].sudo().browse(user_id)
            if not admin_user.has_group('base.group_system'):  # Adjust to your admin group
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {'message': 'Only administrators can access this endpoint'}
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )

            # Optional filter by specific user
            user_filter = [('user_id', '=', int(kwargs['user_id']))] if kwargs.get('user_id') else []
            print(f"User Filter: {user_filter}")
            
            # Get ALL pending withdrawals (no limit)
            payments = request.env['gem.payment'].sudo().search(
                [('gems', '<', 0)] + user_filter,
                order='create_date desc'
            )
            
            # Format response with proper datetime serialization
            payment_data = []
            for payment in payments:
                payment_data.append({
                    'id': payment.id,
                    'gems': abs(payment.gems),
                    'amount': payment.amount,
                    'phone': payment.phone,
                    'status': payment.status,
                    'date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else None,
                    'created_date': payment.create_date.strftime('%Y-%m-%d %H:%M:%S') if payment.create_date else None,
                    'user': {
                        'id': payment.user_id.id,
                        'name': payment.user_id.name
                    }
                })
                
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'payments': payment_data,
                        'total': len(payment_data)
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
                    'data': {'message': str(e)}
                }),
                content_type="application/json"
            )