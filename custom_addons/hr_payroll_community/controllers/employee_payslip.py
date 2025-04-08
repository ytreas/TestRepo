from odoo import http
from odoo.http import request
import json
from . import jwt_token_auth  # Assuming JWT authentication is implemented in this module
from datetime import datetime, timedelta

class HrPayslipController(http.Controller):

    @http.route('/api/hr_payslips', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_hr_payslips(self, **kwargs):
        # JWT authentication check
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return request.make_response(
                json.dumps(auth_status),
                headers=[('Content-Type', 'application/json')],
                status=status_code
            )

        # Fetch filters from query parameters
        employee_id = kwargs.get('employee_id')
        company_id = kwargs.get('company_id')
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        month = kwargs.get('month')  # New parameter for month

        # Build domain (search criteria) for filtering payslips
        domain = []
        if employee_id:
            domain.append(('employee_id', '=', int(employee_id)))
        if company_id:
            domain.append(('company_id.id', '=', int(company_id)))  # Search by company ID
        if date_from:
            domain.append(('date_from', '>=', date_from))
        if date_to:
            domain.append(('date_to', '<=', date_to))
        if month:
            try:
                # Convert the month parameter to an integer
                month = int(month)
                year = datetime.now().year  # Use the current year or adjust as needed
                # Calculate the first and last day of the month
                first_day_of_month = datetime(year, month, 1)
                last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                
                # Add domain filter for month
                domain.append(('date_from', '>=', first_day_of_month.strftime('%Y-%m-%d')))
                domain.append(('date_to', '<=', last_day_of_month.strftime('%Y-%m-%d')))
            except ValueError:
                return request.make_response(
                    json.dumps({'message': 'Invalid month value'}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )

        # Fetch payslips based on filters or return all if no filters are provided
        payslips = request.env['hr.payslip'].sudo().search(domain) if domain else request.env['hr.payslip'].sudo().search([])

        # If no payslips found, return a validation message
        if not payslips:
            return request.make_response(
                json.dumps({'message': 'No payslips found'}),
                headers={'Content-Type': 'application/json'},
                status=404
            )

        # Prepare the response data
        payslip_data = []
        for payslip in payslips:
            basic_info = {
                'id': payslip.id,
                'name': payslip.name,
                'number': payslip.number,
                'employee_id': payslip.employee_id.id,
                'employee_name': payslip.employee_id.name,
                'company_id': payslip.company_id.id,
                'company_name': payslip.company_id.name,
                'date_from': payslip.date_from.strftime('%Y-%m-%d') if payslip.date_from else None,
                'date_to': payslip.date_to.strftime('%Y-%m-%d') if payslip.date_to else None
            }

            accounting_info = {
                'state': payslip.state,
                'paid': payslip.paid if payslip.paid else None,
                'note': payslip.note if payslip.note else None,
                'contract_id': payslip.contract_id.id if payslip.contract_id else None,
                'contract_name': payslip.contract_id.name if payslip.contract_id else None,
                'credit_note': payslip.credit_note if payslip.credit_note else None,
                'payslip_run_id': payslip.payslip_run_id.id if payslip.payslip_run_id else None,
                'payslip_count': payslip.payslip_count,
                'overtime_hr': payslip.overtime_hr
            }

            payslip_data.append({
                'basic_info': basic_info,
                'accounting_info': accounting_info
            })

        # Return the filtered data or all payslips as a JSON response
        return request.make_response(
            json.dumps({
                'status': 'success',
                'data': payslip_data
            }),
            headers={
                'Content-Type': 'application/json'
            }
        )
