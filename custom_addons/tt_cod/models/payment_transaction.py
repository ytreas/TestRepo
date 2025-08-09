from odoo import api, fields, models
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class CODTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model_create_multi
    def create(self, values_list):
        transactions = super().create(values_list)

        for tx in transactions:
            print(f"Creating COD Transaction: {tx.reference}")
            if tx.provider_code == 'custom':
                print(f"COD Transaction created: {tx.reference}")
                tx.state = 'pending'  # COD is pending until delivery

                # Send COD confirmation email
                self._send_cod_email(tx)

        return transactions

    def _send_cod_email(self, tx):
        """Send confirmation email for COD orders."""
        order = self.env['sale.order'].sudo().search([('name', '=', tx.reference)], limit=1)
        if not order:
            _logger.warning(f"No order found for COD transaction {tx.reference}")
            return

        partner = order.partner_id
        email = partner.email or ""
        if not email:
            _logger.warning(f"No email found for partner {partner.name}")
            return

        mail_values = {
            'subject': f'Cash on Delivery Confirmation - {order.name}',
            'body_html': f"""
                <p>Hello {partner.name},</p>
                <p>Your order <strong>{order.name}</strong> has been confirmed with Cash on Delivery.</p>
                <p>You will need to pay <strong>{tx.amount} {tx.currency_id.symbol}</strong> when the products are delivered to your address.</p>
                <p>Please keep the exact amount ready for our delivery personnel.</p>
                <p>Thank you for shopping with us!</p>
                <p>Best regards,<br/>{self.env['ir.config_parameter'].sudo().get_param('website.name') or 'Our Store'} Team</p>
            """,
            'email_from': 'info.flowgenic@gmail.com',
            'email_to': email,
        }
        request.env['mail.mail'].sudo().create(mail_values).send()
        _logger.info(f"COD confirmation email sent to {email} for order {order.name}")
