from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
import datetime
import logging
import json
from odoo.exceptions import ValidationError,UserError
from . import jwt_token_auth
import jwt
import base64

_logger = logging.getLogger(__name__)

class CustomPrices(http.Controller):
    @http.route('/trading/api/product_custom_prices', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_product_custom_prices(self, **kwargs):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Fetch all product custom prices
            custom_prices = request.env['product.custom.price'].sudo().search([])
            custom_price_details = [{
                'id': price.id,
                'product_id': price.product_id.id,
                'product_name': price.product_name,
                'company_id': price.company_id.id,
                'price_sell': price.price_sell,
                'price_cost': price.price_cost,
                'min_qty': price.min_qty,
                'max_qty': price.max_qty,
                'saleable_qty': price.saleable_qty,
                'qty_available': price.qty_available,
                'virtual_available': price.virtual_available,
                'sales_price': price.sales_price,
                'cost_price': price.cost_price,
                'sale_ok': price.sale_ok,
                'purchase_ok': price.purchase_ok,
                'discount': price.discount,
                'product_ribbon': price.product_ribbon,
                'publish': price.publish,
                'free_delivery': price.free_delivery,
                'product_featured_image': f"http://lekhaplus.com/web/image?model=product.custom.price&id={price.id}&field=product_featured_image" if price.product_featured_image else None
            } for price in custom_prices]

            return request.make_response(
                json.dumps({"status": "success", "data": custom_price_details}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                content_type='application/json'
            )

    @http.route('/trading/api/product_custom_prices/<int:company_id>', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_product_custom_prices_by_company(self, company_id, **kwargs):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Fetch product custom prices for the given company_id
            if company_id is not 1:
                custom_prices = request.env['product.custom.price'].sudo().search([('company_id', '=', company_id)])
            else:
                custom_prices = request.env['product.custom.price'].sudo().search([])
            custom_price_details = [{
                'id': price.id,
                'product_id': price.product_id.id,
                'product_name': price.product_name,
                'company_id': price.company_id.id,
                'price_sell': price.price_sell,
                'price_cost': price.price_cost,
                'min_qty': price.min_qty,
                'max_qty': price.max_qty,
                'saleable_qty': price.saleable_qty,
                'qty_available': price.qty_available,
                'virtual_available': price.virtual_available,
                'sales_price': price.sales_price,
                'cost_price': price.cost_price,
                'sale_ok': price.sale_ok,
                'purchase_ok': price.purchase_ok,
                'discount': price.discount,
                'product_ribbon': price.product_ribbon,
                'publish': price.publish,
                'free_delivery': price.free_delivery,
                'product_featured_image': f"http://lekhaplus.com/web/image?model=product.custom.price&id={price.id}&field=product_featured_image" if price.product_featured_image else None
            } for price in custom_prices]

            return request.make_response(
                json.dumps({"status": "success", "data": custom_price_details}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                content_type='application/json'
            )
    
    @http.route('/trading/api/product_custom_prices', type='http', auth='public', cors="*", methods=['POST'], csrf=False)
    def create_product_custom_price(self, **kwargs):
        try:
            # Step 1: Authenticate the request using JWT
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Step 2: Retrieve form data
            product_id = request.params.get('product_id')
            company_id = request.params.get('company_id')
            price_sell = request.params.get('price_sell')
            price_cost = request.params.get('price_cost')
            min_qty = request.params.get('min_qty')
            max_qty = request.params.get('max_qty')
            saleable_qty = request.params.get('saleable_qty')
            discount = request.params.get('discount')
            publish = request.params.get('publish', 'false').lower() == 'true'
            free_delivery = request.params.get('free_delivery', 'false').lower() == 'true'
            product_featured_image = request.httprequest.files.get('product_featured_image')

            # Step 3: Validate User Company
            if str(company_id) != str(auth_status['company_id']):
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'You can only create custom prices for your own company'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Step 4: Validate Product ID
            if not product_id:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Product ID is required'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            product = request.env['product.template'].sudo().search([('id', '=', int(product_id))], limit=1)
            if not product:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Product not found: {product_id}'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Step 5: Validate min_qty and max_qty
            if min_qty and max_qty and float(min_qty) > float(max_qty):
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Maximum Qty should be greater than Minimum Qty'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Step 6: Validate saleable_qty
            if saleable_qty and float(saleable_qty) > product.qty_available:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Saleable Qty should be less than Qty on Hand'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Step 7: Prevent Duplicate Records
            existing_custom_price = request.env['product.custom.price'].sudo().search([
                ('product_id.id', '=', product.id),
                ('company_id.id', '=', company_id)
            ], limit=1)

            if existing_custom_price:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Only one price record per product can exist for each company.'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Step 8: Handle File Upload
            image_data = False
            if product_featured_image:
                image_data = base64.b64encode(product_featured_image.read())

            # Step 9: Create Product Custom Price
            custom_price_vals = {
                'product_id': product.id,
                'company_id': company_id,
                'price_sell': price_sell,
                'price_cost': price_cost,
                'min_qty': min_qty,
                'max_qty': max_qty,
                'saleable_qty': saleable_qty,
                'discount': discount,
                'publish': publish,
                'free_delivery': free_delivery,
                'product_featured_image': image_data,
            }

            custom_price = request.env['product.custom.price'].sudo().create(custom_price_vals)

            # Step 10: Return Success Response
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Product custom price created successfully',
                        'custom_price_id': custom_price.id
                    }
                }),
                headers=[("Content-Type", "application/json")],
                status=200
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': 'Internal server error',
                        'details': str(e)
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/trading/api/product_custom_prices/edit', type='http', auth='public', cors="*", methods=['POST'], csrf=False)
    def edit_product_custom_price(self, **kwargs):
        try:
            # Step 1: Authenticate the request using JWT
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Step 2: Retrieve form data
            custom_price_id = request.params.get('custom_price_id')  # Required
            price_sell = request.params.get('price_sell')
            price_cost = request.params.get('price_cost')
            min_qty = request.params.get('min_qty')
            max_qty = request.params.get('max_qty')
            saleable_qty = request.params.get('saleable_qty')
            discount = request.params.get('discount')
            publish = request.params.get('publish', 'false').lower() == 'true'
            free_delivery = request.params.get('free_delivery', 'false').lower() == 'true'
            product_featured_image = request.httprequest.files.get('product_featured_image')

            # Step 3: Validate Custom Price ID
            if not custom_price_id:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Custom Price ID is required'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            custom_price = request.env['product.custom.price'].sudo().search([('id', '=', int(custom_price_id))], limit=1)
            if not custom_price:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Custom Price not found: {custom_price_id}'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Step 4: Prepare Values for Update
            update_vals = {}

            if price_sell is not None:
                update_vals['price_sell'] = price_sell
            if price_cost is not None:
                update_vals['price_cost'] = price_cost
            if min_qty is not None:
                update_vals['min_qty'] = min_qty
            if max_qty is not None:
                update_vals['max_qty'] = max_qty
            if saleable_qty is not None:
                update_vals['saleable_qty'] = saleable_qty
            if discount is not None:
                update_vals['discount'] = discount
            update_vals['publish'] = publish
            update_vals['free_delivery'] = free_delivery

            # Step 5: Handle File Upload
            if product_featured_image:
                update_vals['product_featured_image'] = base64.b64encode(product_featured_image.read())

            # Step 6: Update Record
            if update_vals:
                custom_price.sudo().write(update_vals)
                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': {
                            'message': 'Product custom price updated successfully',
                            'custom_price_id': custom_price.id
                        }
                    }),
                    headers=[("Content-Type", "application/json")],
                    status=200
                )
            else:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'No valid fields provided for update'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': 'Internal server error',
                        'details': str(e)
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )