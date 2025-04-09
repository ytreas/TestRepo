from odoo.http import Response, request
from odoo import http,api,SUPERUSER_ID
import datetime
from . import jwt_token_auth
from datetime import date
import base64
import logging
import json

_logger = logging.getLogger(__name__)

class ProductController(http.Controller):
    @http.route("/trading/api/get_products", type="http", cors="*", auth="public", methods=["GET"], csrf=False)
    def get_product(self, **kw):
        try:
            company_id = kw.get('company_id')
            product_id = kw.get('product_id')

            domain = []
            purchase_domain=[]
            if company_id:
                company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
                if not company:
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail",
                            "data": {"message": "Company not found"}
                        }),
                        headers=[('Content-Type', 'application/json')],
                    )
                if company.id is 1:
                    purchase_domain=[]
                    records = request.env["product.template"].sudo().search(purchase_domain)
                    data = []
                    for record in records:
                        product_categories = record.company_category
                        category_data = [{"id": cat.id, "name": cat.name} for cat in product_categories]

                        data.append({
                            "id": record.id,
                            "name": record.name if record.name else None,
                            "name_np": record.name_np if record.name_np else None,
                            "cost_price": record.standard_price,
                            "min_qty": record.min_qty,
                            "max_qty": record.max_qty,
                            "sales_price": record.list_price,
                            "categories": category_data,
                            "saleable_qty": record.qty_available
                        })
                    return request.make_response(
                            json.dumps({"status": "success", "data": data}),
                            headers=[('Content-Type', 'application/json')]
                    )

            if product_id:
                domain.append(('id', '=', int(product_id)))
            else:
                quant_records = request.env['stock.quant'].sudo().search([
                    ('company_id', '=', company.id),
                    ('location_id.usage', '=', 'internal')
                ])
                product_template_ids = []
                custom_price_records = request.env['product.custom.price'].sudo().search([
                    ('company_id', '=', company.id),
                    ('saleable_qty', '>', 0)
                ])
                print("Custom price records:", custom_price_records)
                
                for price_record in custom_price_records:
                    product_template_id = price_record.product_id.id
                    if product_template_id not in product_template_ids:
                        product_template_ids.append(price_record.product_id.id)

                warehouse_template_ids = []

                for quant in quant_records:
                    product_template_id = quant.product_id.product_tmpl_id.id
                    if product_template_id in product_template_ids:
                        if product_template_id not in warehouse_template_ids:
                            warehouse_template_ids.append(product_template_id)
                product_ids = []
                for business_based_product in company.company_category_product:
                    business_based_product_id = business_based_product.product_id.id                
                    product_ids.append(business_based_product_id)

                common_template_ids = list(set(warehouse_template_ids) & set(product_ids) &set(product_template_ids))

                if common_template_ids:
                    purchase_domain = [('id', 'in', common_template_ids)]
                else:
                    purchase_domain = [('id', 'in', [])]
            if not purchase_domain:
                data = []
                records = request.env["product.template"].sudo().search(domain)
                for record in records:
                    product_categories = record.company_category  # Handle multiple categories
                    category_data = [{"id": cat.id, "name": cat.name} for cat in product_categories]       
                    data.append({
                        "id": record.id,
                        "name": record.name if record.name else None,
                        "name_np": record.name_np if record.name_np else None,
                        "cost_price": record.standard_price,
                        "min_qty": record.min_qty,
                        "max_qty": record.max_qty,
                        "sales_price": record.list_price,
                        "categories": category_data,
                        "saleable_qty": record.qty_available
                    })
            else:
                records = request.env["product.template"].sudo().search(purchase_domain)
                data = []
                for record in records:
                    product_categories = record.company_category  # Handle multiple categories
                    category_data = [{"id": cat.id, "name": cat.name} for cat in product_categories]       
                    custom_price = request.env["product.custom.price"].sudo().search([
                        ("product_id", "=", record.id),
                        ("company_id", "=", company.id),
                    ], limit=1)
                    if custom_price:
                        cost_price = custom_price.cost_price
                        min_qty = custom_price.min_qty
                        max_qty = custom_price.max_qty
                        saleable_qty = custom_price.saleable_qty
                        sales_price = custom_price.sales_price
                    else:
                        cost_price = record.standard_price
                        min_qty = record.min_qty
                        max_qty = record.max_qty
                        sales_price = record.list_price
                        saleable_qty = record.qty_available

                    data.append({
                        "id": record.id,
                        "name": record.name if record.name else None,
                        "name_np": record.name_np if record.name_np else None,
                        "cost_price": cost_price,
                        "min_qty": min_qty,
                        "max_qty": max_qty,
                        "sales_price": sales_price,
                        "categories": category_data,
                        "saleable_qty": saleable_qty
                    })
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            return http.Response(
                status=401,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                headers=[('Content-Type', 'application/json')],
            )
    @http.route("/trading/api/get_products_2", type="http", cors="*", auth="public", methods=["GET"], csrf=False)
    def get_product_2(self, **kw):
        try:
            company_id = kw.get('company_id')
            product_id = kw.get('product_id')
            is_inventory = kw.get("is_inventory")

            domain = []
            purchase_domain=[]
            if company_id:
                company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
                if not company:
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail",
                            "data": {"message": "Company not found"}
                        }),
                        headers=[('Content-Type', 'application/json')],
                    )
                if company.id is 1:
                    purchase_domain=[]
                    if is_inventory and is_inventory == "True":
                        purchase_domain.append(('detailed_type', '=', 'product'))
                    records = request.env["product.template"].sudo().search(purchase_domain)
                    data = []
                    for record in records:
                        product_categories = record.company_category
                        category_data = [{"id": cat.id, "name": cat.name} for cat in product_categories]

                        data.append({
                            "id": record.id,
                            "name": record.name if record.name else None,
                            "name_np": record.name_np if record.name_np else None,
                            "cost_price": record.standard_price,
                            "min_qty": record.min_qty,
                            "max_qty": record.max_qty,
                            "sales_price": record.list_price,
                            "categories": category_data,
                            "saleable_qty": record.qty_available
                        })
                    return request.make_response(
                            json.dumps({"status": "success", "data": data}),
                            headers=[('Content-Type', 'application/json')]
                    )

            if product_id:
                domain.append(('id', '=', int(product_id)))
            else:
                product_ids = []
                for business_based_product in company.company_category_product:
                    business_based_product_id = business_based_product.product_id.id                
                    product_ids.append(business_based_product_id)

                common_template_ids = list(set(product_ids))

                if common_template_ids:
                    purchase_domain = [('id', 'in', common_template_ids)]
                else:
                    purchase_domain = [('id', 'in', [])]
            if not purchase_domain:
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail",
                            "data": {"message": "No eligible product for the given company."}
                        }),
                        headers=[('Content-Type', 'application/json')],
                    )
            else:
                if is_inventory and is_inventory == "True":
                    purchase_domain.append(('detailed_type', '=', 'product'))
                records = request.env["product.template"].sudo().search(purchase_domain)
                data = []
                for record in records:
                    product_categories = record.company_category  # Handle multiple categories
                    category_data = [{"id": cat.id, "name": cat.name} for cat in product_categories]       
                    custom_price = request.env["product.custom.price"].sudo().search([
                        ("product_id", "=", record.id),
                        ("company_id", "=", company.id),
                    ], limit=1)
                    if custom_price:
                        cost_price = custom_price.cost_price
                        min_qty = custom_price.min_qty
                        max_qty = custom_price.max_qty
                        saleable_qty = custom_price.saleable_qty
                        sales_price = custom_price.sales_price
                    else:
                        cost_price = record.standard_price
                        min_qty = record.min_qty
                        max_qty = record.max_qty
                        sales_price = record.list_price
                        saleable_qty = record.qty_available

                    data.append({
                        "id": record.id,
                        "name": record.name if record.name else None,
                        "name_np": record.name_np if record.name_np else None,
                        "cost_price": cost_price,
                        "min_qty": min_qty,
                        "max_qty": max_qty,
                        "sales_price": sales_price,
                        "categories": category_data,
                        "saleable_qty": saleable_qty
                    })
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            return http.Response(
                status=401,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                headers=[('Content-Type', 'application/json')],
            )


            

    @http.route("/trading/api/post_products", type="http", cors="*",auth="public",  methods=["POST"], csrf=False)
    def post_product(self,**kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received login data: {hosturl}")
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )
                
            # company_id = kw.get('company_id')
            # if not company_id:
            #     return http.Response(
            #         status=404,
            #         response=json.dumps({
            #             "status": "fail", 
            #             "data":{
            #                 "message": "Company required"
            #             }}),
            #         headers=[
            #             ('Content-Type', 'application/json')
            #         ],
            #     )
            # company = request.env['res.company'].search([('id', '=', int(company_id))], limit=1)
            # if not company:
            #     return http.Response(
            #         status=404,
            #         response=json.dumps({
            #             "status": "fail", 
            #             "data":{
            #                 "message": "Company not found"
            #             }}),
            #         headers=[
            #             ('Content-Type', 'application/json')
            #         ],
            #     )
            image_1920 = kw.get('image_1920')
            if image_1920:
                image_1920_binary =  base64.b64encode(image_1920.read())
            else:
                image_1920_binary = None

            

            # category_id = kw.get('category_id')
            # if not category_id: 
            #     return http.Response(
            #         status=404,
            #         response=json.dumps({
            #             "status": "fail", 
            #             "data":{
            #                 "message": "Company Category required"
            #             }}),
            #         headers=[
            #             ('Content-Type', 'application/json')
            #         ],
            #     )

            locality_name = kw.get('locality_name') 

            taxes_names = kw.get('tax')
            
            sales_price = kw.get('sales_price')
            standard_price = kw.get('cost_price')
            min_qty = kw.get('min_qty')
            max_qty = kw.get('max_qty')
            
            # company_category = request.env['company.category'].search([('id', '=', category_id)], limit=1)
        
            # if not company_category:
            #     return http.Response(
            #         status=404,
            #         response=json.dumps({
            #             "status": "fail", 
            #             "data":{ 
            #                 "message": f"Company category '{category_id}' not found"
            #                 }}),
            #         headers=[
            #             ('Content-Type', 'application/json')
                       
            #         ],
            #     )
            name_np = kw.get('name_np')
            product_details = {
                # 'company_id': company.id,
                'name': kw.get('product_name'),
                'name_np': name_np if name_np else None,
                # 'company_category': [(6, 0, [company_category.id])],  # List of IDs for many2many field
                'list_price': sales_price,
                'standard_price': standard_price,
                'min_qty': min_qty,
                'max_qty': max_qty,
                'image_1920': image_1920_binary if image_1920 else None
            }
            # _logger.info(f"Product Details: {product_details}")
            product = request.env['product.template'].sudo().create(product_details)
            # if product:
            # reference_name = kw.get('reference_order_id')
            # company = request.env['res.company'].search([('id', '=', company_id)], limit=1)
            # _logger.info(f"Company ID+++++++++++: {company.name}")

            # product_product = request.env['product.product'].search([('name', '=', product.name)], limit=1)
            
            return request.make_response(
                http.json.dumps({
                    "status": "success", 
                    "data":{
                        "product_id":product.id
                        }
                    }),
                headers=[
                    ('Content-Type', 'application/json')
                ],
            )
        except Exception as e:
            return http.Response(
                status=401,
                response=json.dumps({
                    "status":"fail",
                    "data":{
                        "message":str(e)
                        }
                    }),
                headers=[
                    ('Content-Type', 'application/json')
                    
                ],
            )
    @http.route("/trading/api/edit_product", type="http", cors="*", auth="public", methods=["PUT"], csrf=False)
    def edit_product(self, **kw):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Fetch company and product by IDs
            company_id = kw.get('company_id')
            product_id = kw.get('product_id')
            company = request.env['res.company'].sudo().search([('id', '=', company_id)], limit=1)
            product = request.env['product.template'].sudo().search([('id', '=', product_id)], limit=1)

            if not company:
               return Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "Company not found"}
                    }),
                    content_type='application/json'
                )
            if not product:
                return Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "Product not found"}
                    }),
                    content_type='application/json'
                )

            update_vals = {}

            # Update basic fields if provided
            if 'name' in kw:
                update_vals['name'] = kw.get('name')
            if 'name_np' in kw:
                update_vals['name_np'] = kw.get('name_np')
            if 'list_price' in kw:
                update_vals['list_price'] = float(kw.get('list_price'))
            if 'standard_price' in kw:
                update_vals['standard_price'] = float(kw.get('standard_price'))
            if 'min_qty' in kw:
                update_vals['min_qty'] = float(kw.get('min_qty'))
            if 'max_qty' in kw:
                update_vals['max_qty'] = float(kw.get('max_qty'))
            if 'image_1920' in kw:
                image_1920 = kw.get('image_1920')
                update_vals['image_1920'] = base64.b64encode(image_1920.read())

            # Process product attributes
            # attributes = []
            # for key in kw:
            #     if key.startswith('attributes'):
            #         parts = key.split('[')
            #         attr_index = int(parts[1][:-1])
            #         sub_key = parts[2][:-1] if len(parts) > 2 else None

            #         while len(attributes) <= attr_index:
            #             attributes.append({'values': []})

            #         if sub_key in ['id', 'name']:
            #             attributes[attr_index][sub_key] = kw[key]
            #         elif sub_key.startswith('values'):
            #             value_index = int(parts[3][:-1])
            #             value_sub_key = parts[4][:-1]

            #             while len(attributes[attr_index]['values']) <= value_index:
            #                 attributes[attr_index]['values'].append({})

            #             attributes[attr_index]['values'][value_index][value_sub_key] = kw[key]

            # attributes_data = []
            # for attr in attributes:
            #     attribute_id = int(attr.get('id'))
            #     value_ids = []
            #     for value in attr.get('values', []):
            #         value_id = int(value.get('id'))
            #         value_ids.append(value_id)

            #     attributes_data.append((0, 0, {
            #         'attribute_id': attribute_id,
            #         'value_ids': [(6, 0, value_ids)],
            #     }))

            # Update the product with the new values and attributes
            product.sudo().write({
                'name': update_vals.get('name'),
                'standard_price': update_vals.get('standard_price'),
                'list_price': update_vals.get('list_price'),
                'min_qty': update_vals.get('min_qty'),
                'max_qty': update_vals.get('max_qty'),
                # 'attribute_line_ids': [(5, 0, 0)] + attributes_data,
            })

            return request.make_response(
                json.dumps({"status": "success", "message": "Product updated successfully"}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return http.Response(
                status=401,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                content_type='application/json'
            )

            
    @http.route('/trading/api/delete_product',cors="*",auth="public", methods=['DELETE'], csrf=False)
    def delete_product(self, **kw):
        try:

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )
            product_id = kw.get('product_id')
            if not product_id:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Product ID is required"
                        }
                    }),
                    content_type="application/json"
                )

           
            product = request.env['product.template'].sudo().search([('id', '=', int(product_id))], limit=1)
            if not product:
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Product not found"
                        }
                    }),
                    content_type="application/json"
                )

        
            product.unlink()

            return http.Response(
                status=200,
                response=json.dumps({
                    "status": "success",
                    "data": {
                        "message": "Product successfully deleted"
                    }
                }),
                content_type="application/json"
            )

        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                content_type="application/json"
            )
    
