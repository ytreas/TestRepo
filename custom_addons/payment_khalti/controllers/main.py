import logging
import pprint
import json
import requests
from odoo import http
from odoo.http import request

import ast
_logger = logging.getLogger(__name__)

class KhaltiController(http.Controller):
    _redirect_url_2 = '/khalti/verify'
    @http.route(
        _redirect_url_2, type='http', auth='public', methods=['GET'], csrf=False, save_session=False
    )
    def verify_khalti_payment(self, **data):

        pidx = request.params.get('pidx')
        if not pidx:
            return request.redirect('/shop/payment/validate')

        transaction_orm = request.env['payment.transaction'].sudo()
        transaction = transaction_orm.search([('pidx', '=', pidx)], limit=1)

        if not transaction:
            return request.redirect('/shop/payment/validate')

        payload = {"pidx": pidx}
        try:
            response = transaction.provider_id._make_khalti_request(payload, mode="lookup")

        except Exception:
            return request.redirect('/shop/payment/validate')

        status = response.get('status')
        ref_id = response.get('transaction_id') or response.get('ref_id')
        order = request.env['sale.order'].sudo().search([
            ('name', '=', transaction.reference)
        ], limit=1)

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
                _logger.warning("No payment method found on the journal!")
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
            transaction.payment_id = payment.id

        partner = transaction.partner_id
        email = partner.email or ""
        if email:
            if status == 'Completed':
                # Mark as done
                transaction._set_done()
                transaction.provider_reference = ref_id
                _logger.info(f"Payment marked DONE for transaction {transaction.reference}")
                payment.action_post()

                # Send confirmation email
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

            elif status in ['Pending', 'Refunded', 'Expired', 'Cancelled', 'Failed']:
                transaction._set_canceled()

                # Send cancellation email
                mail_values = {
                    'subject': f'Payment Issue - {order.name}',
                    'body_html': f"""
                        <p>Hello {partner.name},</p>
                        <p>We noticed that your payment for order <strong>{order.name}</strong> was not successful (Status: {status}).</p>
                        <p>Our team will contact you shortly to resolve this issue.</p>
                        <p>If you believe this is an error, please get in touch with us.</p>
                        <p>Best regards,<br/>{request.env['ir.config_parameter'].sudo().get_param('website.name') or 'Our Store'} Team</p>
                    """,
                    'email_from': 'info.flowgenic@gmail.com',
                    'email_to': email,
                }
                request.env['mail.mail'].sudo().create(mail_values).send()
                return request.redirect('/shop/payment/validate')

        else:
            _logger.warning(f"No email found for partner {partner.name}")

        _logger.warning(f"Unrecognized payment status from Khalti: {status}")
        return request.redirect('/shop/payment/validate')
