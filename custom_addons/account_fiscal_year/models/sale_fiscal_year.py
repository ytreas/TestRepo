from odoo import api, fields, models


class SaleFiscalYear(models.Model):

    _inherit = "sale.order"
    _description = "Fiscal Year For Purchase"

    fiscal_year =  fields.Many2one('account.fiscal.year', string='Fiscal Year', default=lambda self: self._compute_fiscal_year())

    @api.depends("date_order")
    def _compute_fiscal_year(self):
        current_date = self.date_order
        fiscal_year = self.env['account.fiscal.year'].search([('date_from', '<=', current_date), ('date_to', '>=', current_date)], limit=1)
        if fiscal_year:
            return fiscal_year.id
        else:
            return False