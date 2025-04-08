from odoo import http
from odoo.http import request
import json
from datetime import datetime, timedelta
from . import jwt_token_auth  # Assuming this is your JWT auth module

class HrLeaveController(http.Controller):

    @http.route('/api/payroll/timeoff', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_hr_leaves(self, **kwargs):
        # JWT authentication check
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return request.make_response(
                json.dumps(auth_status),
                headers={'Content-Type': 'application/json'},
                status=status_code
            )

        # Initialize empty domain for search filters
        domain = []

        # Optional filter: holiday_type
        holiday_type = kwargs.get('holiday_type')
        if holiday_type:
            if holiday_type not in ['employee', 'company', 'department', 'category']:
                return request.make_response(
                    json.dumps({'error': 'Invalid holiday_type'}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )
            domain.append(('holiday_type', '=', holiday_type))

        # Optional filter: employee_id
        employee_id = kwargs.get('employee_id')
        if employee_id:
            try:
                employee_id = int(employee_id)
                domain.append(('employee_ids', 'in', [employee_id]))
            except ValueError:
                return request.make_response(
                    json.dumps({'error': 'Invalid employee_id format'}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )

        # Optional filter: date_from
        date_from = kwargs.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                domain.append(('request_date_from', '>=', date_from.strftime('%Y-%m-%d')))
            except ValueError:
                return request.make_response(
                    json.dumps({'error': 'Invalid date_from format, expected YYYY-MM-DD'}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )

        # Optional filter: date_to
        date_to = kwargs.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d')
                domain.append(('request_date_to', '<=', date_to.strftime('%Y-%m-%d')))
            except ValueError:
                return request.make_response(
                    json.dumps({'error': 'Invalid date_to format, expected YYYY-MM-DD'}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )

        # Optional filter: month
        month = kwargs.get('month')
        if month:
            try:
                month = int(month)
                year = datetime.now().year  # Use the current year or adjust as needed
                first_day_of_month = datetime(year, month, 1)
                last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                
                # Add domain filter for month
                domain.append(('request_date_from', '>=', first_day_of_month.strftime('%Y-%m-%d')))
                domain.append(('request_date_to', '<=', last_day_of_month.strftime('%Y-%m-%d')))
            except ValueError:
                return request.make_response(
                    json.dumps({'error': 'Invalid month value'}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )

        # Fetch leave records based on the domain filters
        leaves = request.env['hr.leave'].sudo().search(domain)

        # Prepare the response data
        leave_data = []
        for leave in leaves:
            leave_data.append({
                'id': leave.id,
                'holiday_type': leave.holiday_type,
                'employee_ids': [{'id': emp.id, 'name': emp.name} for emp in leave.employee_ids],
                'holiday_status_id': leave.holiday_status_id.name,
                'request_date_from': leave.request_date_from.strftime('%Y-%m-%d') if leave.request_date_from else None,
                'request_date_to': leave.request_date_to.strftime('%Y-%m-%d') if leave.request_date_to else None,
                'request_unit_half': leave.request_unit_half if leave.request_unit_half else None,
                'request_unit_hours': leave.request_unit_hours if leave.request_unit_hours else None,
                'name': leave.name
            })

        # Return the data as a JSON response
        return request.make_response(
            json.dumps({
                'status': 'success',
                'data': leave_data
            }),
            headers={'Content-Type': 'application/json'}
        )
