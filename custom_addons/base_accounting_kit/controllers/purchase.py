from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
from datetime import datetime
import logging
import json
from odoo.exceptions import ValidationError
from . import jwt_token_auth
import jwt

_logger = logging.getLogger(__name__)

class Purchase(http.Controller):
    def _validate_received_products(self, purchase_order, demand_data):
        try:
            # Find the warehouse operation related to the purchase order
            warehouse_origin = purchase_order.name
            warehouse_operation = request.env['stock.picking'].sudo().search([
                ('origin', '=', warehouse_origin),
                ('state', '=', 'assigned')
            ], limit=1)

            if not warehouse_operation:
                return {'status': 'fail', 'data': {'message': 'Warehouse operation not found'}}, 404

            product_id_to_move = {move.product_id.id: move for move in warehouse_operation.move_ids}

            # Update quantities based on demand data or default to the requested quantities
            for line in purchase_order.order_line:
                product_id = line.product_id.id
                quantity = demand_data.get(str(product_id), line.product_qty)  # Use demand data if available, otherwise use requested quantity

                move_line = product_id_to_move.get(product_id)
                if not move_line: 
                    return {'status': 'fail', 'data': {'message': f'Product not found: {product_id} in warehouse operation'}}, 404

                move_line.write({
                    'product_uom_qty': quantity,
                    'quantity': quantity
                })

            # Validate the warehouse operation
            warehouse_operation.sudo().with_context(skip_backorder=True).button_validate()

            return {
                'status': 'success',
                'data': {
                    'message': 'Warehouse operation validated successfully',
                    'picking_id': warehouse_operation.id
                }
            }, 200

        except Exception as e:
            return {'status': 'fail', 'data': {'message': 'Internal server error', 'details': str(e)}}, 500
        
    def confirm_purchase_order_logic(self, order):
        if order.state not in ['draft', 'sent']:
            return {'status': 'fail', 'data': {'message': f'Purchase order is in {order.state} state and cannot be confirmed'}}, 400

        order.sudo().with_context(from_api=True, validate_analytic=True).button_confirm()
        print(order.state)
        return {
            'status': 'success',
            'data': {
                'message': f'Purchase order {order.id} confirmed successfully',
                'purchase_order_id': order.id,
                'state': order.state
            }
        }, 200
    
    @http.route('/trading/api/get_purchase_order', type='http',cors="*",auth="public",  methods=['GET'], csrf=False)
    def get_purchase_order(self, **kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            state = kwargs.get('state')
            vendor = kwargs.get('vendor_id')
            name = kwargs.get('name')
            company = kwargs.get('company_id')
            user = kwargs.get('buyer_id')

            domain = []
            
            if state:
                domain.append(('state', '=', state))
            if vendor:
                domain.append(('partner_id.id', '=', vendor))
            if name:
                domain.append(('name', '=', name))
            if company and company is not 1:
                domain.append(('company_id.id', '=', company))
            if user:
                domain.append(('user_id.id', '=', user))
                
            purchase_orders = request.env['purchase.order'].sudo().search(domain)

            purchase_order_details = []
            for purchase in purchase_orders:
                order_lines = []
                for line in purchase.order_line:
                    order_lines.append({
                        'product': line.product_id.display_name,
                        'quantity': line.product_qty,
                        'price_unit': line.price_unit,
                        'subtotal': line.price_subtotal,
                        'tax_amount': sum(tax.amount for tax in line.taxes_id),
                    })
                
                purchase_order_details.append({
                    'id': purchase.id if purchase.id else None,
                    'name': purchase.name if purchase.name else None,
                    'vendor': purchase.partner_id.name if purchase.partner_id and purchase.partner_id.name else None,
                    'vendor_np': purchase.partner_id.name_np if purchase.partner_id and purchase.partner_id.name_np else None,
                    'state': purchase.state if purchase.state else None,
                    'company': purchase.company_id.name if purchase.company_id and purchase.company_id.name else None,
                    'company_np': purchase.company_id.name_np if purchase.company_id and purchase.company_id.name_np else None,
                    'buyer': purchase.user_id.name if purchase.user_id and purchase.user_id.name else None,
                    'buyer_np': purchase.user_id.name_np if purchase.user_id and purchase.user_id.name_np else None,
                    'total': purchase.amount_total if purchase.amount_total else None,
                    'untaxed_amount': purchase.amount_untaxed if purchase.amount_untaxed else None,
                    'tax_amount': purchase.amount_tax if purchase.amount_tax else None,
                    'confirmation_date': purchase.date_approve.strftime('%Y-%m-%d %H:%M:%S') if purchase.date_approve else None,
                    'expected_date': purchase.date_planned.strftime('%Y-%m-%d %H:%M:%S') if purchase.date_planned else None,
                    'arrival_date': purchase.effective_date.strftime('%Y-%m-%d %H:%M:%S') if purchase.effective_date else None,
                    'order_lines': order_lines if order_lines else None
                })

            return request.make_response(
                json.dumps({"status": "success", "data": purchase_order_details}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            _logger.error(f"Error occurred: {e}")

            return http.Response(
                status=400,
                response=json.dumps({
                    "status":"error",
                    "data":{
                        "message": str(e)
                    }}),
                content_type='application/json'
            )

    @http.route('/trading/api/get_purchase_order_bill/<int:purchase_id>', type='http', cors="*", auth="public", methods=['GET'], csrf=False)
    def get_purchase_order_bill(self, purchase_id, **kwargs):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # No need to get purchase_id from kwargs, it's directly in the function parameters
            if not purchase_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Purchase order ID is required'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Rest of the code remains the same
            purchase_order = request.env['purchase.order'].sudo().browse(int(purchase_id))
            if not purchase_order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'Purchase order with ID {purchase_id} not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Find associated vendor bills (invoices) for this purchase order
            invoice_origin = purchase_order.name if purchase_order.name else None
            invoices = request.env['account.move'].sudo().search([
                ('invoice_origin', '=', invoice_origin),
                ('move_type', '=', 'in_invoice')  # Vendor bill
            ])
            
            if not invoices:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'No bills found for purchase order {purchase_order.name if purchase_order.name else purchase_id}'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Prepare response data with invoice details
            invoice_list = []
            for invoice in invoices:
                invoice_lines = []
                for line in invoice.invoice_line_ids:
                    tax_info = []
                    for tax in line.tax_ids:
                        tax_info.append({
                            'tax_id': tax.id if tax.id else None,
                            'tax_name': tax.name if tax.name else None,
                            'tax_amount': tax.amount if tax.amount else None
                        })
                    
                    invoice_lines.append({
                        'product_id': line.product_id.id if line.product_id else None,
                        'product_name': line.product_id.name if line.product_id and line.product_id.name else line.name if line.name else None,
                        'description': line.name if line.name else None,
                        'quantity': line.quantity if line.quantity else None,
                        'price_unit': line.price_unit if line.price_unit else None,
                        'price_subtotal': line.price_subtotal if line.price_subtotal else None,
                        'account_id': line.account_id.id if line.account_id else None,
                        'account_name': line.account_id.name if line.account_id and line.account_id.name else None,
                        'taxes': tax_info
                    })
                
                # Prepare payment information
                payment_info = []
                if invoice.payment_state in ['paid', 'partial']:
                    payments = invoice.sudo()._get_reconciled_payments()
                    for payment in payments:
                        payment_info.append({
                            'payment_id': payment.id if payment.id else None,
                            'payment_name': payment.name if payment.name else None,
                            'payment_date': payment.date.strftime('%Y-%m-%d') if payment.date else None,
                            'journal_id': payment.journal_id.id if payment.journal_id else None,
                            'journal_name': payment.journal_id.name if payment.journal_id and payment.journal_id.name else None,
                            'payment_method': payment.payment_method_line_id.name if payment.payment_method_line_id and payment.payment_method_line_id.name else None,
                            'amount': payment.amount if payment.amount else None,
                            'currency': payment.currency_id.name if payment.currency_id and payment.currency_id.name else None
                        })
                
                invoice_list.append({
                    'invoice_id': invoice.id if invoice.id else None,
                    'invoice_name': invoice.name if invoice.name else None,
                    'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else None,
                    'due_date': invoice.invoice_date_due.strftime('%Y-%m-%d') if invoice.invoice_date_due else None,
                    'vendor_id': invoice.partner_id.id if invoice.partner_id else None,
                    'vendor_name': invoice.partner_id.name if invoice.partner_id and invoice.partner_id.name else None,
                    'vendor_vat': invoice.partner_id.vat if invoice.partner_id and invoice.partner_id.vat else None,
                    'company_id': invoice.company_id.id if invoice.company_id else None,
                    'company_name': invoice.company_id.name if invoice.company_id and invoice.company_id.name else None,
                    'state': invoice.state if invoice.state else None,
                    'payment_state': invoice.payment_state if invoice.payment_state else None,
                    'currency': invoice.currency_id.name if invoice.currency_id and invoice.currency_id.name else None,
                    'amount_untaxed': invoice.amount_untaxed if hasattr(invoice, 'amount_untaxed') else None,
                    'amount_tax': invoice.amount_tax if hasattr(invoice, 'amount_tax') else None,
                    'amount_total': invoice.amount_total if hasattr(invoice, 'amount_total') else None,
                    'amount_residual': invoice.amount_residual if hasattr(invoice, 'amount_residual') else None,
                    'invoice_lines': invoice_lines,
                    'payments': payment_info,
                    'journal_id': invoice.journal_id.id if invoice.journal_id else None,
                    'journal_name': invoice.journal_id.name if invoice.journal_id and invoice.journal_id.name else None,
                    'reference': invoice.ref if invoice.ref else None,
                    'narration': invoice.narration if invoice.narration else None
                })
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'purchase_order_id': purchase_order.id if purchase_order.id else None,
                        'purchase_order_name': purchase_order.name if purchase_order.name else None,
                        'bills': invoice_list
                    }
                }, default=str),  # default=str handles serialization of date objects
                headers=[('Content-Type', 'application/json')],
                status=200
            )
            
        except ValueError as e:
            # Handle value errors (e.g., invalid ID format)
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': f'Invalid value: {str(e)}'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
        except Exception as e:
            # Log the full exception for debugging
            _logger.exception(f"Error in get_purchase_order_bill: {str(e)}")
            
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

    @http.route('/trading/api/create_purchase_orders', type='http', cors="*", auth="public", csrf=False, methods=['POST'])
    def create_purchase_orders(self, **kw):
        try:
            # Step 1: Authenticate the request using JWT
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Step 2: Parse JSON data from the request
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)

            # Step 3: Retrieve Vendor
            vendor_id = json_data.get('vendor')
            vendor = request.env['res.partner'].sudo().search([('id', '=', vendor_id)], limit=1)
            if not vendor:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Vendor {vendor_id} not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Step 4: Prepare Purchase Order values
            fiscal_year = None
            deadline_date = json_data.get('deadline_date')
            if deadline_date:
                fiscal_year = request.env['account.fiscal.year'].sudo().search([
                    ('date_from', '<=', deadline_date),
                    ('date_to', '>=', deadline_date),
                    ('company_id', '=', 1)
                ], limit=1) 
            user = request.env['res.users'].sudo().browse(auth_status['user_id'])
            company = request.env['res.company'].sudo().browse(auth_status['company_id'])    
            purchase_order_vals = {
                'partner_id': vendor.id,
                'partner_ref': json_data.get('reference'),
                'date_order': deadline_date,
                'date_planned': json_data.get('expected_date'),
                'fiscal_year': fiscal_year.id if fiscal_year else None,
                'order_line': [],
                'user_id': user.id,
                'company_id': company.id,
                'create_uid': user.id,
                'write_uid': user.id,
            }

            # Step 5: Validate and Prepare Order Lines
            order_lines = json_data.get('order_lines', [])
            if not order_lines:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'At least one order line is required'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            for line in order_lines:
                product_id = line.get('product_id')
                if not product_id:
                    return request.make_response(
                        json.dumps({'status': 'fail', 'data': {'message': 'Product id is required for each order line'}}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )
                product_template = request.env['product.template'].search([('id', '=', product_id)], limit=1)

                if len(product_template.product_variant_ids) == 1:
                    print("Product Variant ID:", product_template.product_variant_id.id)
                    product = product_template.product_variant_id
                else:
                    print("Product Variant IDs:", product_template.product_variant_ids.ids)
                    product = product_template.product_variant_ids[:1] 

                if not product:
                    return request.make_response(
                        json.dumps({'status': 'fail', 'data': {'message': f'Product not found: {product_id}'}}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

                line_vals = {
                    'product_id': product.id,
                    'name': line.get('description', product.name),
                    'product_qty': line.get('quantity'),
                    'price_unit': line.get('price_unit'),
                    'date_planned': purchase_order_vals['date_planned'],
                }
                purchase_order_vals['order_line'].append((0, 0, line_vals))

            # Step 6: Create the Purchase Order
            purchase_order = request.env['purchase.order'].sudo().create(purchase_order_vals)

            # Step 7: Confirm the Purchase Order
            response, status = Purchase().confirm_purchase_order_logic(purchase_order)
            if status != 200:
                return request.make_response(
                    json.dumps(response),
                    headers=[("Content-Type", "application/json")],
                    status=status
                )

            # Step 8: Validate Warehouse Operations (Receipt Validation)
            demand_data = json_data.get("demand", {})
            validate_response, validate_status = self._validate_received_products(purchase_order, demand_data)
            if validate_status != 200:
                return request.make_response(
                    json.dumps(validate_response),
                    headers=[("Content-Type", "application/json")],
                    status=validate_status
                )

            # Automating the three endpoints

            # Step 9: Create Purchase Order Invoice
            self.create_purchase_order_invoice(purchase_order.id)

            # Step 10: Set the Invoice Date and Account Move Date
            # Step 10.1: Get today's date in the required format (YYYY-MM-DD)
            today_date = datetime.today().strftime('%Y-%m-%d')

            # Step 10.2: Set the date_data to today's date
            date_data = {
                'invoice_date': today_date,
                'date': today_date
            }
            self.po_account_move_set_date(purchase_order.id, **date_data)

            # Step 11: Confirm the Purchase Order Bill
            self.confirm_po_bill(purchase_order.id)

            # Step 12: Return Success Response
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Purchase order created, invoiced, and confirmed',
                        'purchase_order_id': purchase_order.id,
                        'confirmation': response['data']
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

    
    @http.route('/trading/api/confirm_purchase_order/<int:order_id>', type='http',cors="*",auth="public",  csrf=False, methods=['POST'])
    def confirm_purchase_order(self, order_id, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            order = request.env['purchase.order'].sudo().browse(order_id)

            if not order.exists():
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Purchase order with id {order_id} not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            if order.state not in ['draft', 'sent']:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Purchase order is in {order.state} state and cannot be confirmed'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            order.sudo().with_context(from_api=True, validate_analytic=True).button_confirm()

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': f'Purchase order {order_id} confirmed successfully',
                        'purchase_order_id': order.id,
                        'state': order.state
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

    @http.route('/trading/api/validate_recieved_products/<int:order_id>', type='http',cors="*",auth="public",  csrf=False, methods=['POST'])
    def validate_recieved_products(self, order_id, **kw):
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

            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Order not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            warehouse_origin = order.name
            warehouse_operation = request.env['stock.picking'].search([
                ('origin', '=', warehouse_origin),
                ('state', '=', 'assigned')
            ], limit=1)

            if not warehouse_operation:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Warehouse operation not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            demand_data = json_data.get("demand")
            if not demand_data:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Demand data is missing'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            product_id_to_move = {move.product_id.id: move for move in warehouse_operation.move_ids}

            for line in demand_data:
                product_id = line.get('product_id')
                quantity = line.get('quantity')

                if not product_id or quantity is None:
                    return request.make_response(
                        json.dumps({'status': 'fail', 'data': {'message': f'Invalid demand data: {line}'}}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )

                move_line = product_id_to_move.get(product_id)
                if not move_line:
                    return request.make_response(
                        json.dumps({'status': 'fail', 'data': {'message': f'Product not found: {product_id}'}}),
                        headers=[('Content-Type', 'application/json')],
                        status=404
                    )

                move_line.write({
                    'product_uom_qty': quantity,
                    'quantity': quantity
                })


            warehouse_operation.with_context(skip_backorder=True).button_validate()

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Warehouse operation validated successfully',
                        'picking_id': warehouse_operation.id
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

    @http.route('/trading/api/create_purchase_order_invoice/<int:order_id>', type='http',cors="*",auth="public",  csrf=False, methods=['POST'])
    def create_purchase_order_invoice(self, order_id, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Order not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            if order.invoice_status != 'to invoice':
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Order is not ready to be invoiced'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            order.action_create_invoice()

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Invoice created successfully',
                        'order_id': order_id
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

    @http.route('/trading/api/po_account_move_set_date/<int:order_id>', type='http',cors="*",auth="public",  csrf=False, methods=['POST'])
    def po_account_move_set_date(self, order_id, **kw):
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
            invoice_date = json_data.get('invoice_date')
            date = json_data.get('date')

            if not order_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Order ID is required'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Order not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            invoice_origin = order.name
            invoice = request.env['account.move'].search([
                ('invoice_origin', '=', invoice_origin),
                ('state', '=', 'draft')
            ], limit=1)

            if invoice:
                invoice.write({
                    'invoice_date': invoice_date,
                    "date": date
                })
                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': {
                            'message': 'Dates Set Successfully'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )
            else:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Could Not Set Date'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': f'Error {str(e)}'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/trading/api/confirm_po_bill/<int:order_id>', type='http', cors="*", auth="public", csrf=False, methods=['POST'])
    def confirm_po_bill(self, order_id, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            if not order_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Order ID is required'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Order not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            invoice_origin = order.name
            invoice = request.env['account.move'].search([
                ('invoice_origin', '=', invoice_origin),
                ('state', '=', 'draft')
            ], limit=1)

            if not invoice:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'No draft invoice found for this purchase order'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # DIRECT APPROACH: Instead of using action_post which checks for balanced entries,
            # we'll manually create the balancing entry and then post the invoice

            # 1. Get the total amount that needs balancing
            debit_total = 0
            credit_total = 0
            
            for line in invoice.line_ids:
                debit_total += line.debit
                credit_total += line.credit
            
            imbalance = debit_total - credit_total
            
            _logger.info(f"Invoice before balancing: Debit={debit_total}, Credit={credit_total}, Imbalance={imbalance}")
            
            if abs(imbalance) > 0.001:  # Small threshold for float comparison
                # 2. Find the appropriate payable account
                payable_account = request.env['account.account'].sudo().search([
                    ('company_id', '=', invoice.company_id.id),
                    ('account_type', '=', 'liability_payable')
                ], limit=1)
                
                if not payable_account:
                    return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data': {
                                'message': 'No payable account found for creating balancing entry'
                            }
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=500
                    )
                
                # 3. Create a balancing line with the appropriate debit/credit
                if imbalance > 0:
                    # We need more credit
                    balancing_vals = {
                        'name': 'Balancing Entry',
                        'account_id': payable_account.id,
                        'credit': imbalance,
                        'debit': 0.0,
                        'move_id': invoice.id,
                        'partner_id': invoice.partner_id.id,
                    }
                else:
                    # We need more debit
                    balancing_vals = {
                        'name': 'Balancing Entry',
                        'account_id': payable_account.id,
                        'debit': abs(imbalance),
                        'credit': 0.0,
                        'move_id': invoice.id,
                        'partner_id': invoice.partner_id.id,
                    }
                
                # 4. Create the balancing line directly
                request.env['account.move.line'].sudo().create(balancing_vals)
                
                # 5. Check if balanced now
                debit_total = sum(line.debit for line in invoice.line_ids)
                credit_total = sum(line.credit for line in invoice.line_ids)
                new_imbalance = debit_total - credit_total
                
                _logger.info(f"Invoice after balancing: Debit={debit_total}, Credit={credit_total}, Imbalance={new_imbalance}")
                
                if abs(new_imbalance) > 0.001:
                    return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data': {
                                'message': 'Failed to balance invoice even after creating balancing entry',
                                'details': f"Debit={debit_total}, Credit={credit_total}, Imbalance={new_imbalance}"
                            }
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=500
                    )
            
            # 6. Set the invoice to posted state directly
            try:
                invoice.sudo().with_context(from_api=True, check_move_validity=False).action_post()
                
                # 7. Check if posted successfully
                if invoice.state != 'posted':
                    return request.make_response(
                        json.dumps({
                            'status': 'fail',
                            'data': {
                                'message': 'Failed to post invoice even after balancing',
                                'details': f"Current state: {invoice.state}"
                            }
                        }),
                        headers=[('Content-Type', 'application/json')],
                        status=500
                    )
                
                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': {
                            'message': 'Bill Confirmed',
                            'invoice_id': invoice.id,
                            'invoice_number': invoice.name,
                            'amount_total': invoice.amount_total,
                            'amount_residual': invoice.amount_residual
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )
            except Exception as e:
                _logger.exception(f"Error posting invoice: {str(e)}")
                
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Could Not Confirm Bill',
                            'details': str(e)
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )

        except Exception as e:
            _logger.exception(f"Exception in confirm_po_bill: {str(e)}")
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': f'Error {str(e)}'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    @http.route('/trading/api/pay_bill/<int:order_id>', type='http',cors="*",auth="public",  csrf=False, methods=['POST'])
    def pay_bill(self, order_id, **kw):
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
            journal_id = json_data.get('journal_id')
            payment_method_line_id = json_data.get('payment_method_line_id')
            payment_date = json_data.get('payment_date')
            effective_date = json_data.get('effective_date')
            bank_reference = json_data.get('bank_reference')
            cheque_reference = json_data.get('cheque_reference')

            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Order not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            invoice_origin = order.name
            invoice = request.env['account.move'].search([
                ('invoice_origin', '=', invoice_origin),
                ('state', '=', 'posted'),
                ('payment_state', '=', 'not_paid')
            ], limit=1)

            if not invoice.exists() or invoice.state != 'posted':
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Invoice not found or not in posted state'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            form_action = invoice.sudo().with_context(
                from_api=True,
                active_model='account.move.line',
                active_ids=invoice.ids
            ).action_register_payment()

            PaymentRegister = invoice.env['account.payment.register']
            context = form_action['context']

            journal = request.env['account.journal'].search([('id', '=', journal_id)], limit=1)
            if not journal:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Invalid journal id'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            payment_method = request.env['account.payment.method.line'].search([('id', '=', payment_method_line_id)], limit=1)
            if not payment_method:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Invalid payment method'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            context.update({
                'default_journal_id': journal.id,
                'default_payment_method_line_id': payment_method.id,
                'default_payment_date': payment_date,
                'default_effective_date': effective_date,
                'default_bank_reference': bank_reference,
                'default_cheque_reference': cheque_reference,
            })

            wizard = PaymentRegister.with_context(context).create({})
            wizard.action_create_payments()

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Payment Registered'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.exception("Failed to pay bill")
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': f'Error {str(e)}'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    # @http.route('/trading/api/create_purchase_order_report/<int:order_id>', type='http',cors="*",auth="public",  csrf=False, methods=['POST'])
    # def create_purchase_order_report(self, order_id, **kw):
    #     try:
    #         auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
    #         if auth_status['status'] == 'fail':
    #             return request.make_response(
    #                 json.dumps(auth_status),
    #                 headers=[('Content-Type', 'application/json')],
    #                 status=status_code
    #             )
    #         raw_data = request.httprequest.data
    #         json_data = json.loads(raw_data)

    #         order = request.env['purchase.order'].browse(order_id)
    #         if not order.exists():
    #             return request.make_response(
    #                 json.dumps({
    #                     'status': 'fail',
    #                     'data': {
    #                         'message': 'Purchase order not found'
    #                     }
    #                 }),
    #                 headers=[('Content-Type', 'application/json')],
    #                 status=404
    #             )

    #         report_name = 'purchase.report_purchaseorder'
    #         report = request.env['ir.actions.report'].sudo()._get_report_from_name(report_name)
    #         pdf_content, _ = request.env['ir.actions.report'].sudo().render_qweb_pdf([order.id])

    #         pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

    #         return request.make_response(
    #             json.dumps({
    #                 'status': 'success',
    #                 'data': {
    #                     'pdf_base64': pdf_base64,
    #                     'filename': f'Purchase_Order_{order.name}.pdf'
    #                 }
    #             }),
    #             headers=[('Content-Type', 'application/json')],
    #             status=200
    #         )

    #     except Exception as e:
    #         return request.make_response(
    #             json.dumps({
    #                 'status': 'fail',
    #                 'data': {
    #                     'message': f'Error {str(e)}'
    #                 }
    #             }),
    #             headers=[('Content-Type', 'application/json')],
    #             status=500
    #         )
    
    @http.route('/trading/api/delete_purchase_order/<int:order_id>', type='http',cors="*",auth="public",  csrf=False, methods=['POST'])
    def delete_purchase_order(self, order_id, **kw):
        try:
            # Authenticate Request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Validate Purchase Order ID
            if not order_id:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Purchase order ID is required'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Search for the Purchase Order
            purchase_order = request.env['purchase.order'].sudo().search([('id', '=', order_id)], limit=1)
            if not purchase_order:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Purchase order {order_id} not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Check related warehouse operations (pickings)
            stock_pickings = purchase_order.picking_ids
            validated_pickings = stock_pickings.filtered(lambda p: p.state == 'done')
            non_validated_pickings = stock_pickings.filtered(lambda p: p.state != 'done')

            # If any picking is validated, do not delete the PO
            if validated_pickings:
                # Cancel and set bills to draft if paid
                vendor_bills = purchase_order.invoice_ids
                for bill in vendor_bills:
                    if bill.state in ['posted', 'paid']:
                        if bill.state == 'paid':
                            # Reset bill to draft
                            bill.sudo().button_draft()
                        bill.sudo().button_cancel()

                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Cannot delete purchase order because some warehouse operations are validated.'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # If no pickings are validated, delete non-validated pickings
            for picking in non_validated_pickings:
                picking.sudo().action_cancel()  # Cancel picking before deletion
                picking.sudo().unlink()  # Delete the picking

            # Delete or archive related vendor bills if not already handled
            vendor_bills = purchase_order.invoice_ids
            for bill in vendor_bills:
                if bill.state != 'cancel':
                    bill.sudo().button_cancel()  # Cancel bill before deletion
                bill.sudo().unlink()

            # Cancel the Purchase Order before deletion
            if purchase_order.state != 'cancel':
                purchase_order.sudo().button_cancel()

            # Finally, delete the purchase order
            purchase_order.sudo().unlink()

            # Return success response
            return request.make_response(
                json.dumps({'status': 'success', 'data': {'message': 'Purchase order deleted successfully'}}),
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
    
    @http.route('/trading/api/get_purchase_order_report/<int:order_id>', type='http', cors="*", auth="public", csrf=False, methods=['GET'])
    def get_purchase_order_report(self, order_id, **kw):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Validate order_id
            if not order_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Purchase order ID is required'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Check if purchase order exists
            purchase_order = request.env['purchase.order'].sudo().browse(order_id)
            if not purchase_order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'Purchase order with ID {order_id} not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Generate the report URL
            base_url = "http://lekhaplus.com"
            report_url = f"{base_url}/report/public/pdf/purchase.report_purchaseorder/{order_id}"
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'report_url': report_url
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )
        
        except Exception as e:
            _logger.exception(f"Error in get_purchase_order_report: {str(e)}")
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

    @http.route('/trading/api/get_purchase_order_receipt/<int:order_id>', type='http', cors="*", auth="public", csrf=False, methods=['GET'])
    def get_purchase_order_receipt(self, order_id, **kwargs):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Validate order_id
            if not order_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Purchase order ID is required'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Fetch the purchase order
            purchase_order = request.env['purchase.order'].sudo().browse(order_id)
            if not purchase_order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'Purchase order with ID {order_id} not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Fetch associated stock pickings (receipts)
            pickings = purchase_order.picking_ids
            
            if not pickings:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'No receipt orders found for purchase order {purchase_order.name}'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Prepare response data with picking details
            picking_list = []
            for picking in pickings:
                move_lines = []
                for move in picking.move_ids:
                    move_lines.append({
                        'product_id': move.product_id.id if move.product_id else None,
                        'product_name': move.product_id.name if move.product_id and move.product_id.name else None,
                        'description': move.description_picking if move.description_picking else None,
                        'quantity_demand': move.product_uom_qty if hasattr(move, 'product_uom_qty') else 0.0,
                        'quantity_done': move.quantity_done if hasattr(move, 'quantity_done') else 0.0,
                        'product_uom': move.product_uom.name if move.product_uom else None,
                        'state': move.state if move.state else None,
                        'lot_ids': [lot.id for lot in move.move_line_ids.mapped('lot_id')] if move.move_line_ids else [],
                        'lot_names': [lot.name for lot in move.move_line_ids.mapped('lot_id')] if move.move_line_ids else []
                    })
                
                # Add receipt report URL
                base_url = "http://lekhaplus.com"
                report_url = f"{base_url}/report/pdf/stock.report_reception/{picking.id}" if picking else None
                
                picking_list.append({
                    'picking_id': picking.id if picking.id else None,
                    'picking_name': picking.name if picking.name else None,
                    'picking_type': picking.picking_type_id.name if picking.picking_type_id and picking.picking_type_id.name else None,
                    'partner_id': picking.partner_id.id if picking.partner_id else None,
                    'partner_name': picking.partner_id.name if picking.partner_id and picking.partner_id.name else None,
                    'scheduled_date': picking.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if picking.scheduled_date else None,
                    'date_done': picking.date_done.strftime('%Y-%m-%d %H:%M:%S') if picking.date_done else None,
                    'origin': picking.origin if picking.origin else None,
                    'state': picking.state if picking.state else None,
                    'move_lines': move_lines,
                    'report_url': report_url,
                    'location_id': picking.location_id.id if picking.location_id else None,
                    'location_name': picking.location_id.name if picking.location_id and picking.location_id.name else None,
                    'location_dest_id': picking.location_dest_id.id if picking.location_dest_id else None,
                    'location_dest_name': picking.location_dest_id.name if picking.location_dest_id and picking.location_dest_id.name else None,
                    'backorder_id': picking.backorder_id.id if picking.backorder_id else None,
                    'backorder_name': picking.backorder_id.name if picking.backorder_id and picking.backorder_id.name else None,
                    'company_id': picking.company_id.id if picking.company_id else None,
                    'company_name': picking.company_id.name if picking.company_id and picking.company_id.name else None
                })
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'purchase_order_id': purchase_order.id if purchase_order.id else None,
                        'purchase_order_name': purchase_order.name if purchase_order.name else None,
                        'pickings': picking_list
                    }
                }, default=str),  # default=str handles serialization of date objects
                headers=[('Content-Type', 'application/json')],
                status=200
            )
        
        except ValueError as e:
            # Handle value errors (e.g., invalid ID format)
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': f'Invalid value: {str(e)}'
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
        except Exception as e:
            # Log the full exception for debugging
            _logger.exception(f"Error in get_purchase_order_receipt: {str(e)}")
            
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