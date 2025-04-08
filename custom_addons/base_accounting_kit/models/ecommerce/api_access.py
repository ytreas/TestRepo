from odoo import fields, _, models
import secrets


class APIAccess(models.Model):
    _name = "ecommerce.api.access.token"

    name = fields.Char("Token name", required=True)
    token = fields.Char(string="Access Token", unique=True)
    active = fields.Boolean(string="Active", default=True)
    expiry_date = fields.Datetime(string="Expiry Date")

    def generate_token(self):
        new_token = secrets.token_urlsafe(32)
        self.token = new_token
