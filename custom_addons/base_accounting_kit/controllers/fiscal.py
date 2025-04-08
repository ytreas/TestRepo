from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime
from odoo.exceptions import ValidationError
from . import jwt_token_auth

_logger = logging.getLogger(__name__)

class FiscalYearController(http.Controller):

    # GET API to retrieve fiscal year details
    @http.route('/api/account/fiscal_get', type='http', auth='public', methods=['GET'], csrf=False)
    def get_fiscal_years(self, **kwargs):
        try:
            # Authenticate using JWT
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers={'Content-Type': 'application/json'},
                    status=status_code
                )

            # Filter fiscal years if optional parameters are passed
            domain = []
            company_id = auth_status['company_id']
            if company_id:
                domain.append(('company_id.id', '=', company_id))
            if 'name' in kwargs:
                domain.append(('name', 'ilike', kwargs.get('name')))
            if 'name_np' in kwargs:
                domain.append(('name_np', 'ilike', kwargs.get('name_np')))

            fiscal_years = request.env['account.fiscal.year'].sudo().search(domain)
            if not fiscal_years:
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'No fiscal years found'}),
                    headers={'Content-Type': 'application/json'},
                    status=404
                )

            # Prepare the response
            fiscal_year_data = []
            for fy in fiscal_years:
                fy_data = {
                    'id': fy.id, 
                    'name': fy.name if fy.name else None,
                    'name_np': fy.name_np if fy.name_np else None,
                    'date_from': fy.date_from.strftime('%Y-%m-%d') if fy.date_from else None,
                    'date_to': fy.date_to.strftime('%Y-%m-%d') if fy.date_to else None,
                    'date_from_bs': fy.date_from_bs if fy.date_from_bs else None,
                    'date_to_bs': fy.date_to_bs if fy.date_to_bs else None,
                    'company_id': fy.company_id.id if fy.company_id else None,
                }
                fiscal_year_data.append(fy_data)

            # Return the response
            return request.make_response(
                json.dumps({'status': 'success', 'data': fiscal_year_data}),
                headers={'Content-Type': 'application/json'},
                status=200
            )

        except Exception as e:
            _logger.error(f"Error fetching fiscal years: {e}")
            return request.make_response(
                json.dumps({'status': 'fail', 'message': f'Error fetching fiscal years: {str(e)}'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )

    # POST API to create a new fiscal year
    @http.route('/api/account/fiscal_post', type='http', auth='public', methods=['POST'], csrf=False)
    def create_fiscal_year(self, **kwargs):
        try:
            # Authenticate using JWT
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers={'Content-Type': 'application/json'},
                    status=status_code
                )

            # Get raw data from the request body
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            # Extract required fields from the request data
            name = json_data.get('name')
            name_np = json_data.get('name_np')
            date_from = json_data.get('date_from')
            date_to = json_data.get('date_to')
            date_from_bs = json_data.get('date_from_bs')
            date_to_bs = json_data.get('date_to_bs')

            # Validation
            if not name or not date_from or not date_to or not date_from_bs or not date_to_bs:
                raise ValidationError("The fields 'name', 'date_from', 'date_from_bs', 'date_to' and 'date_to_bs' are required.")

            # Create new fiscal year record
            new_fiscal_year = request.env['account.fiscal.year'].sudo().create({
                'name': name,
                'name_np': name_np,
                'date_from': date_from,
                'date_to': date_to,
                'date_from_bs': date_from_bs,
                'date_to_bs': date_to_bs,
                'company_id': auth_status['company_id']
            })

            _logger.info(f"Fiscal year {name} created successfully")
            return request.make_response(
                json.dumps({'status': 'success', 'message': 'Fiscal year created successfully', 'fiscal_year_id': new_fiscal_year.id}),
                headers={'Content-Type': 'application/json'},
                status=201
            )

        except ValidationError as ve:
            _logger.warning(f"Validation error: {ve}")
            return request.make_response(
                json.dumps({'status': 'fail', 'message': str(ve)}),
                headers={'Content-Type': 'application/json'},
                status=400
            )

        except Exception as e:
            _logger.error(f"Error creating fiscal year: {e}")
            return request.make_response(
                json.dumps({'status': 'fail', 'message': f'Error creating fiscal year: {str(e)}'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )
