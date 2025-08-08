# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class CustomController(Controller):
    _process_url = '/payment/cod/process'

    @route(_process_url, type='http', auth='public', methods=['POST'], csrf=False)
    def custom_process_transaction(self, **post):
        print("Handling COD processing with data:", post)

        reference = post.get('reference')
        if not reference:
            print("Missing order reference in post data:", post)
            return request.redirect('/shop/payment/validate')

        transaction_orm = request.env['payment.transaction'].sudo()
        transaction = transaction_orm.search([('reference', '=', reference)], limit=1)

        if not transaction:
            print(f"No transaction found with reference {reference}")
            return request.redirect('/shop/payment/validate')

        order = request.env['sale.order'].sudo().search([('name', '=', reference)], limit=1)
        if not order:
            print(f"No sale order found for reference {reference}")
            return request.redirect('/shop/payment/validate')

        website = request.env['website'].sudo().get_current_website()
        order.write({'website_id': website.id})

        if order.state in ['draft', 'sent']:
            print(f"Confirming order {order.name}")
            order.action_confirm()

        # Try finding a cash journal, fallback to bank if not found
        journal = request.env['account.journal'].sudo().search([('type', '=', 'cash')], limit=1)
        if not journal:
            print("No cash journal found, trying bank journal")
            journal = request.env['account.journal'].sudo().search([('type', '=', 'bank')], limit=1)
            if not journal:
                print("No suitable journal found")
                return request.redirect('/shop/payment/validate')

        payment_method = journal.inbound_payment_method_line_ids[:1]
        if not payment_method:
            print("No payment method found on the journal!")
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

        transaction._set_done()
        transaction.provider_reference = f"COD-{transaction.reference}"
        print(f"COD transaction processed for order {order.name} — payment in draft.")

        return request.redirect('/shop/payment/validate')
