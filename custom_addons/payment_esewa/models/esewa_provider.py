from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from datetime import datetime
import requests
import pprint
import logging

_logger = logging.getLogger(__name__)
SECRET_KEY = "8gBm/:&EnhH.1/q"
PRODUCT_CODE = "EPAYTEST"

class EsewaProvider(models.Model):
    _inherit = 'payment.provider'
    _api_endpoint = '/epayment/initiate/'
    _lookup_endpoint = '/epayment/lookup/'

    domain_name = fields.Char(_("Server Domain"),default="http://localhost:8069/")
    port=fields.Char(_("Port Number"),default="8069")
    
    code = fields.Selection(
        selection_add=[('esewa', "Esewa")], ondelete={'esewa': 'set default'}
    )
    esewa_auth_key=fields.Char(string='Esewa Authorization Key', required_id_provider="esewa", groups='base.group_system')
    def _generate_esewa_signature(self, raw_string):
        import hmac
        import hashlib
        secret_key = SECRET_KEY
        return hmac.new(secret_key.encode(), raw_string.encode(), hashlib.sha256).hexdigest()
    
    def _get_supported_payment_methods(self, processing_values=None):
        if self.code != 'esewa':
            return super()._get_supported_payment_methods(processing_values)

        return [{
            'code': 'esewa',
            'name': 'Esewa Wallet',
        }]

    def _esewa_get_api_url(self):
        """ Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'
        else:
            return 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'

    def _make_esewa_request(self, payload, mode="initiate"):
        self.ensure_one()
        
        if mode == "initiate":
            url = f"{self._esewa_get_api_url()}{self._api_endpoint}"
        elif mode == "lookup":
            url = f"{self._esewa_get_api_url()}{self._lookup_endpoint}"
        else:
            print(f"[Esewa] Unknown mode: {mode}")
            raise ValidationError(f"Esewa: Unknown mode '{mode}'")

        headers = {
            "Authorization": f"Key {self.esewa_auth_key}",
            "Content-Type": "application/json"
        }

        print(f"[Esewa] Request URL: {url}")
        print(f"[Esewa] Payload: {payload}")
        print(f"[Esewa] Headers: {headers}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()

                
