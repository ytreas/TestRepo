from odoo.http import Response, request
from odoo import http,api, fields
import datetime
from . import jwt_token_auth
from datetime import date,timedelta
import logging
import json
import jwt
from . import jwt_token_auth

_logger = logging.getLogger(__name__)

class InventoryController(http.Controller):
    @http.route("/trading/api/get_inventory", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_product(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            company_id = kw.get('company_id')
            if not company_id:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message":"Company required"
                        }}),
                    content_type='application/json'
                )
            vendor = kw.get('vendor_id')
            category = kw.get('category_id')
            date_filter = kw.get('date_filter')
            company = request.env['res.company'].search([('id', '=', int(company_id))], limit=1)
            if not company:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message":"Company not found"
                        }}),
                    content_type='application/json'
                )
            initial_domain = [('company_id', '=', company.id)]
            stock_quants = request.env['stock.quant'].sudo().search(initial_domain)

            print("initial_domain",len(stock_quants))
            product_ids = stock_quants.mapped('product_id').ids

            # Using the extracted product IDs to search for products in the product.product model
            if product_ids:
                product_domain = [('id', 'in', product_ids)]
                initial_results = request.env["product.product"].sudo().search(product_domain)
            else:
                initial_results = request.env["product.product"].sudo().browse([])
          
            # if company:
            filtered_results = initial_results 
            if vendor:
            
                filtered_results = filtered_results.filtered(lambda r: r.seller_ids.partner_id.id == int(vendor))
            if category:
                filtered_results = filtered_results.filtered(lambda r: r.category_id == int(category))
            if date_filter:
                today = datetime.datetime.today().date()
                if date_filter == 'daily':
                    start_date = datetime.datetime.combine(today, datetime.time.min)
                    end_date = datetime.datetime.combine(today, datetime.time.max)
                    filtered_results = filtered_results.filtered(lambda r: start_date <= r.create_date <= end_date)
                elif date_filter == 'weekly':
                    start_date = today - timedelta(days=today.weekday())
                    end_date = start_date + timedelta(days=6)
                    filtered_results = filtered_results.filtered(lambda r: start_date <= r.create_date.date() <= end_date)
                elif date_filter == 'monthly':
                    start_date = today.replace(day=1)
                    end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(seconds=1)
                    filtered_results = filtered_results.filtered(lambda r: start_date <= r.create_date.date() <= end_date)
                elif date_filter == 'yearly':
                    start_date = today.replace(month=1, day=1)
                    end_date = today.replace(month=12, day=31)
                    filtered_results = filtered_results.filtered(lambda r: start_date <= r.create_date.date() <= end_date)
                else:
                    return http.Response(
                        status=404, 
                        response=json.dumps({"status": "fail", "message": f"Invalid '{date_filter}' date filter"}),
                        content_type="application/json"
                    )
                # domain.append(('create_date', '>=', start_date.strftime('%Y-%m-%d %H:%M:%S')))
                # start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
                # filtered_results = filtered_results.filtered(lambda r: r.create_date >= start_date)



            # if not company_id:
            #     return {"status": "error", "message": "company_id is required"}



            # records = request.env["product.product"].sudo().search([('company_id', '=', int(company_id))])
            # records = request.env["product.product"].sudo().search(domain)
            # _logger.info(f"Company: {len(records)}")
  
            data = []
            for record in filtered_results:
                data.append(
                    {
                        "id": record.product_tmpl_id.id,  # Use product.template ID instead of product.product ID
                        "name": record.display_name,
                        "name_np": record.product_tmpl_id.name_np if record.product_tmpl_id.name_np else None,
                        'on_hand_quantity': record.qty_available,
                        'unit_cost': record.free_qty,  # Ensure correct field is used for unit cost
                        'create_date': record.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'incoming': record.incoming_qty,
                        'outgoing': record.outgoing_qty,
                        'company': record.company_id.name if record.company_id else None,
                    }
                )

            return http.Response(
                status=200,  
                response=json.dumps({"status": "success", "data":data}),
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            
            return http.Response(
                status=401,
                response=json.dumps({
                    "status":"fail",
                    "data":{
                        "message": str(e)
                    }}),
                content_type='application/json'
            )

    @http.route("/trading/api/update_product", type="http",auth='public',cors="*", methods=["POST"], csrf=False)
    def update_inventory_product(self, **kw):
        try:
            # Authentication check
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
                
            # Parse request data
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            product_id = json_data.get('product_id')
            counted_quantity = json_data.get('counted_quantity')
            company_id = json_data.get('company_id')
            location_id = json_data.get('location_id', False)

            _logger.info(f"Setting counted quantity: {counted_quantity} for product: {product_id} in company: {company_id}")

            # Validate required inputs
            if not product_id or counted_quantity is None or not company_id:
                return http.Response(
                    status=400,  
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Missing required parameters (product_id, counted_quantity, company_id)"
                        }
                    }),
                    content_type='application/json'
                )

            # Get the product
            product_template = request.env['product.template'].sudo().browse(int(product_id))
                    
            if product_template.exists():
                if product_template.product_variant_ids:
                    if len(product_template.product_variant_ids) == 1:
                        product = product_template.product_variant_id
                    else:
                        product = product_template.product_variant_ids[0]
                else:
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"No product variants found for template with ID {product_id}"
                            }
                        }),
                        content_type="application/json"
                    )
                if not product.exists():
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"Product with ID {product_id} not found"
                            }
                        }),
                        content_type="application/json"
                    )

            # Get the company
            company = request.env['res.company'].sudo().browse(int(company_id))
            if not company.exists():
                return http.Response(
                    status=404,  
                    response=json.dumps({
                        "status": "fail", 
                        "data": {
                            "message": f"Company with ID {company_id} not found"
                        }
                    }),
                    content_type="application/json"
                )

            # Get or set location
            if location_id:
                location = request.env['stock.location'].sudo().browse(int(location_id))
                if not location.exists():
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"Location with ID {location_id} not found"
                            }
                        }),
                        content_type="application/json"
                    )
            else:
                # Use the default internal location for the company
                location = request.env['stock.location'].sudo().search([
                    ('company_id', '=', company.id),
                    ('usage', '=', 'internal'),
                    ('name', '=', 'Stock')
                ], limit=1)
                
                # If not found, try to find one containing "Stock" in the name
                if not location:
                    location = request.env['stock.location'].sudo().search([
                        ('company_id', '=', company.id),
                        ('usage', '=', 'internal'),
                        ('name', 'ilike', 'Stock')
                    ], limit=1)
                
                # If still not found, try to find locations with complete_name like "WH/Stock"
                if not location:
                    location = request.env['stock.location'].sudo().search([
                        ('company_id', '=', company.id),
                        ('usage', '=', 'internal'),
                        ('complete_name', 'ilike', '/Stock')
                    ], limit=1)
                    
                # As a last resort, fallback to any internal location
                if not location:
                    location = request.env['stock.location'].sudo().search([
                        ('company_id', '=', company.id),
                        ('usage', '=', 'internal')
                    ], limit=1)
                
                if not location:
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"No default internal location found for company {company.name}"
                            }
                        }),
                        content_type="application/json"
                    )

            # Check if a stock quant already exists
            stock_quant = request.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('company_id', '=', company.id),
                ('location_id', '=', location.id)
            ], limit=1)
            
            if stock_quant:
                # Add new quantity to existing stock
                # new_quantity = stock_quant.quantity + float(counted_quantity)
                stock_quant.sudo().write({'quantity': counted_quantity})
                message = f"Quantity of '{product.name}' updated to {counted_quantity}."
            else:
                return http.Response(
                    status=404,  
                    response=json.dumps({
                        "status": "fail", 
                        "data":{
                            "message": f"Stock is not available for this product in the company's warehouse use the update it instead"}
                        }),
                    content_type="application/json"
                )

            return http.Response(
                status=200,  
                response=json.dumps({
                    "status": "success",
                    "data": {
                        "message": message,
                        "product_id": product.id,
                        "product_name": product.name,
                        "quantity": counted_quantity,
                        "location_id": location.id,
                        "location_name": location.name
                    }
                }),
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error updating quantity: {str(e)}")
            return http.Response(
                status=500,  
                response=json.dumps({
                    "status": "fail", 
                    "data": {
                        "message": f"Failed to update quantity: {str(e)}"
                    }
                }),
                content_type="application/json"
            )

    @http.route("/trading/api/get_inventory_history", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_inventory_history(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            product_id = kw.get('product_id')
            company_id = kw.get('company_id')

            if not product_id or not company_id:
                return http.Response(
                    status=404,  
                    response=json.dumps({
                        "status": "fail", 
                        "data":{
                            "message": f"product_id and company_id are required"}
                        }),
                    content_type="application/json"
                    )

            # Get the product template
            product_template = request.env['product.template'].sudo().browse(int(product_id))

            # Use the first variant if available; otherwise, fallback to template ID
            if product_template.exists():
                product_product_id = product_template.product_variant_ids[:1].id if product_template.product_variant_ids else product_template.id
            else:
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": f"Product template with ID {product_id} not found"}
                    }),
                    content_type="application/json"
                )

            # Fetch stock move history using the determined product ID
            history = request.env['stock.move.line'].sudo().search([
                ('product_id', '=', product_product_id),
                ('company_id', '=', int(company_id))
            ])

            if not history:
                return http.Response(
                    status=404,  
                    response=json.dumps({
                        "status": "fail", 
                        "data":{
                            "message": f"History not found for this product and company"}
                        }),
                    content_type="application/json"
                    )
                
            # action = stock_quant.action_inventory_history()
            # stock_move_lines = request.env['stock.move.line'].sudo().search(action['domain'])
            _logger.error(f"Historyyyy: {len(history)}")
            data = []
            for line in history:
                data.append({
                    'product_id': line.product_id.product_tmpl_id.id,  # Use product.template ID
                    'product_name': line.product_id.product_tmpl_id.name,  # Use product.template Name
                    'quantity': line.quantity,
                    'date': line.date.strftime('%Y-%m-%d') if line.date else None,
                    'location_id': line.location_id.id,
                    'from': line.location_id.name,
                    'location_dest_id': line.location_dest_id.id,
                    'to': line.location_dest_id.name,
                    'company_id': line.company_id.id,
                    'done_by': line.create_uid.name,
                    'reference': line.reference,
                })


            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            # _logger.error(f"Error: {str(e)}")
            return http.Response(
                status=404,  
                response=json.dumps({
                    "status": "fail", 
                    "data":{
                        "message": str(e)}
                    }),
                content_type="application/json"
            )
        
            

    # @http.route("/trading/api/delete", type="http", methods=["DELETE"], csrf=False)
    # def delete_from_inventory(self, **kw):
    #     try:
    #         product_id = kw.get('product_id')
    #         company_id = kw.get('company_id')

    #         if not product_id or not company_id:
    #             return request.make_response(
    #                 json.dumps({"status": "error", "message": "product_id and company_id are required"}),
    #                 headers=[("Content-Type", "application/json")]
    #             )

    #         stock_quant = request.env['stock.quant'].sudo().search(
    #             [('product_id', '=', int(product_id)), ('company_id', '=', int(company_id))], limit=1)
            
    #         if not stock_quant:
    #             return request.make_response(
    #                 json.dumps({"status": "error", "message": "Stock quant not found for this product and company"}),
    #                 headers=[("Content-Type", "application/json")]
    #             )

    #         if stock_quant.quantity != 0:
    #             return request.make_response(
    #                 json.dumps({"status": "error", "message": "Cannot delete stock quant with non-zero quantity"}),
    #                 headers=[("Content-Type", "application/json")]
    #             )

    #         stock_move_lines = request.env['stock.move.line'].sudo().search(
    #             [('product_id', '=', int(product_id)), ('company_id', '=', int(company_id))])
            
    #         if stock_move_lines:
    #             stock_move_lines.sudo().unlink()
                
    #         stock_quant.sudo().unlink()

    #         return request.make_response(
    #             json.dumps({"status": "success", "message": "Product and related records deleted successfully"}),
    #             headers=[("Content-Type", "application/json")]
    #         )
    #     except Exception as e:
    #         _logger.error(f"Error: {str(e)}")
    #         return request.make_response(
    #             json.dumps({"status": "error", "message": str(e)}),
    #             headers=[("Content-Type", "application/json")]
    #         )

  
    @http.route("/trading/api/set_initial_quantity", type="http", auth='public', cors="*", methods=["POST"], csrf=False)
    def set_initial_product_quantity(self, **kw):
        try:
            # Authentication check
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
                
            # Parse request data
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            product_id = json_data.get('product_id')
            initial_quantity = json_data.get('initial_quantity')
            company_id = json_data.get('company_id')
            location_id = json_data.get('location_id', False)

            _logger.info(f"Setting initial quantity: {initial_quantity} for product: {product_id} in company: {company_id}")

            # Validate required inputs
            if not product_id or initial_quantity is None or not company_id:
                return http.Response(
                    status=400,  
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Missing required parameters (product_id, initial_quantity, company_id)"
                        }
                    }),
                    content_type='application/json'
                )

            # Get the product
            product_template = request.env['product.template'].sudo().browse(int(product_id))
                    
            if product_template.exists():
                if product_template.product_variant_ids:
                    if len(product_template.product_variant_ids) == 1:
                        product = product_template.product_variant_id
                    else:
                        product = product_template.product_variant_ids[0]
                else:
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"No product variants found for template with ID {product_id}"
                            }
                        }),
                        content_type="application/json"
                    )
                if not product.exists():
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"Product with ID {product_id} not found"
                            }
                        }),
                        content_type="application/json"
                    )

            # Get the company
            company = request.env['res.company'].sudo().browse(int(company_id))
            if not company.exists():
                return http.Response(
                    status=404,  
                    response=json.dumps({
                        "status": "fail", 
                        "data": {
                            "message": f"Company with ID {company_id} not found"
                        }
                    }),
                    content_type="application/json"
                )

            # Get or set location
            if location_id:
                location = request.env['stock.location'].sudo().browse(int(location_id))
                if not location.exists():
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"Location with ID {location_id} not found"
                            }
                        }),
                        content_type="application/json"
                    )
            else:
                # Use the default internal location for the company
                location = request.env['stock.location'].sudo().search([
                    ('company_id', '=', company.id),
                    ('usage', '=', 'internal'),
                    ('name', '=', 'Stock')
                ], limit=1)
                
                # If not found, try to find one containing "Stock" in the name
                if not location:
                    location = request.env['stock.location'].sudo().search([
                        ('company_id', '=', company.id),
                        ('usage', '=', 'internal'),
                        ('name', 'ilike', 'Stock')
                    ], limit=1)
                
                # If still not found, try to find locations with complete_name like "WH/Stock"
                if not location:
                    location = request.env['stock.location'].sudo().search([
                        ('company_id', '=', company.id),
                        ('usage', '=', 'internal'),
                        ('complete_name', 'ilike', '/Stock')
                    ], limit=1)
                    
                # As a last resort, fallback to any internal location
                if not location:
                    location = request.env['stock.location'].sudo().search([
                        ('company_id', '=', company.id),
                        ('usage', '=', 'internal')
                    ], limit=1)
                
                if not location:
                    return http.Response(
                        status=404,  
                        response=json.dumps({
                            "status": "fail", 
                            "data": {
                                "message": f"No default internal location found for company {company.name}"
                            }
                        }),
                        content_type="application/json"
                    )

            # Check if a stock quant already exists
            stock_quant = request.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('company_id', '=', company.id),
                ('location_id', '=', location.id)
            ], limit=1)
            
            if stock_quant:
                # Update existing quant
                return http.Response(
                    status=404,  
                    response=json.dumps({
                        "status": "fail", 
                        "data":{
                            "message": f"Stock already exists for this product in the company's warehouse use the update it instead"}
                        }),
                    content_type="application/json"
                )
            else:
                # Create new quant
                stock_quant = request.env['stock.quant'].sudo().create({
                    'product_id': product.id,
                    'company_id': company.id,
                    'location_id': location.id,
                    'inventory_quantity': float(initial_quantity)
                })
                stock_quant.sudo().action_apply_inventory()
                message = f"Initial quantity of '{product.name}' set to {initial_quantity}"

            return http.Response(
                status=200,  
                response=json.dumps({
                    "status": "success",
                    "data": {
                        "message": message,
                        "product_id": product.id,
                        "product_name": product.name,
                        "quantity": initial_quantity,
                        "location_id": location.id,
                        "location_name": location.name
                    }
                }),
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error setting initial quantity: {str(e)}")
            return http.Response(
                status=500,  
                response=json.dumps({
                    "status": "fail", 
                    "data": {
                        "message": f"Failed to set initial quantity: {str(e)}"
                    }
                }),
                content_type="application/json"
            )