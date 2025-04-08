from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
import base64
from . import jwt_token_auth
import datetime
import logging
import json
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class Customer(http.Controller):
    
    @http.route('/trading/api/get_customer_list', type='http', auth='public',cors="*",methods=['GET'], csrf=False)
    def get_customer_list(self,**kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            domain = []
            domain.append(('customer_rank', '>', 0))
                
            customers = request.env['res.partner'].sudo().search(domain)

            customer_details = []
            for customer in customers:
                customer_sale_domain=[]
                customer_total_sale = 0
                customer_sale_domain.append(('partner_id.id', '=', customer.id))
                customer_sale_orders = request.env['sale.order'].sudo().search(customer_sale_domain)
                for customer_sale_order in customer_sale_orders:
                    customer_total_sale = sum([line.price_subtotal for line in customer_sale_order.order_line])+customer_total_sale
                customer_details.append({
                    'id': customer.id,
                    'name': customer.complete_name,
                    'name_np': customer.name_np if customer.name_np else None,
                    'email': customer.email if customer.email else None,
                    'pan_no': customer.pan_no if customer.pan_no else None,
                    'mobile': customer.mobile if customer.mobile else None,
                    'total_sale': customer_total_sale,
        
                })
            return request.make_response(
                json.dumps({"status": "success", "data": customer_details}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return http.Response(
                status=500,
                response=json.dumps({'status': 'Internal server error'}),
                content_type='application/json'
            )

    @http.route("/trading/api/create_customer", type="http",auth='public',cors="*", methods=["POST"], csrf=False)
    def create_customer(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            token = request.httprequest.headers.get("Authorization")
            if token and token.startswith("Bearer "):
                bearer_token = token[len("Bearer "):]
        
            status = jwt_token_auth.JWTAuth.check_jwt(self, bearer_token)
        

            if status.get("success") != 'Access granted':
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':  {
                                'message': 'Unauthorized access',
                            }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=401
                )

            company_id = kw.get('company_id')
            image_1920 = kw.get('image_1920')
            image_1920_binary =  base64.b64encode(image_1920.read())

            company = request.env['res.company'].search([('id', '=', int(company_id))], limit=1)
            if not company:
                return http.Response(
                    status=404,
                    response=json.dumps({"status": "fail", "message": "Company not found"}),
                    content_type="application/json"
                )
            company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
            if not company:
                    return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':  {
                                'message': 'Company not found',
                            }
                    }),
                    headers=[("Content-Type", "application/json")],
                    status=404
                )
            max_rank = request.env['res.partner'].sudo().search([('customer_rank', '>', 0)], order='customer_rank desc', limit=1).customer_rank or 0
            customer_rank = max_rank + 1

            customer_details= {
                'company_id' : company_id,
                'name' : kw.get('customer_name'),
                'name_np' : kw.get('customer_name_np'),
                'city' : kw.get('address'),
                'zip' : kw.get('zip'),
                'phone' : kw.get('phone'),
                'vat' : kw.get('vat'),
                'email' : kw.get('email'),
                'mobile' : kw.get('mobile'),
                'pan_no': kw.get('pan_no'),
                # 'province': kw.get('province'),
                # 'district' : kw.get('district'),
                # 'palika': kw.get('palika'),
                # 'ward_no': kw.get('ward_no'),
                'customer_rank': customer_rank,
                'image_1920': image_1920_binary
                # 'tole': kw.get('ward_no')
            }
            customer = request.env['res.partner'].sudo().create(customer_details)
            _logger.error(f"datata: {customer_details}")
            return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data':  {
                                'message': 'Successfully created customer',
                                'customer_id': customer.id
                            }
                    }),
                    headers=[("Content-Type", "application/json")],
                    status=200
                )
            
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return request.make_response(
                json.dumps({"status": "fail", "message": str(e)}),
                headers=[("Content-Type", "application/json")]
            )
    
    @http.route("/trading/api/edit_customer", type="http",auth='public',cors="*", methods=["PUT"], csrf=False)
    def edit_customer(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

          
            customer_id = kw.get('customer_id')
            if not customer_id:
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'Customer ID is required'}),
                    headers=[("Content-Type", "application/json")],
                    status=400
                )

            customer = request.env['res.partner'].sudo().search([('id', '=', int(customer_id))], limit=1)
            if not customer:
                return request.make_response(
                    json.dumps({"status": "fail", "message": "Customer not found"}),
                    headers=[("Content-Type", "application/json")],
                    status=404
                )


            # Prepare the fields to update
            update_fields = {}

            # Update fields only if they are provided in the request

            if 'customer_name' in kw:
                if kw.get('customer_name') is not "":
                    update_fields['name'] = kw.get('customer_name')
            if 'name_np' in kw:
                if kw.get('name_np') is not "":
                    update_fields['name_np'] = kw.get('name_np')
            if 'address' in kw:
                if kw.get('address') is not "":
                    update_fields['city'] = kw.get('address')
            if 'zip' in kw:
                if kw.get('zip') is not "":
                    update_fields['zip'] = kw.get('zip')
            if 'phone' in kw:
                if kw.get('phone') is not "":
                    update_fields['phone'] = kw.get('phone')
            if 'vat' in kw:
                if kw.get('vat') is not "":
                    update_fields['vat'] = kw.get('vat')
            if 'email' in kw:
                if kw.get('email') is not "":
                    update_fields['email'] = kw.get('email')
            if 'mobile' in kw:
                if kw.get('mobile') is not "":
                    update_fields['mobile'] = kw.get('mobile')
            # if 'province' in kw:
            #     if kw.get('province') is not "":
            #         update_fields['province'] = kw.get('province')
            # if 'district' in kw:
            #     if kw.get('district') is not "":
            #         update_fields['district'] = kw.get('district')
            # if 'palika' in kw:
            #     if kw.get('palika') is not "":
            #         update_fields['palika'] = kw.get('palika')
            # if 'ward_no' in kw:
            #     if kw.get('ward_no') is not "":
            #         update_fields['ward_no'] = kw.get('ward_no')
            if kw.get('pan_no') is not "":
                    update_fields['pan_no'] = kw.get('pan_no')
            if 'image_1920' in kw:
                if kw.get('image_1920') is not "":
                    image_1920 = kw.get('image_1920')
                    image_1920_binary =  base64.b64encode(image_1920.read())
                    update_fields['image_1920'] = image_1920_binary

            # Log the update fields for debugging
            # _logger.info(f"Updating customer with ID {customer_id} with fields: {update_fields}")

            if not update_fields:
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'No valid fields to update'}),
                    headers=[("Content-Type", "application/json")],
                    status=400
                )

            # Perform the update
            customer.sudo().write(update_fields)
            _logger.info(f"Customer with ID {customer_id} updated successfully.")

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Customer details updated successfully'
                    }
                }),
                headers=[("Content-Type", "application/json")],
                status=200
            )

        except Exception as e:
            _logger.error(f"Error while updating customer: {str(e)}")
            return request.make_response(
                json.dumps({"status": "fail", "message": str(e)}),
                headers=[("Content-Type", "application/json")],
                status=500
            )
    
    @http.route("/trading/api/delete_customer", type="http",auth='public',cors="*", methods=["DELETE"], csrf=False)
    def delete_customer(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            customer_id = json_data.get('customer_id')
            customer = request.env['res.partner'].sudo().search([('id', '=', customer_id)], limit=1)
            if not customer:
                return http.Response(
                    status=404,
                    response=json.dumps({"status": "fail", "message": "Customer not found"}),
                    content_type="application/json"
                )
            
            customer.sudo().unlink()
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Customer deleted successfully'
                    }
                }),
                headers=[("Content-Type", "application/json")],
                status=200
            )

        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return request.make_response(
                json.dumps({"status": "fail", "message": str(e)}),
                headers=[("Content-Type", "application/json")],
                status=500
            )

