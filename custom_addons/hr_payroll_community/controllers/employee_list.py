from odoo import http
from odoo.http import request
import json
from . import jwt_token_auth  # Assuming you are using a JWT auth module

class HREmployeeController(http.Controller):

    @http.route('/api/hr/employee', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_hr_employees(self, **kwargs):
        # JWT authentication check (if required)
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return request.make_response(
                json.dumps(auth_status),
                headers={'Content-Type': 'application/json'},
                status=status_code
            )

        # Initialize an empty domain for search filters
        domain = []

        # Optional filter: employee_id
        employee_id = kwargs.get('employee_id')
        if employee_id:
            try:
                employee_id = int(employee_id)
                domain.append(('id', '=', employee_id))
            except ValueError:
                return request.make_response(
                    json.dumps({'error': 'Invalid employee_id format'}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )

        # Fetch employees based on the domain filters
        employees = request.env['hr.employee'].sudo().search(domain)

        # If no employees are found, return a 404 response
        if not employees:
            return request.make_response(
                json.dumps({'message': 'No employees found matching the provided filters'}),
                headers={'Content-Type': 'application/json'},
                status=404
            )

        # Prepare the response data
        employee_data = []
        for employee in employees:
            # Fetch the related contract for each employee
            contract = request.env['hr.contract'].sudo().search([('employee_id', '=', employee.id)], limit=1)

            # Prepare basic info
            basic_info = {
                "id": employee.id,
                "name": f"Salary Slip of {employee.name} for {request.env.context.get('salary_period', 'current month')}",
                "number": f"SLIP/{employee.id:03}",  # Assuming the slip number format
                "employee_id": employee.id,
                "employee_name": employee.name,
                "company_id": employee.company_id.id if employee.company_id else None,
                "company_name": employee.company_id.name if employee.company_id else None,
                "date_from": request.env.context.get('date_from', '2024-09-01'),  # Example date
                "date_to": request.env.context.get('date_to', '2024-09-30')  # Example date
            }

            # Prepare accounting info with nested salary info
            salary_info = {
                "wage": contract.wage if contract else 0.0,
                "hra": contract.hra if contract else 0.0,
                "travel_allowance": contract.travel_allowance if contract else 0.0,
                "da": contract.da if contract else 0.0,
                "meal_allowance": contract.meal_allowance if contract else 0.0,
                "medical_allowance": contract.medical_allowance if contract else 0.0,
                "other_allowance": contract.other_allowance if contract else 0.0,
            }

            accounting_info = {
                "state": "done",  # Replace with actual state if needed
                "paid": None,
                "note": None,
                "contract_id": contract.id if contract else None,
                "contract_name": contract.name if contract else "pay contract",
                # "credit_note": None,
                # "payslip_run_id": None,  # Replace with actual ID if needed
                "payslip_count": 3,  # Example count, replace as needed
                # "overtime_hr": 0.0,  # Replace with actual overtime hours if applicable
                "salary_info": salary_info
            }

            # Append the structured data
            employee_data.append({
                "basic_info": basic_info,
                "accounting_info": accounting_info
            })

        # Return the data as a JSON response
        return request.make_response(
            json.dumps({
                'status': 'success',
                'data': employee_data
            }),
            headers=[
                ('Content-Type', 'application/json')
            ],
            status=200
        )
