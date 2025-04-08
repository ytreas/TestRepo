from odoo import http
from odoo.http import request, Response
import json
import logging
from datetime import datetime
import jwt
from . import jwt_token_auth

_logger = logging.getLogger(__name__)

class InvoiceController(http.Controller):
    @http.route("/api/get_invoice_details", type="http", auth='public', cors="*", methods=["GET"], csrf=False)
    def get_invoice_details(self, **kw):
        try:
            
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers={'Content-Type': 'application/json'},
                    status=status_code
                )
                
            # Fetch parameters from the request
            invoice_id = kw.get('invoice_id')
            start_date = kw.get('start_date')
            end_date = kw.get('end_date')

            # Log received parameters for debugging
            _logger.info(f"Received parameters: invoice_id={invoice_id}, start_date={start_date}, end_date={end_date}")

            # Prepare domain for search (default domain: fetch all outgoing invoices)
            domain = [('move_type', '=', 'out_invoice')]

            # Add invoice ID to domain if provided
            if invoice_id:
                domain.append(('id', '=', int(invoice_id)))

            # Validate and add start date filtering if provided
            if start_date:
                if not self.is_valid_date(start_date):
                    return Response(
                        status=400,
                        response=json.dumps({"status": "fail", "message": "Invalid start date format. Use YYYY-MM-DD."}),
                        content_type='application/json'
                    )
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                domain.append(('invoice_date', '>=', start_date_obj))
                
            # Validate and add end date filtering if provided
            if end_date:
                if not self.is_valid_date(end_date):
                    return Response(
                        status=400,
                        response=json.dumps({"status": "fail", "message": "Invalid end date format. Use YYYY-MM-DD."}),
                        content_type='application/json'
                    )
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                domain.append(('invoice_date', '<=', end_date_obj))

            # Search for the invoices based on the domain
            invoices = request.env['account.move'].sudo().search(domain)

            if not invoices:
                return Response(
                    status=404,
                    response=json.dumps({"status": "fail", "message": "No invoices found matching the criteria"}),
                    content_type='application/json'
                )

            # Prepare the list of invoice data
            invoice_list = []
            for invoice in invoices:
                invoice_data = {
                    "code": invoice.name,
                    "partner_id": invoice.partner_id.name,
                    "invoice_date": invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else None,
                    "due_date": invoice.invoice_date_due.strftime('%Y-%m-%d') if invoice.invoice_date_due else None,
                    "delivery_date": invoice.delivery_date.strftime('%Y-%m-%d') if invoice.delivery_date else None,
                    "total_amount": invoice.amount_residual,
                    "untaxed_amount": invoice.amount_untaxed_signed,
                    "tax_amount": invoice.amount_tax_signed,
                    "lines": []
                }

                # Fetch corresponding invoice lines
                for line in invoice.invoice_line_ids:
                    line_data = {
                        "product_id": line.product_id.name,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "tax_ids": [tax.name for tax in line.tax_ids],
                        "price_subtotal": line.price_subtotal,
                    }
                    invoice_data["lines"].append(line_data)
                
                invoice_list.append(invoice_data)

            return Response(
                status=200,
                response=json.dumps({"status": "success", "data": invoice_list}),
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return Response(
                status=500,
                response=json.dumps({"status": "fail", "message": str(e)}),
                content_type='application/json'
            )

    def is_valid_date(self, date_str):
        """ Check if the date string is in the format YYYY-MM-DD. """
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
