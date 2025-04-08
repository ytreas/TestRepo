from odoo import models, fields, api
from odoo.exceptions import ValidationError

class InsuranceDetails(models.Model):
    _name = 'insurance.details'
    _description = 'Insurance Details'
    
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    insurance_company_id = fields.Many2one('insurance.company', string='Insurance Company')
    insurance_policy_number = fields.Char(string='Insurance Policy Number')
    insurance_policy_start_date = fields.Date(string=' Policy Start Date')
    insurance_policy_start_date_bs = fields.Char(string=' Policy Start Date (Nepali)')
    insurance_policy_end_date = fields.Date(string=' Policy End Date ')
    insurance_policy_end_date_bs = fields.Char(string=' Policy End Date (Nepali)')
    insurance_policy_status = fields.Selection(
            selection=[
                ('active', 'Active'),
                ('inactive', 'Inactive')
            ],
            string='Status', 
        )
    insurance_policy_description = fields.Text(string='Description')
    
    @api.constrains('insurance_policy_start_date', 'insurance_policy_end_date')
    def _check_insurance_policy_date(self):
        for record in self:
            if record.insurance_policy_start_date > record.insurance_policy_end_date:
                raise ValidationError('Insurance Policy Start Date should be less than Insurance Policy End Date')