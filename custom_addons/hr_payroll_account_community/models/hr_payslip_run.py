
from odoo import fields, models


class HrPayslipRun(models.Model):
    """Extends the standard 'hr.payslip.run' model to include additional fields
    for managing payroll runs.
    Methods:
        compute_total_amount: Compute the total amount of the payroll run."""
    _inherit = 'hr.payslip.run'

    journal_id = fields.Many2one(comodel_name='account.journal',
                                 string='Salary Journal',
                                 required=True, help="Journal associated with "
                                                     "the record",
                                 default=lambda self: self.env[
                                     'account.journal'].search(
                                     [('type', '=', 'general')],
                                     limit=1))
