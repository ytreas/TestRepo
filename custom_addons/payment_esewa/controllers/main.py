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

        encoded_data = post.get('data')
        if not encoded_data:
            _logger.warning("No 'data' field in POST request")
            return request.redirect('/shop/payment/validate')

        try:
            decoded_bytes = base64.b64decode(encoded_data)
            decoded_str = decoded_bytes.decode('utf-8')
            esewa_data = json.loads(decoded_str)
            _logger.info(f"Decoded eSewa data: {esewa_data}")
        except Exception as e:
            _logger.error(f"Failed to decode eSewa data: {e}")
            return request.redirect('/shop/payment/validate')

        product_code = esewa_data.get('product_code')
        transaction_uuid = esewa_data.get('transaction_uuid')
        total_amount = esewa_data.get('total_amount')
        status = esewa_data.get('status')
        ref_id = esewa_data.get('transaction_code')

        transaction = request.env['payment.transaction'].sudo().search([
            ('pidx', '=', transaction_uuid)
        ], limit=1)

        partner = transaction.partner_id
        email = partner.email or ""

        if status == 'COMPLETE':
            transaction._set_done()
            transaction.provider_reference = ref_id
            _logger.info(f"Payment completed. Transaction: {transaction.reference}, Ref ID: {ref_id}")

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

                # Send confirmation email
                if email:
                    mail_values = {
                        'subject': f'Order Confirmation - {order.name}',
                        'body_html': f"""
                            <p>Hello {partner.name},</p>
                            <p>We have successfully received your payment for order <strong>{order.name}</strong>.</p>
                            <p>Your order has been confirmed and will be delivered within the next few days.</p>
                            <p>Thank you for shopping with us!</p>
                            <p>Best regards,<br/>{request.env['ir.config_parameter'].sudo().get_param('website.name') or 'Our Store'} Team</p>
                        """,
                        'email_from': 'info.flowgenic@gmail.com',
                        'email_to': email,
                    }
                    request.env['mail.mail'].sudo().create(mail_values).send()

            return request.redirect('/shop/payment/validate')

        elif status in ['CANCELLED', 'FAILED']:
            _logger.info(f"Payment cancelled or failed. Status: {status}")
            transaction._set_canceled()

            # Send failure email
            if email:
                mail_values = {
                    'subject': f'Payment Issue - {transaction.reference}',
                    'body_html': f"""
                        <p>Hello {partner.name},</p>
                        <p>Your payment for order <strong>{transaction.reference}</strong> was not successful (Status: {status}).</p>
                        <p>Our team will contact you shortly to assist you.</p>
                        <p>If you believe this is an error, please reach out to us.</p>
                        <p>Best regards,<br/>{request.env['ir.config_parameter'].sudo().get_param('website.name') or 'Our Store'} Team</p>
                    """,
                    'email_from': 'info.flowgenic@gmail.com',
                    'email_to': email,
                }
                request.env['mail.mail'].sudo().create(mail_values).send()

            return request.redirect('/shop/payment/validate')

        elif status == 'PENDING':
            _logger.info(f"Payment still pending. Status: {status}")
            transaction._set_pending()
            return request.redirect('/shop/payment/validate')

        else:
            _logger.warning(f"Unrecognized payment status from eSewa: {status}")
            return request.redirect('/shop/payment/validate')
