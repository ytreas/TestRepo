
from odoo import fields, models


class HrContract(models.Model):
    """Extends the standard 'hr.contract' model to include additional fields
        for employee contracts."""
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          help="Select Analytic account")
    journal_id = fields.Many2one('account.journal',
                                 string='Salary Journal',
                                 help="Journal associated with the record")
