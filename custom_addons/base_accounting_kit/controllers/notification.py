import json
import logging
from odoo import http
from odoo.http import request
from . import jwt_token_auth 


_logger = logging.getLogger(__name__)

class NotificationController(http.Controller):

    @http.route('/trading/api/get_notifications', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_notifications(self, **kwargs):
        """Fetch all unread notifications for the authenticated user."""
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            user = request.env.user
            domain = [('user_id', '=', user.id), ('state', '=', 'unread')]
            notifications = request.env['notification.notification'].sudo().search(domain)

            notification_list = []
            for notification in notifications:
                notification_list.append({
                    'id': notification.id,
                    'message': notification.message,
                    'model': notification.model,
                    'record_id': notification.record_id,
                    'state': notification.state,
                    'create_date': notification.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                })

            return request.make_response(
                json.dumps({"status": "success", "data": notification_list}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                content_type='application/json'
            )

    @http.route('/trading/api/mark_notification_as_read', type='http', auth='public', cors="*", methods=['POST'], csrf=False)
    def mark_notification_as_read(self, **kwargs):
        """Mark a specific notification as read."""
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            request_data = json.loads(request.httprequest.data)
            notification_id = request_data.get('notification_id')

            if not notification_id:
                return request.make_response(
                    json.dumps({"status": "fail", "data": {"message": "Notification ID is required"}}),
                    headers=[("Content-Type", "application/json")],
                    status=400
                )

            notification = request.env['notification.notification'].sudo().browse(notification_id)

            if not notification.exists():
                return request.make_response(
                    json.dumps({"status": "fail", "data": {"message": "Notification not found"}}),
                    headers=[("Content-Type", "application/json")],
                    status=404
                )

            notification.mark_as_read()

            return request.make_response(
                json.dumps({"status": "success", "message": "Notification marked as read"}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                content_type='application/json'
            )

    @http.route('/trading/api/subscribe_notifications', type='http', auth='public', cors='*', methods=['POST'], csrf=False)
    def subscribe_notifications(self, **kwargs):
        """
        Subscribe to real-time notifications using Odoo's long-polling bus system.
        """
        try:
            # Authenticate the user via JWT
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                _logger.error(f"Authentication failed: {auth_status}")
                return http.Response(
                    json.dumps(auth_status),
                    status=status_code,
                    headers=[('Content-Type', 'application/json')]
                )
            print("auth_status", auth_status['user_id'])
            user = auth_status['user_id']
            
            user_channel = f'notification_channel_{user}'
            _logger.info(f"Subscribed user: {user} to channel: {user_channel}")

            # Poll for notifications from the bus system
            notifications = request.env['bus.bus']._poll([user_channel])
            _logger.info(f"Fetched notifications: {notifications}")

            # Return the notifications to the client
            return http.Response(
                json.dumps({"status": "success", "notifications": notifications}),
                status=200,
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            _logger.error(f"Error in subscription: {e}")
            return http.Response(
                json.dumps({"status": "fail", "message": str(e)}),
                status=400,
                headers=[("Content-Type", "application/json")]
            )
