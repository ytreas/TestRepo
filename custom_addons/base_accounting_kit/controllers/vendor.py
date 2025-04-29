from odoo.http import Response, request
from odoo import fields, http,api,SUPERUSER_ID
from odoo.osv import expression
import jwt
import base64
from . import jwt_token_auth
import datetime
import logging
import json
from odoo.exceptions import ValidationError
from collections import defaultdict

_logger = logging.getLogger(__name__)

class Vendor(http.Controller):
    
    @http.route('/trading/api/get_vendor_list', type='http',auth='public',cors="*", methods=['GET'], csrf=False)
    def get_vendor_list(self,**kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            domain = []
            domain.append(('ref_company_ids', '!=', False))
                
            vendors = request.env['res.partner'].sudo().search(domain)

            vendor_details = []
            for vendor in vendors:
                vendor_purchase_domain=[]
                vendor_total_purchase = 0
                vendor_purchase_domain.append(('partner_id.id', '=', vendor.id))
                vendor_purchase_orders = request.env['purchase.order'].sudo().search(vendor_purchase_domain)
                for vendor_purchase_order in vendor_purchase_orders:
                    vendor_total_purchase = sum([line.price_subtotal for line in vendor_purchase_order.order_line])+vendor_total_purchase
                vendor_details.append({

                    'id': vendor.id,
                    'name': vendor.complete_name,
                    'name_np': vendor.name_np if vendor.name_np else None,             
                    'email': vendor.email if vendor.email else None,
                    'pan_no': vendor.pan_no if vendor.pan_no else None,
                    'mobile': vendor.mobile if vendor.mobile else None,
                    'total_purchase': vendor_total_purchase,
                    'company_id': vendor.ref_company_ids[0].id if vendor.ref_company_ids else None,
                    
                })
            return request.make_response(
                json.dumps({"status": "success", "data": vendor_details}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return http.Response(
                status=400,
                response=json.dumps({
                    "status":"fail",
                    "data":{ 
                        "message": str(e)
                    }}),
                content_type='application/json'
            )
        
    # @http.route('/trading/api/get_vendor_price', type='http',auth='public',cors="*", methods=['GET'], csrf=False)
    # def get_vendor_price(self,**kwargs):
    #     partner_id = request.httprequest.args.get('vendor_id')
    #     product_id = request.httprequest.args.get('product_id')
    #     vendor = request.env['res.partner'].sudo().search([('id', '=', int(partner_id))], limit=1)
    #     print("vendor",vendor)
    #     company_id = vendor.ref_company_ids[0].id
    #     domain = [('product_id.id', '=', int(product_id)),('company_id.id', '=', company_id)]
    #     print("domain",domain)
    #     custom_price = request.env['product.custom.price'].sudo().search(domain, limit=1)
    #     print("custom_price",custom_price)
    #     if custom_price:
    #         return request.make_response(
    #             json.dumps({"price_sell": custom_price.price_sell, "saleable_qty": custom_price.saleable_qty}),
    #             headers=[("Content-Type", "application/json")]
    #         )
    #     else:
    #         return request.make_response(
    #             json.dumps({"price_sell": None, "saleable_qty": None}),
    #             headers=[("Content-Type", "application/json")]
    #         )
            

    @http.route('/trading/api/create_vendor', type='http',auth='public',methods=['POST'], csrf=False)
    def create_vendors(self, **kw):
     
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
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "Unauthorized access"
                        }}),
                    content_type='application/json'
                )
            
            company_id = kw.get('company_id')
            image_1920 = kw.get('image_1920')
            if not image_1920:
                image_1920_binary =  None
            else:
                image_1920_binary =  base64.b64encode(image_1920.read())

            company = request.env['res.company'].search([('id', '=', int(company_id))], limit=1)
            if not company:
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message":"Company not found"
                        }}),
                    content_type='application/json'
                )
            

            max_rank = request.env['res.partner'].sudo().search([('supplier_rank', '>', 0)], order='supplier_rank desc', limit=1).supplier_rank or 0
            supplier_rank = max_rank + 1

            vendor_details= {
                'company_id' : company_id,
                'name' : kw.get('vendor_name'),
                'name_np' : kw.get('vendor_name_np'),
                'city' : kw.get('address'),
                'zip' : kw.get('zip'),
                'phone' : kw.get('phone'),
                'vat' : kw.get('vat'),
                'email' : kw.get('email'),
                'mobile' : kw.get('mobile'),
                # 'province': kw.get('province'),
                # 'district' : kw.get('district'),
                # 'palika': kw.get('palika'),
                # 'ward_no': kw.get('ward_no'),
                'pan_no': kw.get('pan_no'),
                'mobile': kw.get('mobile'),
                'supplier_rank': supplier_rank,
                'image_1920': image_1920_binary 
                # 'tole': kw.get('ward_no')
            }
            vendor = request.env['res.partner'].sudo().create(vendor_details)
            _logger.error(f"datata: {vendor_details}")
            return request.make_response(
                json.dumps({"status": "success", "data": {
                    "message": f"Vendor {vendor.name} created successfully",
                    "vendor_id":vendor.id
                }}),
                headers=[("Content-Type", "application/json")]
            )
            
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
    
    @http.route("/trading/api/edit_vendor", type="http", methods=["POST"], csrf=False)
    def edit_vendor(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            vendor_id = kw.get('vendor_id')
            print("vendor_id",vendor_id)
            if not vendor_id:
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'vendor ID is required'}),
                    headers=[("Content-Type", "application/json")],
                    status=400
                )

            vendor = request.env['res.partner'].sudo().search([('id', '=', int(vendor_id))], limit=1)
            if not vendor:
                return request.make_response(
                    json.dumps({"status": "fail", "message": "vendor not found"}),
                    headers=[("Content-Type", "application/json")],
                    status=404
                )

            print("vendor.name",vendor.name)
            # Prepare the fields to update
            update_fields = {}

            if 'vendor_name' in kw:
                if kw.get('vendor_name') is not "":
                    update_fields['name'] = kw.get('vendor_name')
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
            if 'province' in kw:
                if kw.get('province') is not "":
                    update_fields['province'] = kw.get('province')
            if 'district' in kw:
                if kw.get('district') is not "":
                    update_fields['district'] = kw.get('district')
            if 'palika' in kw:
                if kw.get('palika') is not "":
                    update_fields['palika'] = kw.get('palika')
            if 'ward_no' in kw:
                if kw.get('ward_no') is not "":
                    update_fields['ward_no'] = kw.get('ward_no')
            if 'image_1920' in kw:
                if kw.get('image_1920') is not "":
                    image_1920 = kw.get('image_1920')
                    image_1920_binary =  base64.b64encode(image_1920.read())
                    # _logger.info("images",image_1920_binary)
                    update_fields['image_1920'] = image_1920_binary

            # Log the update fields for debugging
            # _logger.info(f"Updating Vendor with ID {vendor_id} with fields: {update_fields}")

            if not update_fields:
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'No valid fields to update'}),
                    headers=[("Content-Type", "application/json")],
                    status=400
                )
    
            vendor.sudo().write(update_fields)
            _logger.info(f"Vendor with ID {vendor_id} updated successfully.")

            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': f'Vendor {vendor_id} details updated successfully'
                    }
                }),
                headers=[("Content-Type", "application/json")],
                status=200
            )

        except Exception as e:
            _logger.error(f"Error while updating Vendor: {str(e)}")
            return request.make_response(
                json.dumps({"status": "fail", "message": str(e)}),
                headers=[("Content-Type", "application/json")],
                status=400
            )
    
    @http.route("/trading/api/delete_vendor", type="http", methods=["DELETE"], csrf=False)
    def delete_vendor(self, **kw):
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
            vendor_id = json_data.get('vendor_id')
            vendor = request.env['res.partner'].sudo().search([('id', '=', vendor_id)], limit=1)
            if not vendor:
                return http.Response(
                    status=404,
                    response=json.dumps({"status": "fail", "message": "Vendor not found"}),
                    content_type="application/json"
                )
            
            vendor.sudo().unlink()
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'message': 'Vendor deleted successfully'
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
                status=400
            )

    @http.route('/trading/api/company_payables_receivables_report', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_company_payables_receivables_report(self, **kwargs):
        """
        API endpoint to get total payables and receivables for the company,
        counts of partners, and totals per partner, with individual unpaid
        documents embedded within each partner's summary.
        Excludes company filter if company_id is 1.
        """
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            company_id = auth_status.get('company_id')
            if not company_id:
                 return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Company ID not found in token'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            AccountMove = request.env['account.move'].sudo()

            base_domain = [
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ]
            if company_id != 1:
                base_domain.append(('company_id', '=', company_id))

            payable_domain = expression.AND([base_domain, [('move_type', '=', 'in_invoice')]])
            unpaid_bills = AccountMove.search(payable_domain)

            total_payable = 0.0
            payables_per_vendor = defaultdict(lambda: {
                'vendor_name': '',
                'total_payable': 0.0,
                'bill_count': 0,
                'payable_bills': []
            })

            for bill in unpaid_bills:
                if not bill.partner_id.ref_company_ids:
                    continue
                payable_amount = abs(bill.amount_residual_signed)
                total_payable += payable_amount
                vendor_id = bill.partner_id.id
                vendor_name = bill.partner_id.display_name

                bill_detail = {
                    'bill_id': bill.id,
                    'bill_number': bill.name,
                    'bill_date': fields.Date.to_string(bill.invoice_date),
                    'due_date': fields.Date.to_string(bill.invoice_date_due),
                    'amount_due': payable_amount,
                    'total_amount': bill.amount_total_signed
                }

                payables_per_vendor[vendor_id]['vendor_name'] = vendor_name
                payables_per_vendor[vendor_id]['total_payable'] += payable_amount
                payables_per_vendor[vendor_id]['bill_count'] += 1
                payables_per_vendor[vendor_id]['payable_bills'].append(bill_detail)

            payables_summary_list = [
                {
                    'vendor_id': vid,
                    'vendor_name': vdata['vendor_name'],
                    'total_payable': vdata['total_payable'],
                    'total_payable_bill_count': vdata['bill_count'],
                    'payable_bills': sorted(vdata['payable_bills'], key=lambda x: x['due_date'] or '9999-12-31') # Embed sorted list
                 }
                for vid, vdata in payables_per_vendor.items()
            ]
            payable_vendor_count = len(payables_per_vendor)

            receivable_domain = expression.AND([base_domain, [('move_type', '=', 'out_invoice')]])
            unpaid_invoices = AccountMove.search(receivable_domain)

            total_receivable = 0.0
            receivables_per_customer = defaultdict(lambda: {
                'customer_name': '',
                'total_receivable': 0.0,
                'invoice_count': 0,
                'receivable_invoices': []
            })

            for invoice in unpaid_invoices:
                if not invoice.partner_id.ref_company_ids:
                    continue
                receivable_amount = invoice.amount_residual_signed
                total_receivable += receivable_amount
                customer_id = invoice.partner_id.id
                customer_name = invoice.partner_id.display_name

                invoice_detail = {
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.name,
                    'invoice_date': fields.Date.to_string(invoice.invoice_date),
                    'due_date': fields.Date.to_string(invoice.invoice_date_due),
                    'amount_due': receivable_amount,
                    'total_amount': invoice.amount_total_signed
                }

                receivables_per_customer[customer_id]['customer_name'] = customer_name
                receivables_per_customer[customer_id]['total_receivable'] += receivable_amount
                receivables_per_customer[customer_id]['invoice_count'] += 1
                receivables_per_customer[customer_id]['receivable_invoices'].append(invoice_detail)

            receivables_summary_list = [
                {
                    'customer_id': cid,
                    'customer_name': cdata['customer_name'],
                    'total_receivable': cdata['total_receivable'],
                    'total_receivable_invoice_count': cdata['invoice_count'],
                    'receivable_invoices': sorted(cdata['receivable_invoices'], key=lambda x: x['due_date'] or '9999-12-31') # Embed sorted list
                }
                for cid, cdata in receivables_per_customer.items()
            ]
            receivable_customer_count = len(receivables_per_customer)

            response_data = {
                'status': 'success',
                'data': {
                    'company_id': company_id,
                    'total_payable': total_payable,
                    'total_receivable': total_receivable,
                    'payable_vendor_count': payable_vendor_count,
                    'receivable_customer_count': receivable_customer_count,
                    'payables_by_vendor': sorted(payables_summary_list, key=lambda x: x['total_payable'], reverse=True),
                    'receivables_by_customer': sorted(receivables_summary_list, key=lambda x: x['total_receivable'], reverse=True),
                }
            }

            return request.make_response(
                json.dumps(response_data, default=str),
                headers=[("Content-Type", "application/json")],
                status=200
            )

        except Exception as e:
            _logger.error(f"Error fetching detailed payables/receivables report: {str(e)}")
            return request.make_response(
                json.dumps({"status": "fail", "data": {"message": f"An error occurred: {str(e)}"}}),
                headers=[("Content-Type", "application/json")],
                status=500
            )

            
    @http.route('/trading/api/company_payables_receivables_detailed', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_company_payables_receivables_detailed(self, **kwargs):
        """
        API endpoint to get total payables and receivables for the company,
        counts of partners, totals per partner (including document counts),
        and lists of individual unpaid documents.
        Excludes company filter if company_id is 1.
        """
        try:
            # Step 1: Authenticate the request and get company_id
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )

            company_id = auth_status.get('company_id')
            if not company_id:
                 return request.make_response(
                    json.dumps({'status': 'fail', 'data': {'message': 'Company ID not found in token'}}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            AccountMove = request.env['account.move'].sudo()

            # Common domain filters for unpaid/partially paid posted moves
            base_domain = [
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ]
            if company_id != 1:
                base_domain.append(('company_id', '=', company_id))

            # Step 2: Calculate Payables from Vendor Bills
            payable_domain = expression.AND([base_domain, [('move_type', '=', 'in_invoice')]])
            unpaid_bills = AccountMove.search(payable_domain)

            total_payable = 0.0
            vendor_bills_details = []
            # Initialize defaultdict to include count
            payables_per_vendor = defaultdict(lambda: {'vendor_name': '', 'total_payable': 0.0, 'bill_count': 0})

            for bill in unpaid_bills:
                if not bill.partner_id.ref_company_ids:
                    continue
                payable_amount = abs(bill.amount_residual_signed)
                total_payable += payable_amount
                vendor_id = bill.partner_id.id
                vendor_name = bill.partner_id.display_name

                vendor_bills_details.append({
                    'bill_id': bill.id,
                    'bill_number': bill.name,
                    'vendor_id': vendor_id,
                    'vendor_name': vendor_name,
                    'bill_date': fields.Date.to_string(bill.invoice_date),
                    'due_date': fields.Date.to_string(bill.invoice_date_due),
                    'amount_due': payable_amount,
                    'total_amount': bill.amount_total_signed
                })

                # Aggregate total and count per vendor
                payables_per_vendor[vendor_id]['vendor_name'] = vendor_name
                payables_per_vendor[vendor_id]['total_payable'] += payable_amount
                payables_per_vendor[vendor_id]['bill_count'] += 1 # Increment bill count

            # Convert defaultdict to list, including the count
            payables_summary_list = [
                {
                    'vendor_id': vid,
                    'vendor_name': vdata['vendor_name'],
                    'total_payable': vdata['total_payable'],
                    'total_payable_bill_count': vdata['bill_count'] # Added count field
                 }
                for vid, vdata in payables_per_vendor.items()
            ]
            payable_vendor_count = len(payables_per_vendor)

            # Step 3: Calculate Receivables from Customer Invoices
            receivable_domain = expression.AND([base_domain, [('move_type', '=', 'out_invoice')]])
            unpaid_invoices = AccountMove.search(receivable_domain)

            total_receivable = 0.0
            customer_invoices_details = []
            # Initialize defaultdict to include count
            receivables_per_customer = defaultdict(lambda: {'customer_name': '', 'total_receivable': 0.0, 'invoice_count': 0})

            for invoice in unpaid_invoices:
                if not invoice.partner_id.ref_company_ids:
                    continue
                receivable_amount = invoice.amount_residual_signed
                total_receivable += receivable_amount
                customer_id = invoice.partner_id.id
                customer_name = invoice.partner_id.display_name

                customer_invoices_details.append({
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.name,
                    'customer_id': customer_id,
                    'customer_name': customer_name,
                    'invoice_date': fields.Date.to_string(invoice.invoice_date),
                    'due_date': fields.Date.to_string(invoice.invoice_date_due),
                    'amount_due': receivable_amount,
                    'total_amount': invoice.amount_total_signed
                })

                # Aggregate total and count per customer
                receivables_per_customer[customer_id]['customer_name'] = customer_name
                receivables_per_customer[customer_id]['total_receivable'] += receivable_amount
                receivables_per_customer[customer_id]['invoice_count'] += 1 # Increment invoice count

            # Convert defaultdict to list, including the count
            receivables_summary_list = [
                {
                    'customer_id': cid,
                    'customer_name': cdata['customer_name'],
                    'total_receivable': cdata['total_receivable'],
                    'total_receivable_invoice_count': cdata['invoice_count'] # Added count field
                }
                for cid, cdata in receivables_per_customer.items()
            ]
            receivable_customer_count = len(receivables_per_customer)

            # Step 4: Prepare the response
            response_data = {
                'status': 'success',
                'data': {
                    'company_id': company_id,
                    'total_payable': total_payable,
                    'total_receivable': total_receivable,
                    'payable_vendor_count': payable_vendor_count,
                    'receivable_customer_count': receivable_customer_count,
                    # Updated summary lists with counts
                    'payables_by_vendor': sorted(payables_summary_list, key=lambda x: x['total_payable'], reverse=True),
                    'receivables_by_customer': sorted(receivables_summary_list, key=lambda x: x['total_receivable'], reverse=True),
                    'unpaid_vendor_bills': sorted(vendor_bills_details, key=lambda x: x['due_date'] or '9999-12-31'),
                    'unpaid_customer_invoices': sorted(customer_invoices_details, key=lambda x: x['due_date'] or '9999-12-31')
                }
            }

            return request.make_response(
                json.dumps(response_data, default=str),
                headers=[("Content-Type", "application/json")],
                status=200
            )

        except Exception as e:
            _logger.error(f"Error fetching detailed payables/receivables: {str(e)}")
            return request.make_response(
                json.dumps({"status": "fail", "data": {"message": f"An error occurred: {str(e)}"}}),
                headers=[("Content-Type", "application/json")],
                status=500
            )
