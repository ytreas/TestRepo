from odoo import fields, models


class HrPayslipWorkedDays(models.Model):
    """Create new model for adding some fields"""
    _name = 'hr.payslip.worked.days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', 
                       help="Description for Worked Days")
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip',
                                 
                                 ondelete='cascade', index=True,
                                 help="Choose Payslip for worked days")
    sequence = fields.Integer( index=True, default=10,
                              string="Sequence",
                              help="Sequence for worked days")
    code = fields.Char(required=True, string="Code",
                       help="The code that can be used in the salary rules")
    number_of_days = fields.Float(string='Number of Days',
                                  help="Number of days worked")
    number_of_hours = fields.Float(string='Number of Hours',
                                   help="Number of hours worked")
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  help="The contract for which applied"
                                       "this input")