class companyCategory(http.Controller):

    @http.route("/trading/api/get_company_category", type="http",cors="*",auth="public",  methods=["GET"], csrf=False)
    def get_company_category(self,**kw):
        try:
            company_id = kw.get('company_id')
            if company_id:
                company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
                if not company:
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail", 
                            "data":{
                                "message": "Company not found"
                            }}),
                        content_type="application/json"
                    )
                records = company.company_category
            else:
                records = request.env["company.category"].sudo().search([])
            
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.name,
                        "name_np": record.name_np,
                        # "company_id":record.
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
            
            


    @http.route("/trading/api/create_company_category", type="http",cors="*",auth="public",  methods=["POST"], csrf=False)
    def create_company_category(self,**kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                        
                    ],
                    status=status_code
                )

            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            category_name = json_data.get('category_name')
            name_np = json_data.get('name_np')

            print("fdsfhsdjhjf",category_name)
            existing_category = request.env["company.category"].sudo().search([('name', '=', category_name)], limit=1)
            if existing_category:
                return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": f"Company category '{existing_category.name}' already exist"
                        }}),
                    content_type='application/json'
                )
                
            new_category  = request.env["company.category"].sudo().create({'name':category_name, 'name_np': name_np})
          
            return http.Response(
                response=json.dumps({
                    "status":"success",
                    "data":{
                        "message": "Company category created successfully",
                        "category_id":new_category.id
                    }}),
                content_type='application/json'
            )
               
        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
