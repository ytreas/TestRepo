import logging
import pprint
import json
import requests
from odoo import http,fields
import base64
from odoo.http import request

import ast
_logger = logging.getLogger(__name__)

class EsewaController(http.Controller):
    _redirect_url_2 = '/esewa/verify'
    
    @http.route('/esewa/verify', type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def verify_esewa_payment(self, **post):
        _logger.info("Entered eSewa verification route")
        _logger.info(f"eSewa POST data: {post}")

        # Step 1: Get the encoded data from post
        encoded_data = post.get('data')
        if not encoded_data:
            _logger.warning("No 'data' field in POST request")
            return request.redirect('/shop/payment/validate')

        try:
            # Step 2: Decode the base64 data
            decoded_bytes = base64.b64decode(encoded_data)
            decoded_str = decoded_bytes.decode('utf-8')
            esewa_data = json.loads(decoded_str)
            _logger.info(f"Decoded eSewa data: {esewa_data}")
        except Exception as e:
            _logger.error(f"Failed to decode eSewa data: {e}")
            return request.redirect('/shop/payment/validate')

        # Step 3: Extract fields
        product_code = esewa_data.get('product_code')
        transaction_uuid = esewa_data.get('transaction_uuid')
        total_amount = esewa_data.get('total_amount')
        status = esewa_data.get('status')
        ref_id = esewa_data.get('transaction_code')  # Assuming transaction_code is the reference ID

        # if not (product_code and transaction_uuid and total_amount and status):
        #     _logger.warning("Missing required decoded data from eSewa")
        #     return request.redirect('/shop/cart')

        # Step 4: Search for matching transaction
        transaction = request.env['payment.transaction'].sudo().search([
            ('pidx', '=', transaction_uuid)
        ], limit=1)

        # Step 5: Process result
        if status == 'COMPLETE':
            transaction._set_done()
            transaction.provider_reference = ref_id
            _logger.info(f"Payment completed. Transaction: {transaction.reference}, Ref ID: {ref_id}")

            # Process the order...
            order = request.env['sale.order'].sudo().search([('name', '=', transaction.reference)], limit=1)
            if order:
                website = request.env['website'].sudo().get_current_website()
                order.write({'website_id': website.id})

                if order.state in ['draft', 'sent']:
                    order.action_confirm()

                journal = request.env['account.journal'].sudo().search([('type', '=', 'bank')], limit=1)
                if not journal:
                    _logger.error("No journal found to register payment!")
                    return request.redirect('/shop/payment/validate')

                payment_method = journal.inbound_payment_method_line_ids[:1]
                if not payment_method:
                    return request.redirect('/shop/payment/validate')

                payment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': transaction.partner_id.id,
                    'amount': transaction.amount,
                    'currency_id': transaction.currency_id.id,
                    'journal_id': journal.id,
                    'payment_method_line_id': payment_method.id,
                    'payment_transaction_id': transaction.id,
                }
                payment = request.env['account.payment'].sudo().create(payment_vals)
                payment.action_post()
                transaction.payment_id = payment.id

                return request.redirect('/shop/payment/validate')
            else:
                return request.redirect('/shop/payment/validate')

        elif status in ['CANCELLED', 'FAILED']:
            _logger.info(f"Payment cancelled or failed. Status: {status}")
            transaction._set_cancel()
            return request.redirect('/shop/payment/validate')

        elif status == 'PENDING':
            _logger.info(f"Payment still pending. Status: {status}")
            transaction._set_pending()
            return request.redirect('/shop/payment/validate')
        else:
            _logger.warning(f"Unrecognized payment status from eSewa: {status}")
            return request.redirect('/shop/payment/validate')

            