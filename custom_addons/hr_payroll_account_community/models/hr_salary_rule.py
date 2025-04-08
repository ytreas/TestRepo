
from odoo import fields, models


class HrSalaryRule(models.Model):
    """Extends the standard 'hr.salary.rule' model to include additional
    fields for defining salary rules."""
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          help="Analytic account associated "
                                               "with the record")
    account_tax_id = fields.Many2one('account.tax', string='Tax',
                                     help="Tax account associated with the "
                                          "record")
    account_debit_id = fields.Many2one('account.account',
                                       string='Debit Account',
                                       help="Debit account associated with the"
                                            " record",
                                       domain=[('deprecated', '=', False)])
    account_credit_id = fields.Many2one('account.account',
                                        string='Credit Account',
                                        help="Credit account associated with"
                                             " the record",
                                        domain=[('deprecated', '=', False)])