class ProductRequestController(http.Controller):
    @http.route("/trading/api/get_product_requests", type="http", cors="*", auth="public", methods=["GET"], csrf=False)
    def get_product_requests(self, **kw):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Set up domain filters based on parameters
            domain = []
            company_id = kw.get('company_id')
            request_id = kw.get('request_id')
            state = kw.get('state')
            business_type_id = kw.get('business_type_id')
            
            # Apply filters
            if company_id:
                if not company_id == '1':
                    domain.append(('company_id', '=', int(company_id)))
            if request_id:
                domain.append(('id', '=', int(request_id)))
            if state:
                domain.append(('state', '=', state))
            if business_type_id:
                domain.append(('product_business_type', 'in', [int(business_type_id)]))
            
            # Fetch requests based on domain
            requests = request.env['product.request'].sudo().search(domain)
            
            # Prepare response data
            data = []
            for prod_request in requests:
                # Get business types data
                business_types = []
                for business_type in prod_request.product_business_type:
                    business_types.append({
                        "id": business_type.id,
                        "name": business_type.name,
                        "name_np": business_type.name_np
                    })
                
                data.append({
                    "id": prod_request.id,
                    "name": prod_request.name if prod_request.name else None,
                    "description": prod_request.description if prod_request.description else None,
                    "sale_price": prod_request.sale_price if prod_request.sale_price else 0.0,
                    "cost_price": prod_request.cost_price if prod_request.cost_price else 0.0,
                    "company_id": prod_request.company_id.id if prod_request.company_id else None,
                    "state": prod_request.state if prod_request.state else 'draft',
                    # "create_uid": prod_request.create_uid.id if prod_request.create_uid else None,
                    "create_user_name": prod_request.create_uid.name if prod_request.create_uid and prod_request.create_uid.name else None,
                    "business_types": business_types
                })
            
            return request.make_response(
                json.dumps({
                    "status": "success",
                    "data": data
                }),
                headers=[("Content-Type", "application/json")]
            )

        except ValueError as e:
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": f"Invalid parameter value: {str(e)}"}
                }),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error in get_product_requests: {str(e)}")
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                headers=[('Content-Type', 'application/json')]
            )
    
    @http.route("/trading/api/create_product_request", type="http", cors="*", auth="public", methods=["POST"], csrf=False)
    def create_product_request(self, **kw):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Get form data - use kw directly since form data is passed in kw
            data = kw
            
            # Validate required fields
            required_fields = ['name', 'sale_price', 'cost_price', 'company_id', 'business_type_ids']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": f"Missing required fields: {', '.join(missing_fields)}"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Handle image from form-data
            image_binary = None
            if 'image' in request.httprequest.files:
                image_file = request.httprequest.files.get('image')
                if image_file:
                    image_binary = base64.b64encode(image_file.read())
            
            # Check if company exists
            company = request.env['res.company'].sudo().search([('id', '=', int(data.get('company_id')))], limit=1)
            if not company:
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "Company not found"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Validate prices
            sale_price = float(data.get('sale_price'))
            cost_price = float(data.get('cost_price'))
            
            if cost_price > sale_price:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "Cost price must be less than or equal to sale price"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Convert business_type_ids from string to list if needed
            business_type_ids = data.get('business_type_ids')
            if isinstance(business_type_ids, str):
                try:
                    # Try to parse as JSON if it's a string representation of a list
                    business_type_ids = json.loads(business_type_ids)
                except json.JSONDecodeError:
                    # If it's a comma-separated string
                    business_type_ids = [int(x.strip()) for x in business_type_ids.split(',') if x.strip().isdigit()]
            
            if not isinstance(business_type_ids, list):
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "business_type_ids must be a list of business type IDs"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Convert string IDs to integers if needed
            business_type_ids = [int(id) for id in business_type_ids]
            
            # Verify all business types exist
            business_types = request.env['company.category'].sudo().browse(business_type_ids)
            if len(business_types) != len(business_type_ids):
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "One or more business types not found"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Create the product request
            product_request = request.env['product.request'].sudo().create({
                'name': data.get('name'),
                'description': data.get('description'),
                'sale_price': sale_price,
                'cost_price': cost_price,
                'company_id': int(data.get('company_id')),
                'product_business_type': [(6, 0, business_type_ids)],
                'image_image': image_binary,
                'state': 'draft'
            })
            
            return request.make_response(
                json.dumps({
                    "status": "success",
                    "data": {
                        "id": product_request.id,
                        "message": "Product request created successfully"
                    }
                }),
                headers=[("Content-Type", "application/json")]
            )
            
        except ValueError as e:
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail", 
                    "data": {"message": f"Invalid parameter value: {str(e)}"}
                }),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error in create_product_request: {str(e)}")
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                headers=[('Content-Type', 'application/json')]
            )
        
    @http.route("/trading/api/approve_product_request/<int:request_id>", type="http", cors="*", auth="public", methods=["POST"], csrf=False)
    def approve_product_request(self, request_id, **kw):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Validate request_id
            if not request_id:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "Product request ID is required"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Find the product request
            product_request = request.env['product.request'].sudo().browse(request_id)
            if not product_request.exists():
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": f"Product request with ID {request_id} not found"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Check if already approved
            if product_request.state == 'approved':
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": "This product request is already approved"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Approve the product request
            try:
                # Create product
                product = request.env['product.template'].sudo().create({
                    'name': product_request.name,
                    'type': 'product',
                    'detailed_type': 'product',
                    'list_price': product_request.sale_price,
                    'standard_price': product_request.cost_price,
                    'description': product_request.description,
                    'image_1920': product_request.image_image,
                })
                
                # Create custom price entry
                custom_price_vals = {
                    'product_id': product.id,
                    'price_sell': product_request.sale_price,
                    'price_cost': product_request.cost_price,
                    'company_id': product_request.company_id.id,
                    'product_featured_image': product_request.image_image,
                    'saleable_qty': 0,
                    'min_qty': 0,
                    'max_qty': 0,
                }
                custom_price = request.env['product.custom.price'].sudo().create(custom_price_vals)
                
                
                # Add the product to each business type by updating their products_ids field
                for business_type in product_request.product_business_type:
                    # Create a business.based.products record
                    business_product = request.env['business.based.products'].sudo().create({
                        'product_id': product.id,
                        'company_id': product_request.company_id.id,
                    })
                    # Update the business_id on the business.based.products record
                    print("business_type", business_type)
                    business_product.business_id = business_type.id
                    
                    # Add the product to the business type's products_ids
                    business_type.write({
                        'products_ids': [(4, business_product.id)]
                    })
                
                # Update company's product list if needed
                product_request.company_id.sudo()._compute_company_category_product()
                
                # Mark request as approved
                product_request.sudo().write({'state': 'approved'})
                
                return request.make_response(
                    json.dumps({
                        "status": "success",
                        "data": {
                            "message": "Product request approved successfully",
                            "product_id": product.id,
                            "product_name": product.name
                        }
                    }),
                    headers=[("Content-Type", "application/json")]
                )
                
            except Exception as e:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {"message": f"Error during approval: {str(e)}"}
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
        except ValueError as e:
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": f"Invalid parameter value: {str(e)}"}
                }),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error in approve_product_request: {str(e)}")
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {"message": str(e)}
                }),
                headers=[('Content-Type', 'application/json')]
            )