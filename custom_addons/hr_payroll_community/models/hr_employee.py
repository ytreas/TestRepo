from odoo import fields, models, api
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    """Inherit hr_employee for getting Payslip Counts"""

    _inherit = "hr.employee"
    _description = "Employee"

    slip_ids = fields.One2many(
        "hr.payslip",
        "employee_id",
        string="Payslips",
        readonly=True,
        help="Choose Payslip for Employee",
    )
    payslip_count = fields.Integer(
        compute="_compute_payslip_count",
        string="Payslip Count",
        help="Set Payslip Count",
    )
    #our custom fields
    employee_post = fields.Many2one(
        "employee.post",
        string="Job Position",
        store=True,
    )
    position_name = fields.Many2one(
        "employee.post.designation",
        string="Position/Category Level",
        store=True,
    )

    used_yearly_service = fields.Boolean(string="Used Yearly Service", default=False)

    def _compute_payslip_count(self):
        """Function for count Payslips"""
        payslip_data = (
            self.env["hr.payslip"]
            .sudo()
            .read_group(
                [("employee_id", "in", self.ids)], ["employee_id"], ["employee_id"]
            )
        )
        result = dict(
            (data["employee_id"][0], data["employee_id_count"]) for data in payslip_data
        )
        for employee in self:
            employee.payslip_count = result.get(employee.id, 0)

    @api.model
    def calculate_dynamic_tax(self, contract):

        current_year = datetime.now().year

        fiscal_year = self.env["account.fiscal.year"].search(
            [("date_from", "<=", datetime.now()), ("date_to", ">=", datetime.now())],
            limit=1,
        )
        marital_status = self.marital
        _logger.info(f"Fiscal Year: {fiscal_year.id}")

        _logger.info(f"Current Year: {marital_status}")
        tax_config = self.env["employee.tax.config"].search(
            [
                ("fiscal_years", "=", fiscal_year.id),
                ("marital_status", "=", marital_status),
            ],
            limit=1,
        )

        _logger.info(f"Tax Config: {tax_config.marital_status}")

        salary = contract.wage
        tax_amount = 0
        if tax_config:
            for bracket in tax_config.annual_salary_ids:
                if bracket.annual_salary_from <= salary <= bracket.annual_salary_to:
                    tax_amount = salary * (bracket.tax_idsss.amount / 100)
                    break

        _logger.info(f"Final Tax Amount: {tax_amount}")

        return -tax_amount

    @api.model
    def calculate_overtime_amount(self, contract):
        worked_hr = self.slip_ids.worked_days_line_ids
        overtime_hr = self.slip_ids.overtime_hr

        _logger.info(f"Tax Config:{overtime_hr}")
        total_hours = 0

        for value in worked_hr:
            total_hours += value.number_of_hours

        per_hr_rate = (contract.wage) / (total_hours)

        overtime_minutes = overtime_hr * 60

        overtime_amount = (per_hr_rate * 1.5) * (overtime_minutes / 60)

        _logger.info(f"Tax Config: {overtime_minutes}")

        return overtime_hr

    @api.model
    def calculate_unpaid_amount(self, contract):
        # test = 9089

        worked_hr = self.slip_ids.worked_days_line_ids

        total_hours = 0
        unpaid_hr = 0

        for value in worked_hr:
            total_hours += value.number_of_hours
            if value.name == "Unpaid":
                unpaid_hr = value.number_of_hours

        per_hr_rate = (contract.wage) / (total_hours)

        unpaid_amount = per_hr_rate * unpaid_hr

        _logger.info(f"Unpaid Amount +++++++++++ Config: {unpaid_amount}")

        return -unpaid_amount

    @api.model
    def _get_total_months(self, start_date_bs_str, end_date_bs_str):
        start_date_bs = datetime.strptime(start_date_bs_str, "%Y/%m/%d").date()
        end_date_bs = datetime.strptime(end_date_bs_str, "%Y/%m/%d").date()

        total_months = (end_date_bs.year - start_date_bs.year) * 12 + (
            end_date_bs.month - start_date_bs.month
        )

        return total_months

    @api.model
    def compute_total_salary(self, contract, payslip):
        start_date_bs_str = payslip.date_from_bs
        end_date_bs_str = payslip.date_to_bs

        total_months = self._get_total_months(start_date_bs_str, end_date_bs_str)

        # Optional handle partial months by checking the days
        # total_days_in_period = (end_date_bs - start_date_bs).days + 1  # Adding 1 to include both start and end days

        monthly_wage = contract.wage
        gross_salary = monthly_wage * total_months

        return gross_salary

    @api.model
    def compute_total_allowance(self, contract, allowance, payslip):

        start_date_bs_str = payslip.date_from_bs
        end_date_bs_str = payslip.date_to_bs
        total_months = self._get_total_months(start_date_bs_str, end_date_bs_str)

        allowance_total = allowance * total_months

        return allowance_total

    @api.model
    def create(self, vals):
        # Create the employee record
        employee = super(HrEmployee, self).create(vals)

        # Create a record in the insurance.details model
        self.env["insurance.details"].create(
            {
                "employee_id": employee.id,
                "insurance_company_id": vals.get("insurance_company_id"),
                "insurance_policy_number": vals.get("insurance_policy_number"),
            }
        )

        return employee

    def write(self, vals):
        res = super(HrEmployee, self).write(vals)

        # Update the corresponding record in the insurance.details model
        for employee in self:
            insurance_details = self.env["insurance.details"].search(
                [("employee_id", "=", employee.id)], limit=1
            )
            if insurance_details:
                insurance_details.write(
                    {
                        "insurance_company_id": vals.get(
                            "insurance_company_id",
                            insurance_details.insurance_company_id.id,
                        ),
                        "insurance_policy_number": vals.get(
                            "insurance_policy_number",
                            insurance_details.insurance_policy_number,
                        ),
                    }
                )

        return res
