from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
import jwt
import datetime
import logging
import json
from odoo.exceptions import ValidationError,UserError
from . import jwt_token_auth
import jwt

_logger = logging.getLogger(__name__)

class Sale(http.Controller):
    def _validate_delivered_products(self, sale_order, demand_data):
        try:
            # Find the warehouse operation related to the sale order
            warehouse_origin = sale_order.name
            print("warehouse_origin",warehouse_origin)
            warehouse_operation = request.env['stock.picking'].sudo().search([
                ('origin', '=', warehouse_origin),
                ('state', '=', 'assigned')
            ], limit=1)

            if not warehouse_operation:
                return {'status': 'fail', 'data': {'message': 'Warehouse operation not found'}}, 404

            product_id_to_move = {move.product_id.id: move for move in warehouse_operation.move_ids}

            # Update quantities based on demand data or default to the requested quantities
            for line in sale_order.order_line:
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
        
    def confirm_sale_order_logic(self, order):
        if order.state not in ['draft', 'sent']:
            return {'status': 'fail', 'data': {'message': f'Sale order is in {order.state} state and cannot be confirmed'}}, 400

        order.sudo().with_context(from_api=True, validate_analytic=True).action_confirm()

        return {
            'status': 'success',
            'data': {
                'message': f'Sale order {order.id} confirmed successfully',
                'sale_order_id': order.id,
                'state': order.state
            }
        }, 200
        
    @http.route('/trading/api/get_sale_order', type='http',auth='public',cors='*', methods=['GET'], csrf=False)
    def get_sale_order(self, **kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            state = kwargs.get('state')
            customer = kwargs.get('customer_id')
            company = kwargs.get('company_id')
            user = kwargs.get('buyer_id')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')  

            domain = []
            
            if state:
                domain.append(('state', '=', state))
            if customer:
                domain.append(('partner_id.id', '=', customer))
            if company and company is not 1:
                domain.append(('company_id.id', '=', company))
            if user:
                domain.append(('user_id.id', '=', user))
            if date_from:
                domain.append(('order_date', '>=', date_from))
            if date_to:
                domain.append(('order_date', '<=', date_to))
                
            sale_orders = request.env['sale.order'].sudo().search(domain)

            sale_order_details = []
            for sale in sale_orders:

                order_lines = []
                for line in sale.order_line:
                    order_lines.append({
                        'product': line.product_id.display_name,
                        'quantity': line.product_uom_qty,
                        'price_unit': line.price_unit,
                        'subtotal': line.price_subtotal,
                        'tax_amount': sum(tax.amount for tax in line.tax_id),
                    })

                sale_order_details.append({
                    'id': sale.id if sale.id else None,
                    'customer': sale.partner_id.name if sale.partner_id.name else None,
                    'customer_np': sale.partner_id.name_np if sale.partner_id.name_np else None,
                    'state': sale.state if sale.state else None,
                    'company': sale.company_id.name if sale.company_id.name else None,
                    'company_np': sale.company_id.name_np if sale.company_id.name_np else None,
                    'salesperson': sale.user_id.name if sale.user_id.name else None,
                    'salesperson_np': sale.user_id.name_np if sale.user_id.name_np else None,
                    'total': sale.amount_total if sale.amount_total else None,
                    'untaxed_amount': sale.amount_untaxed if sale.amount_untaxed else None,
                    'tax_amount': sale.amount_tax if sale.amount_tax else None,
                    'order_date': sale.date_order.strftime('%Y-%m-%d %H:%M:%S') if sale.date_order else None,
                    'order_lines': order_lines # Include order line details
                })

            return request.make_response(
                json.dumps({"status": "success", "data": sale_order_details}),
                headers=[('Content-Type', 'application/json')],
            )
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return http.Response(
                status=500,
                response=json.dumps({'error': 'Internal server error'}),
                content_type='application/json'
            )
    @http.route('/trading/api/get_sale_order_bill/<int:sale_order_id>', type='http', auth='public', cors='*', methods=['GET'], csrf=False)
    def get_sale_order_bill(self, sale_order_id, **kwargs):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Fetch the sale order
            sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
            if not sale_order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'Sale order with ID {sale_order_id} not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Fetch the related bill (invoice)
            invoices = request.env['account.move'].sudo().search([
                ('invoice_origin', '=', sale_order.name),
                ('move_type', '=', 'out_invoice')  # Ensure it's a customer invoice
            ])

            if not invoices:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'No bills found for sale order {sale_order.name}'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Prepare the bill data
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

            # Return the response in the same format as get_purchase_order_bill
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'sale_order_id': sale_order.id if sale_order.id else None,
                        'sale_order_name': sale_order.name if sale_order.name else None,
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
            _logger.error(f"Error occurred: {e}")
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
    @http.route('/trading/api/get_sale_order_receipt/<int:order_id>', type='http', cors="*", auth="public", csrf=False, methods=['GET'])
    def get_sale_order_receipt(self, order_id, **kwargs):
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
                            'message': 'Sale order ID is required'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Fetch the sale order
            sale_order = request.env['sale.order'].sudo().browse(order_id)
            if not sale_order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'Sale order with ID {order_id} not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Fetch associated stock pickings (delivery orders)
            pickings = sale_order.picking_ids
            
            if not pickings:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'No delivery orders found for sale order {sale_order.name}'
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
                        'quantity_demand': move.product_uom_qty if move.product_uom_qty else 0.0,
                        'quantity': move.quantity if move.quantity else 0.0,
                        'product_uom': move.product_uom.name if move.product_uom else None,
                        'state': move.state if move.state else None,
                        'lot_ids': [lot.id for lot in move.move_line_ids.mapped('lot_id')] if move.move_line_ids else [],
                        'lot_names': [lot.name for lot in move.move_line_ids.mapped('lot_id')] if move.move_line_ids else []
                    })
                
                # Add receipt report URL if picking exists
                base_url = "http://lekhaplus.com"
                report_url = f"{base_url}/report/public/pdf/stock.report_deliveryslip/{picking.id}" if picking else None
                
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
                        'sale_order_id': sale_order.id if sale_order.id else None,
                        'sale_order_name': sale_order.name if sale_order.name else None,
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
            _logger.exception(f"Error in get_sale_order_receipt: {str(e)}")
            
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
    
    @http.route('/trading/api/create_sale_orders', type='http',cors='*',auth='public', csrf=False, methods=['POST'])
    def create_sale_orders(self, **kw):
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

            customer_id = json_data.get('customer')
            print("passed customer",customer_id)
            if not customer_id:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Customer id is required'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            customer = request.env['res.partner'].sudo().search([('id', '=', customer_id)], limit=1)
            if not customer:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Customer {customer_id} not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            user = request.env['res.users'].sudo().browse(auth_status['user_id'])
            company = request.env['res.company'].sudo().browse(auth_status['company_id'])  
            sale_order_vals = {
                'partner_id': customer.id,
                'date_order': json_data.get('quotation_date'),
                'validity_date': json_data.get('expiry_date'),
                'order_line': [],
                'user_id': user.id,
                'company_id': company.id,
                'create_uid': user.id,
                'write_uid': user.id,
            }

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
                    product = product_template.product_variant_id
                else:
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
                    'product_uom_qty': line.get('quantity'),
                    'price_unit': line.get('price_unit'),
                }
                sale_order_vals['order_line'].append((0, 0, line_vals))

            sale_order = request.env['sale.order'].sudo().create(sale_order_vals)
            
                        
            response, status = Sale().confirm_sale_order_logic(sale_order.sudo())
            if status != 200:
                return request.make_response(
                    json.dumps(response),
                    headers=[("Content-Type", "application/json")],
                    status=status
                )
            demand_data = json_data.get("demand", {})
            validate_response, validate_status = self._validate_delivered_products(sale_order.sudo(), demand_data)
            if validate_status != 200:
                return request.make_response(
                    json.dumps(validate_response),
                    headers=[("Content-Type", "application/json")],
                    status=validate_status
                )

            # Step 2: Create Invoice
            if sale_order.sudo().invoice_status == 'to invoice':
                context = dict(request.env.context)
                context.update({
                    'active_id': sale_order.id,
                    'active_ids': [sale_order.id],
                    'active_model': 'sale.order',
                    'open_invoices': True,
                })

                adv_payment_type = json_data.get('advance')
                advance_payment_inv = request.env['sale.advance.payment.inv'].with_context(context).sudo().create({
                    'id': adv_payment_type
                })

                result = advance_payment_inv.create_invoices()

                invoice = request.env['account.move'].sudo().browse(result['res_id'])
                if invoice:
                    invoice.sudo().with_context(from_api=True).action_post()

                    # Step 3: Confirm Invoice
                    return request.make_response(
                        json.dumps({
                            'status': 'success',
                            'data': {
                                'message': 'Sale order and invoice created successfully',
                                'sale_order_id': sale_order.id,
                                'invoice_id': invoice.id,
                                'invoice_number': invoice.name,
                                'amount_total': invoice.amount_total
                            }
                        }),
                        headers=[("Content-Type", "application/json")],
                        status=200
                    )
                else:
                    return request.make_response(
                        json.dumps({'status': 'fail', 'data': {'message': 'Invoice creation failed'}}),
                        headers=[('Content-Type', 'application/json')],
                        status=400
                    )
            else:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Sale order is not ready for invoicing'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )    

        except ValidationError as ve:
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': str(ve)}}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
        except Exception as e:
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': 'Internal server error', 'details': str(e)}}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )


    @http.route('/trading/api/confirm_sale_order/<int:order_id>', type='http',cors='*',auth='public', csrf=False, methods=['POST'])
    def confirm_sale_order(self, order_id, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Sale order with id {order_id} not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            if order.state not in ['draft', 'sent']:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Sale order is in {order.state} state and cannot be confirmed'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            order.sudo().with_context(from_api=True).action_confirm()

            return request.make_response(
                json.dumps({'status': 'success', 'data': {'message': f'Sale order {order_id} confirmed successfully', 'sale_order_id': order.id, 'state': order.state}}),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': 'Internal server error', 'details': str(e)}}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
        
    @http.route('/trading/api/validate_delivered_products/<int:order_id>', type='http',cors='*',auth='public', csrf=False, methods=['POST'])
    def validate_delivered_products(self, order_id, **kw):
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

            order = request.env['sale.order'].browse(order_id)
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

    @http.route('/trading/api/create_so_invoice/<int:order_id>', type='http',cors='*',auth='public', csrf=False, methods=['POST'])
    def create_invoice(self, order_id, **kw):
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

            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Order not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            if order.invoice_status != 'to invoice':
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'This order is not ready to be invoiced'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            context = dict(request.env.context)
            context.update({
                'active_id': order.id,
                'active_ids': [order.id],
                'active_model': 'sale.order',
                'open_invoices': True,
            })

            adv_payment_type = json_data.get('advance')
            advance_payment_inv = request.env['sale.advance.payment.inv'].with_context(context).create({
                'id': adv_payment_type
            })

            result = advance_payment_inv.create_invoices()

            invoice = request.env['account.move'].browse(result['res_id'])

            return request.make_response(
                json.dumps({'status': 'success', 'data': {'invoice_id': invoice.id, 'invoice_number': invoice.name, 'amount_total': invoice.amount_total}}),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except UserError as e:
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': str(e)}}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
        except Exception as e:
            return request.make_response(
                json.dumps({'status': 'fail', 'data': {'message': 'Internal server error', 'details': str(e)}}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/trading/api/confirm_so_invoice/<int:order_id>', type='http',cors='*',auth='public', csrf=False, methods=['POST'])
    def confirm_so_invoice(self, order_id, **kw):
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
                            'message': 'Order ID is required',
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Order not found',
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
                invoice.sudo().with_context(from_api=True).action_post()
                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': {
                            'message': 'Invoice Confirmed',
                        }
                    }),
                    headers=[("Content-Type", "application/json")],
                    status=200
                )
            else:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': 'Could Not Confirm Invoice',
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
                        'message': f'Error {str(e)}',
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/trading/api/pay_so_invoice/<int:order_id>', type='http',cors='*',auth='public', csrf=False, methods=['POST'])
    def pay_so_invoice(self, order_id, **kw):
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

            order = request.env['sale.order'].browse(order_id)
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
            _logger.exception("Failed to pay invoice")
            return request.make_response(
                json.dumps({
                    'status': 'fail',
                    'data': {
                        'message': f'Error {str(e)}',
                    }
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/trading/api/delete_sale_order/<int:order_id>', type='http',cors='*',auth='public', csrf=False, methods=['POST'])
    def delete_sale_order(self, order_id, **kw):
        try:
            # Authenticate Request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            # Validate Sale Order ID
            if not order_id:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Sale order ID is required'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Search for the Sale Order
            sale_order = request.env['sale.order'].sudo().search([('id', '=', order_id)], limit=1)
            if not sale_order:
                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': f'Sale order {order_id} not found'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Handle related deliveries (pickings)
            stock_pickings = sale_order.picking_ids
            validated_pickings = stock_pickings.filtered(lambda p: p.state == 'done')
            non_validated_pickings = stock_pickings.filtered(lambda p: p.state != 'done')

            # If any picking is validated, do not delete the SO
            if validated_pickings:
                # Cancel and set invoices to draft if paid
                invoices = sale_order.invoice_ids
                for invoice in invoices:
                    if invoice.state in ['posted', 'paid']:
                        if invoice.state == 'paid':
                            # Reset invoice to draft
                            invoice.sudo().button_draft()
                        invoice.sudo().button_cancel()

                return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Cannot delete sale order because some deliveries are validated.'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # If no deliveries are validated, delete non-validated deliveries
            for picking in non_validated_pickings:
                picking.sudo().action_cancel()  # Cancel picking before deletion
                picking.sudo().unlink()  # Delete the picking

            # Delete or archive related invoices if not already handled
            invoices = sale_order.invoice_ids
            for invoice in invoices:
                if invoice.state != 'cancel':
                    invoice.sudo().button_cancel()  # Cancel invoice before deletion
                invoice.sudo().unlink()

            # Cancel the Sale Order before deletion
            if sale_order.state not in ['draft', 'cancel']:
                sale_order.sudo().action_cancel()  # Cancel the sale order first

            # Finally, delete the sale order
            sale_order.sudo().unlink()

            # Return success response
            return request.make_response(
                json.dumps({'status': 'success', 'data': {'message': 'Sale order deleted successfully'}}),
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

    @http.route('/trading/api/get_sale_order_report/<int:order_id>', type='http', cors="*", auth="public", csrf=False, methods=['GET'])
    def get_sale_order_report(self, order_id, **kw):
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
                            'message': 'Sale order ID is required'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Check if sale order exists
            sale_order = request.env['sale.order'].sudo().browse(order_id)
            if not sale_order.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data': {
                            'message': f'Sale order with ID {order_id} not found'
                        }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            # Generate the report URL
            base_url = "http://lekhaplus.com"
            report_url = f"{base_url}/report/public/pdf/sale.report_saleorder/{order_id}"
            
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
            _logger.exception(f"Error in get_sale_order_report: {str(e)}")
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