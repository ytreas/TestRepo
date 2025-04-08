
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class HrPayslipLine(models.Model):
    """Create new model for adding Payslip Line"""
    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'contract_id, sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip',
                              required=True,
                              ondelete='cascade',
                              help="Choose Payslip for line")
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Pay Head Type',
                                     required=True,
                                     help="Choose Salary Rule for line")
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  required=True,
                                  help="Choose Employee for line")
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  required=True, index=True,
                                  help="Choose Contract for line")
    rate = fields.Float(string='Rate (%)', help="Set Rate for payslip",
                        digits=dp.get_precision('Payroll Rate'), default=100.0)
    amount = fields.Float(digits=dp.get_precision('Payroll'), string="Amount",
                          help="Set Amount for line")
    quantity = fields.Float(digits=dp.get_precision('Payroll'), default=1.0,
                            string="Quantity", help="Set Qty for line")
    total = fields.Float(compute='_compute_total', string='Total',
                         help="Total amount for Payslip",
                         digits=dp.get_precision('Payroll'), store=True)

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        """Function for compute total amount"""
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        """Function for change value at the time of creation"""
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['hr.payslip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get(
                    'employee_id') or payslip.employee_id.id
                values['contract_id'] = (values.get(
                    'contract_id') or payslip.contract_id and
                                         payslip.contract_id.id)
                if not values['contract_id']:
                    raise UserError(
                        _('You must set a contract to create a payslip line.'))
        return super(HrPayslipLine, self).create(vals_list)


class EmployeeTaxConfig(models.Model):
    _name = "employee.tax.config"
    _description = "Employee Tax Configuration"

    fiscal_years = fields.Many2one('account.fiscal.year', string="Fiscal Year")
    marital_status = fields.Selection(
        selection=[
            ('single', 'Single'),
            ('married', 'Married')
        ],
        string='Marital Status',
        required=True,  
    )
    annual_salary_ids = fields.One2many('annual.salary.model', 'employee_tax_id', string='Annual Salary')
    # payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    
class AnnualSalaryModel(models.Model):
    _name = "annual.salary.model"
    _description = "Annual Salary Model"

    annual_salary_from = fields.Integer(string="Annual Salary From")
    annual_salary_to = fields.Integer(string="Annual Salary To")
    tax_idsss = fields.Many2one('account.tax', string="Tax")
    employee_tax_id = fields.Many2one('employee.tax.config', string="Employee Tax Config")



class Employeetax(models.Model):
    _name="employee.tax.config"
    _description="Employee config"

    fiscal_years = fields.Many2one('account.fiscal.year', string="Fiscal Year")
    marital_status = fields.Selection(
        selection=[
            ('single', 'Single'),
            ('married', 'Married')
        ],
        string='Marital Status',
        required=True,  
    )
    annual_salary_ids = fields.One2many('annual.salary.model', 'employee_tax_id', string= 'Annual Salary')

    
class Annualsalary(models.Model):
    _name="annual.salary.model"
    _description = "Annual Salary Model"

    annual_salary_from = fields.Integer(string="Annual Salary from")
    annual_salary_to = fields.Integer(string="Annual Salary To")
    tax_idsss = fields.Many2one('account.tax', string="Tax")
    employee_tax_id = fields.Many2one('employee.tax.config',"Employee Tax Config")


