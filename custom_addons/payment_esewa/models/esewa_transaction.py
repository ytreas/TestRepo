from odoo.exceptions import ValidationError
from odoo import api, fields, models
from datetime import datetime
from odoo.http import request
import logging
import json  # Required to convert dict to JSON string if needed
import uuid
import hmac
import hashlib
import base64

_logger = logging.getLogger(__name__)

PRODUCT_CODE = "EPAYTEST"
SECRET_KEY = "8gBm/:&EnhH.1/q"
class EsewaTransaction(models.Model):
    _inherit = 'payment.transaction'   
    pidx=fields.Char('pidx')
    @api.model_create_multi
    def create(self, values_list):
        tsx = super().create(values_list)
        print(tsx,tsx.provider_id,tsx.provider_id.code)

        if tsx.provider_code == 'esewa':
            tsx.state='pending'

        return tsx
    
    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'esewa':
            return res

        # Get current logged-in user (frontend user)
        user = request.env.user
        partner = user.partner_id

        # Fetch the sale order by reference
        order = request.env['sale.order'].sudo().search([('name', '=', self.reference)], limit=1)
        if not order:
            raise ValidationError(f"No order found for reference: {self.reference}")

        # Calculate base amount
        base_amount = sum(int(line.price_total) for line in order.order_line)

        # Optional: Shipping Fee
        shipping_fee = 1
        total_amount = base_amount + shipping_fee

        # Generate transaction UUID
        transaction_uuid = str(uuid.uuid4())
        self.pidx = transaction_uuid
        print("Transaction UUID:", transaction_uuid)
        # self.acquirer_reference = transaction_uuid  # Optional: store for verification tracking

        # Build raw string for signature
        # raw_string = f"{total_amount},{self.reference},{transaction_uuid}"
        data_to_sign = f"total_amount={total_amount+3},transaction_uuid={transaction_uuid},product_code={PRODUCT_CODE}"
        print("Data to sign:", data_to_sign)
        # Generate signature (implement _generate_esewa_signature in provider model)
        digest = hmac.new(
                    SECRET_KEY.encode("utf-8"),
                    msg=data_to_sign.encode("utf-8"),
                    digestmod=hashlib.sha256
                ).digest()
        signature = base64.b64encode(digest).decode("utf-8")
        print("Signature:", signature)

        # eSewa-compatible payload for HTML form
        payload = {
            "amount": total_amount,
            "tax_amount": 1,
            "total_amount": total_amount+1+1+1,
            "product_code": "EPAYTEST",
            "product_service_charge": 1,
            "product_delivery_charge": 1,
            "success_url": f"{self.provider_id.domain_name}:{self.provider_id.port}/esewa/verify",
            "failure_url": f"{self.provider_id.domain_name}:{self.provider_id.port}/esewa/verify",
            "signed_field_names": "total_amount,transaction_uuid,product_code",
            "transaction_uuid": transaction_uuid,
            "signature": signature,
        }
        print("Payload:", payload)

        return {
            'payment_form_action': "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
            'payload': payload,
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

    def action_esewa_set_done(self):
        """ Set the state of the esewa transaction to 'done'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'esewa':
            return

        self._set_done()

    def action_esewa_set_pending(self):
        """ Set the state of the esewa transaction to 'pending'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'esewa':
            return

        self._set_pending()

    def action_esewa_set_auth(self):
        """ Set the state of the esewa transaction to 'done'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'esewa':
            return

        self._set_authorized()


    def action_esewa_set_canceled(self):
        """ Set the state of the esewa transaction to 'cancel'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'esewa':
            return

        self._set_canceled()

    def action_esewa_set_error(self):
        """ Set the state of the esewa transaction to 'cancel'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'esewa':
            return

        self._set_error("Error Has Occured Registering This Payment")
        
        
        
        
    
