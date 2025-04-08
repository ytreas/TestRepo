from odoo import models, fields, api

class ResCompany(models.Model):
    """
    Inherited for adding configuration for inter company transfers.
    @author: Maulik Barad.
    """
    _inherit = "res.company"

    sale_journal_id = fields.Many2one('account.journal', check_company=True,
                                      help="Sale Journal for creating invoice on.")
    purchase_journal_id = fields.Many2one('account.journal', check_company=True,
                                          help="Purchase Journal for creating vendor bill on.")
    farmerid = fields.Char(string="Farmer ID")