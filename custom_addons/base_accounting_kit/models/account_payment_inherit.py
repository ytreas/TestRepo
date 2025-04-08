from odoo import fields, models, api, _

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    voucher_id = fields.Char(string='Voucher ID')
