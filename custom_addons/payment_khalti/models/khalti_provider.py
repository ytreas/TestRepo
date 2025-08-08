from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from datetime import datetime
import requests
import pprint
import logging

_logger = logging.getLogger(__name__)


class KhaltiProvider(models.Model):
    _inherit = 'payment.provider'
    _api_endpoint = '/epayment/initiate/'
    _lookup_endpoint = '/epayment/lookup/'

    domain_name = fields.Char(_("Server Domain"),default="http://localhost:8069/")
    port=fields.Char(_("Port Number"),default="8069")
    
    code = fields.Selection(
        selection_add=[('khalti', "khalti")], ondelete={'khalti': 'set default'}
    )
    khalti_auth_key=fields.Char(string='Khalti Authorization Key', required_id_provider="khalti", groups='base.group_system')

    def _get_supported_payment_methods(self, processing_values=None):
        if self.code != 'khalti':
            return super()._get_supported_payment_methods(processing_values)

        return [{
            'code': 'khalti',
            'name': 'Khalti Wallet',
        }]
        
    def _khalti_get_api_url(self):
        """ Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://a.khalti.com/api/v2'
        else:
            return 'https://a.khalti.com/api/v2'
        
    def _make_khalti_request(self, payload, mode="initiate"):
        self.ensure_one()
        
        if mode == "initiate":
            url = f"{self._khalti_get_api_url()}{self._api_endpoint}"
        elif mode == "lookup":
            url = f"{self._khalti_get_api_url()}{self._lookup_endpoint}"
        else:
            print(f"[Khalti] Unknown mode: {mode}")
            raise ValidationError(f"Khalti: Unknown mode '{mode}'")
        
        headers = {
            "Authorization": f"Key {self.khalti_auth_key}",
            "Content-Type": "application/json"
        }

        print(f"[Khalti] Request URL: {url}")
        print(f"[Khalti] Payload: {payload}")
        print(f"[Khalti] Headers: {headers}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()

                
