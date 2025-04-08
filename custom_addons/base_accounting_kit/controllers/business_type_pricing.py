from odoo import http
from odoo.http import request
import json
import logging
from odoo.exceptions import ValidationError
from . import jwt_token_auth

_logger = logging.getLogger(__name__)

class BusinessTypePricingController(http.Controller):

    # GET API to retrieve Business Type Pricing details
    @http.route('/api/business_type_pricing', type='http',cors='*', auth='public', methods=['GET'], csrf=False)
    def get_business_type_pricing(self, **kwargs):
        try:
            # Filter business type pricing based on optional parameters
            domain = []
            if 'id' in kwargs:
                domain.append(('business_type.id', '=', kwargs.get('id')))
            # if 'business_type' in kwargs:
            #     domain.append(('business_type.name', 'ilike', kwargs.get('business_type')))
            pricing_data = []
            if kwargs.get('id') is '0':
                data = {
                    'id': 999999,
                    'name': 'test',
                    'business_type': 'test',
                    'pricing':0.0,
                }
                pricing_data.append(data)
                return request.make_response(
                json.dumps({'status': 'success', 'data': pricing_data}),
                headers={'Content-Type': 'application/json'},
                status=200
                )
            business_type_pricing = request.env['business.type.pricing'].sudo().search(domain)
            if not business_type_pricing:
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'No business type pricing found'}),
                    headers={'Content-Type': 'application/json'},
                    status=404
                )


            for pricing in business_type_pricing:
                data = {
                    'id': pricing.id,
                    'name': pricing.name,
                    'business_type': pricing.business_type.name if pricing.business_type else None,
                    'pricing': pricing.pricing,
                }
                pricing_data.append(data)

            # Return the response
            return request.make_response(
                json.dumps({'status': 'success', 'data': pricing_data}),
                headers={'Content-Type': 'application/json'},
                status=200
            )

        except Exception as e:
            _logger.error(f"Error fetching business type pricing: {e}")
            return request.make_response(
                json.dumps({'status': 'fail', 'message': f'Error fetching business type pricing: {str(e)}'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )

   