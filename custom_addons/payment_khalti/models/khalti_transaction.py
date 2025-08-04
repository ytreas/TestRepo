from odoo.exceptions import ValidationError
from odoo import api, fields, models
from datetime import datetime
from odoo.http import request
import logging
import json  # Required to convert dict to JSON string if needed

_logger = logging.getLogger(__name__)


class KhaltiTransaction(models.Model):
    _inherit = 'payment.transaction'   
    pidx=fields.Char('pidx')

    @api.model_create_multi
    def create(self, values_list):
        tsx = super().create(values_list)
        print(tsx,tsx.provider_id,tsx.provider_id.code)

        if tsx.provider_code == 'khalti':
            tsx.state='pending'

        return tsx
    
    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'khalti':
            return res

        # Get current logged-in user (frontend user)
        user = request.env.user
        partner = user.partner_id

        # Fetch the sale order by reference
        order = request.env['sale.order'].sudo().search([('name', '=', self.reference)], limit=1)
        if not order:
            raise ValidationError(f"No order found for reference: {self.reference}")

        # Build product details
        product_details = []
        base_amount = 0
        for line in order.order_line:
            quantity = int(line.product_uom_qty)
            line_total = int(line.price_total * 100)
            base_amount += line_total
            unit_price = line_total // quantity if quantity > 0 else 0
            
            if unit_price * quantity != line_total:
                unit_price = line_total
                
            if line.price_unit >= 1:
                product_details.append({
                    "identity": str(line.product_id.id),  # Convert to string
                    "name": line.product_id.name,
                    "total_price": line_total,
                    "quantity": int(line.product_uom_qty),
                    "unit_price": unit_price,
                })

        # You can calculate actual shipping fee if applicable
        shipping_fee = 1  # Update this if you have a delivery line or custom fee

        # Add shipping fee as product line if non-zero
        if shipping_fee >= 1:
            product_details.append({
                "identity": 999999,
                "name": "Shipping Fee",
                "total_price": shipping_fee,
                "quantity": 1,
                "unit_price": shipping_fee
            })

        # Total amount for payment gateway (already in paisa)
        total_amount = base_amount + shipping_fee

        # Construct return URL
        return_url = f'{self.provider_id.domain_name}:{self.provider_id.port}/khalti/verify'

        # Final Khalti-compatible payload
        payload = {
            "return_url": return_url,
            "website_url": return_url,
            "amount": total_amount,
            "purchase_order_id": self.reference,
            "purchase_order_name": f"Ref:{self.reference}",
            "customer_info": {
                "name": partner.name,
                "email": partner.email,
                "phone": "9843098510",
            },
            "amount_breakdown": [
                {"label": "Product Price", "amount": base_amount},
                {"label": "Shipping Fee", "amount": shipping_fee}
            ],
            "product_details": product_details,
            "merchant_username": "biseshkoirala123456@gmail.com",
            "merchant_extra": self.reference  # Must be string
        }

        # Make request to Khalti
        response = self.provider_id._make_khalti_request(payload)
        print("Response of khalti: ", response)

        payment_url = response['payment_url']
        pidx = response['pidx']
        self.pidx = pidx

        return {
            'payment_url': payment_url,
            'pidx': pidx
        }
    
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Adyen data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        return tx
    
    def action_khalti_set_done(self):
        """ Set the state of the khalti transaction to 'done'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'khalti':
            return

        self._set_done()

    def action_khalti_set_pending(self):
        """ Set the state of the khalti transaction to 'done'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'khalti':
            return

        self._set_pending()

    def action_khalti_set_auth(self):
        """ Set the state of the khalti transaction to 'done'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'khalti':
            return

        self._set_authorized()


    def action_khalti_set_canceled(self):
        """ Set the state of the khalti transaction to 'cancel'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'khalti':
            return

        self._set_canceled()

    def action_khalti_set_error(self):
        """ Set the state of the khalti transaction to 'cancel'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'khalti':
            return

        self._set_error("Error Has Occured Registering This Payment")
        
        
        
        
    
