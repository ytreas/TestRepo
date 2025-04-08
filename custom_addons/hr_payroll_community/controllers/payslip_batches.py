from odoo import http
from odoo.http import request
import json
from . import jwt_token_auth  # Assuming this is your JWT auth module
from datetime import datetime, timedelta

class HrPayslipRunController(http.Controller):

    @http.route('/api/hr_payslip_runs', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_hr_payslip_runs(self, **kwargs):
        # JWT authentication check
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return request.make_response(
                json.dumps(auth_status),
                headers=[('Content-Type', 'application/json')],
                status=status_code
            )

        try:
            # Fetch filters from query parameters
            employee_id = kwargs.get('employee_id')
            company_id = kwargs.get('company_id')
            month = kwargs.get('month')  # New parameter for month

            # Build the domain (search criteria) based on filters
            domain = []

            if employee_id:
                try:
                    domain.append(('slip_ids.employee_id', '=', int(employee_id)))  # Filter by employee_id
                except ValueError:
                    return request.make_response(
                        json.dumps({'error': 'Invalid employee_id format'}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

            if company_id:
                try:
                    domain.append(('slip_ids.company_id', '=', int(company_id)))  # Filter by company_id
                except ValueError:
                    return request.make_response(
                        json.dumps({'error': 'Invalid company_id format'}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

            if month:
                try:
                    month = int(month)
                    year = datetime.now().year  # Use the current year or adjust as needed
                    # Calculate the first and last day of the month
                    first_day_of_month = datetime(year, month, 1)
                    last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    
                    # Add domain filter for month
                    domain.append(('date_start', '>=', first_day_of_month.strftime('%Y-%m-%d')))
                    domain.append(('date_end', '<=', last_day_of_month.strftime('%Y-%m-%d')))
                except ValueError:
                    return request.make_response(
                        json.dumps({'error': 'Invalid month value'}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

            # If no filters are provided, return all payslip runs
            if not domain:
                payslip_runs = request.env['hr.payslip.run'].sudo().search([])
            else:
                # Search for payslip runs with the applied filters
                payslip_runs = request.env['hr.payslip.run'].sudo().search(domain)

            # If no payslip runs are found, return a message
            if not payslip_runs:
                return request.make_response(
                    json.dumps({'message': 'No payslip runs found for the given filters'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Prepare the response data
            payslip_run_data = []
            for payslip_run in payslip_runs:
                # Fetch related payslips
                payslips = payslip_run.slip_ids

                # Prepare payslip data
                payslip_data = []
                for payslip in payslips:
                    payslip_data.append({
                        'id': payslip.id,
                        'name': payslip.name,
                        'number': payslip.number if payslip.number else None,
                        'employee_id': payslip.employee_id.id,  # Employee ID
                        'employee_name': payslip.employee_id.name,  # Employee name
                        'date_from': payslip.date_from.strftime('%Y-%m-%d') if payslip.date_from else None,
                        'date_to': payslip.date_to.strftime('%Y-%m-%d') if payslip.date_to else None,
                        'state': payslip.state,
                        'company_id': payslip.company_id.id,  # Company ID
                        'company_name': payslip.company_id.name,  # Company name
                        'payslip_run_id': payslip.payslip_run_id.id,
                        'payslip_run_name': payslip.payslip_run_id.name
                    })

                payslip_run_data.append({
                    'id': payslip_run.id,
                    'name': payslip_run.name,
                    'state': payslip_run.state,
                    'date_start': payslip_run.date_start.strftime('%Y-%m-%d') if payslip_run.date_start else None,
                    'date_end': payslip_run.date_end.strftime('%Y-%m-%d') if payslip_run.date_end else None,
                    'credit_note': payslip_run.credit_note,
                    'payslips': payslip_data  # Include the related payslip data
                })

            # Return the data as a JSON response
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': payslip_run_data
                }),
                headers=[('Content-Type', 'application/json')]
            )
        
        except Exception as e:
            return request.make_response(
                json.dumps({'error': 'Internal server error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
