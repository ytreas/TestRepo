from datetime import date, datetime, time
import babel
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from num2words import num2words
from . import utilities


# This will generate 16th of days
ROUNDING_FACTOR = 16
import logging

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    """Create new model for getting total Payroll Sheet for an Employee"""

    _name = "hr.payslip"
    _inherit = "mail.thread"
    _description = "Pay Slip"

    def _amount_to_words(self, amount):
        return utilities.Utilities().amount_to_words_np(amount)

    struct_id = fields.Many2one(
        comodel_name="hr.payroll.structure",
        string="Structure",
    )
    name = fields.Char(string="Payslip Name", help="Enter Payslip Name")
    number = fields.Char(
        string="Reference",
        copy=False,
        help="References for Payslip",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        help="Choose Employee for Payslip",
    )
    date_from = fields.Date(
        string="Date From",
        required=True,
        help="Start date for Payslip",
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)),
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        help="End date for Payslip",
        default=lambda self: fields.Date.to_string(
            (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        ),
    )
    date_from_bs = fields.Char("Date From (Nepali)", store=True)
    date_to_bs = fields.Char("Date To (Nepali)", store=True)

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("verify", "Waiting"),
            ("done", "Done"),
            ("cancel", "Rejected"),
        ],
        string="Status",
        index=True,
        readonly=True,
        copy=False,
        default="draft",
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, 
                the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""",
    )
    line_ids = fields.One2many(
        "hr.payslip.line",
        "slip_id",
        string="Payslip Lines",
        help="Choose Payslip for line",
    )
    # tax_ids = fields.One2many('employee.tax.config',
    #                           'payslip_id',
    #                           string='Employee Tax Configuration',
    #                           help="Choose Employee Tax Configuration")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        copy=False,
        help="Choose Company for line",
        default=lambda self: self.env["res.company"]._company_default_get(),
    )
    worked_days_line_ids = fields.One2many(
        "hr.payslip.worked.days",
        "payslip_id",
        string="Payslip Worked Days",
        copy=True,
        help="Payslip worked days for line",
    )
    input_line_ids = fields.One2many(
        "hr.payslip.input",
        "payslip_id",
        string="Payslip Inputs",
        help="Choose Payslip Input",
    )
    paid = fields.Boolean(
        string="Made Payment Order ? ", copy=False, help="Is Payment Order"
    )
    note = fields.Text(string="Internal Note", help="Description for Payslip")
    contract_id = fields.Many2one(
        "hr.contract", string="Contract", help="Choose Contract for Payslip"
    )
    details_by_salary_rule_category_ids = fields.One2many(
        comodel_name="hr.payslip.line",
        compute="_compute_details_by_salary_rule_category_ids",
        string="Details by Salary Rule Category",
        help="Details from the salary" " rule category",
    )
    credit_note = fields.Boolean(
        string="Credit Note", help="Indicates this payslip has " "a refund of another"
    )
    payslip_run_id = fields.Many2one(
        "hr.payslip.run",
        string="Payslip Batches",
        copy=False,
        help="Choose Payslip Run",
    )
    payslip_count = fields.Integer(
        compute="_compute_payslip_count",
        string="Payslip Computation Details",
        help="Set Payslip Count",
    )
    overtime_hr = fields.Float(string="Overtime(/hr)")

    annual_salary = fields.Float(
        string="Annual Salary", compute="compute_annual_salary", store=True
    )
    # income_tax = fields.Float(string='Income Tax')
    # ss_tax = fields.Float(string='Social Security Tax', _compute = 'compute_ss_tax')
    #ss_tax = fields.Float(string='Social Security Tax')
    batches_id = fields.Many2one('calculate.salary.batches', string='Batches',store=True, readonly=True)
    
    starting_salary= fields.Float(string='Base Salary')
    grade_amount= fields.Float(string='Grade Amount')
    grade_quantity= fields.Float(string='Number of Grade')
    total= fields.Float(string='Salary Total')
    # citizen_investment_fund= fields.Float(string='Citizen Investment Fund')
    income_tax= fields.Float(string='Income Tax')
    dearness_allowance = fields.Float(string='Dearness Allowance')
    qa_allowance = fields.Float(string='Q.A Allowance')
    social_security_tax = fields.Float(string='Social Security Tax')
    allowance = fields.Float(string='Allowance')
    special_allowance = fields.Float(string='Special Allowance')
    loan = fields.Float(string='Loan')
    lunch_allowance = fields.Float(string='Lunch Allowance')
    dress_allowance = fields.Float(string='Dress Allowance')
    submission= fields.Float(string='Submission')
    local_allowance = fields.Float(string='Local Allowance')
    other_allowance = fields.Float(string='Other Allowance')
    absent_days = fields.Float(string='Absent Days')
    absent_deduction= fields.Float(string='Absent Deduction')

    pf_add = fields.Float(string="PF Add")
    extraordinary_holiday = fields.Float(string="Extraordinary Holiday")
    extraordinary_holiday_deduction = fields.Float(
        string="Extraordinary Holiday Deduction"
    )
    interest_fund_deduction = fields.Float(string="Interest Fund Deduction")
    insurance_add = fields.Float(string="Insurance Add")
    technical_allowance = fields.Float(string="Technical Allowance")
    transport_allowance = fields.Float(string="Transport Allowance")
    food_allowance = fields.Float(string="Food Allowance")
    other_deduction = fields.Float(string="Other Deduction")
    cit_cut = fields.Float(string="CIT Deduction")
    pf_deduction = fields.Float(string="PF Deduction")
    medical_allowance = fields.Float(string="Medical Allowance")
    incentive_allowance = fields.Float(string="Incentive Allowance")
    communication_expense = fields.Float(string="Communication Expense")
    insurance_deduction = fields.Float(string="Insurance Deduction")
    total_total = fields.Float(string="Net Amount Received By Employee")
    welfare_fund_cut = fields.Float(string="Welfare Fund Cut")
    total_deduction = fields.Float(string="Total Deduction")
    woman_tax_discount = fields.Float(string="Womans 10% Tax Discount")
    salary_grade = fields.Float(string="Salary Grade")
    total_allowance = fields.Float(string="Total Allowance")

    batches_id = fields.Many2one(
        "calculate.salary.batches", string="Batches", store=True
    )
    letter_num = fields.Char(
        related="batches_id.letter_number",
        string="Letter Number",
        store=True,
        readonly="True",
    )
    use_yearly_service = fields.Boolean(string='Use Yearly Service', default=False)

    def get_report_value(self, batch_id=None, emp_id=None):

        if batch_id == None and emp_id == None:
            return None

        data = self.search(
            [("batches_id", "=", batch_id), ("employee_id", "=", emp_id)], limit=1
        )
        if not data:
            return None
        batches= data.batches_id.monthly_employee_detail_ids.sudo().search([('employee_name.id','=',emp_id),('batch_id','=',batch_id)],limit=1)
        return batches   
    
    @api.model
    def generate_payslips_from_contracts(self, batch_id, department):

        # Get the first and last day of the month three months ago
        today = date.today()
        start_date = (today.replace(day=1) - relativedelta(months=3)).replace(day=1)
        end_date = (today.replace(day=1) - relativedelta(months=2)) - relativedelta(
            days=1
        )

        # Find contracts eligible for payslip creation
        contracts = self.env["hr.contract"].search(
            [
                ("state", "=", "open"),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", start_date),
            ]
        )

        for contract in contracts:
            existing_payslip = self.env["hr.payslip"].search(
                [
                    ("batches_id", "=", batch_id),
                    ("contract_id", "=", contract.id),
                ],
                limit=1,
            )

            if existing_payslip:
                continue  # Skip if payslip already exists

            if department.id:
                if contract.employee_id.department_id.id == department.id:
                    # Create a new payslip
                    self.env["hr.payslip"].create(
                        {
                            "name": f'Salary Slip for {contract.employee_id.name} ({start_date.strftime("%d/%m/%Y")} to {end_date.strftime("%d/%m/%Y")})',
                            "employee_id": contract.employee_id.id,
                            "contract_id": contract.id,
                            "date_from_bs": start_date.strftime("%Y/%m/%d"),
                            "date_to_bs": end_date.strftime("%Y/%m/%d"),
                            "struct_id": contract.structure_type_id.id,
                            "company_id": contract.company_id.id,
                            "batches_id": batch_id.id,
                        }
                    )
                continue

            self.env["hr.payslip"].create(
                {
                    "name": f'Salary Slip for {contract.employee_id.name} ({start_date.strftime("%d/%m/%Y")} to {end_date.strftime("%d/%m/%Y")})',
                    "employee_id": contract.employee_id.id,
                    "contract_id": contract.id,
                    "date_from_bs": start_date.strftime("%Y/%m/%d"),
                    "date_to_bs": end_date.strftime("%Y/%m/%d"),
                    "struct_id": contract.structure_type_id.id,
                    "company_id": contract.company_id.id,
                    "batches_id": batch_id,
                }
            )

    @api.model
    def create(self, vals):
        # Create the payslip record
        payslip = super(HrPayslip, self).create(vals)

        # Get the contract linked to the employee
        contract = payslip.contract_id

        # Generate payslip lines based on allowances in the contract
        payslip_lines = []
        for allowance in contract.allowance_ids:
            payslip_lines.append(
                (
                    0,
                    0,
                    {
                        "salary_rule_id": allowance.allowance_id.id,
                        "category_id": allowance.allowance_id.category_id.id,
                        "amount": allowance.amount,
                        "contract_id": contract.id,
                    },
                )
            )

        # Assign payslip lines to the payslip
        payslip.line_ids = payslip_lines

        return payslip

    @api.depends("line_ids.total")
    def compute_annual_salary(self):
        for rec in self:
            total_annual_salary = 0.0
            # Loop through payslip lines and sum totals for 'Annual Salary'
            for line in rec.line_ids:
                if (
                    line.salary_rule_id.code == "ANN"
                ):  # Adjust this according to your rule code
                    total_annual_salary = line.total
            rec.annual_salary = total_annual_salary

    def amount_to_words(self, amount):
        return num2words(amount, lang="en").replace(",", "")

    def action_preview(self):
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": "/report/pdf/%s/%s"
            % ("hr_payroll_community.hr_payslip_new_report_action", self.id),
        }

    def action_test(self):

        overtime_amount = 888788
        worked_hr = self.worked_days_line_ids

        total_hours = 0
        unpaid_hr = 0
        for value in worked_hr:
            print(f" {value.name}:{value.number_of_hours}")
            total_hours += value.number_of_hours
            if value.name == "Unpaid":
                unpaid_hr = value.number_of_hours

        # per_hr_rate = (contract.wage) / (total_hours)
        print(f"Total Hour : {total_hours}")
        print(f" Unpaid Total Hour : {unpaid_hr}")
        # overtime_minutes = self.overtime_hr * 60

        # unpaid_amount = (per_hr_rate * unpaid_hr)
        return overtime_amount

    def action_preview(self):
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": "/report/pdf/%s/%s"
            % ("hr_payroll_community.hr_payslip_new_report_action", self.id),
        }

    def _compute_details_by_salary_rule_category_ids(self):
        """Compute function for Salary Rule Category for getting
        all Categories"""
        for payslip in self:
            payslip.details_by_salary_rule_category_ids = payslip.mapped(
                "line_ids"
            ).filtered(lambda line: line.category_id)

    def _compute_payslip_count(self):
        """Compute function for getting Total count of Payslips"""
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        """Function for adding constrains for payslip datas
        by considering date_from and date_to fields"""
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(_("Payslip 'Date From' must be earlier 'Date To'."))

    def action_payslip_draft(self):
        """Function for change stage of Payslip"""
        return self.write({"state": "draft"})

    def action_payslip_done(self):
        """Function for change stage of Payslip"""
        self.action_compute_sheet()
        return self.write({"state": "done"})

    def action_payslip_cancel(self):
        """Function for change stage of Payslip"""
        return self.write({"state": "cancel"})

    def action_refund_sheet(self):
        """Function for refund the Payslip sheet"""
        for payslip in self:
            copied_payslip = payslip.copy(
                {"credit_note": True, "name": _("Refund: ") + payslip.name}
            )
            copied_payslip.action_compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref("hr_payroll_community.hr_payslip_view_form", False)
        treeview_ref = self.env.ref("hr_payroll_community.hr_payslip_view_tree", False)
        return {
            "name": _("Refund Payslip"),
            "view_mode": "tree, form",
            "view_id": False,
            "res_model": "hr.payslip",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": "[('id', 'in', %s)]" % copied_payslip.ids,
            "views": [
                (treeview_ref and treeview_ref.id or False, "tree"),
                (formview_ref and formview_ref.id or False, "form"),
            ],
            "context": {},
        }

    def unlink(self):
        """Function for unlink the Payslip"""
        if any(self.filtered(lambda payslip: payslip.state not in ("draft", "cancel"))):
            raise UserError(
                _("You cannot delete a payslip which is not draft or cancelled!")
            )
        return super(HrPayslip, self).unlink()

    # TODO move this function into hr_contract module, on hr.employee object
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date_field
        @param date_to: date_field
        @return: returns the ids of all the contracts for the given employee
        that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ["&", ("date_end", "<=", date_to), ("date_end", ">=", date_from)]
        # OR if it starts between the given dates
        clause_2 = ["&", ("date_start", "<=", date_to), ("date_start", ">=", date_from)]
        # OR if it starts before the date_from and finish after the
        # date_end (or never finish)
        clause_3 = [
            "&",
            ("date_start", "<=", date_from),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", date_to),
        ]
        clause_final = (
            [("employee_id", "=", employee.id), ("state", "=", "open"), "|", "|"]
            + clause_1
            + clause_2
            + clause_3
        )
        return self.env["hr.contract"].search(clause_final).ids

    def action_compute_sheet(self):
        """Function for compute Payslip sheet"""
        for payslip in self:
            number = payslip.number or self.env["ir.sequence"].next_by_code(
                "salary.slip"
            )

            # Retrieve existing salary_rule_ids from current line_ids
            existing_rule_ids = payslip.line_ids.mapped("salary_rule_id.id")

            # Determine the list of contracts to apply the rules for
            contract_ids = payslip.contract_id.ids or self.get_contract(
                payslip.employee_id, payslip.date_from, payslip.date_to
            )

            # Get all new payslip lines
            all_lines = self._get_payslip_lines(contract_ids, payslip.id)

            # Filter out duplicates based on salary_rule_id
            new_lines = [
                line
                for line in all_lines
                if line.get("salary_rule_id") not in existing_rule_ids
            ]

            # Prepare new lines for creation
            lines = [(0, 0, line) for line in new_lines]

            # Update the payslip with new lines and sequence number
            payslip.write({"line_ids": lines, "number": number})
            yearly = payslip.batches_id.use_yearly_service

            if yearly:
                self.employee_id.used_yearly_service = True

            for line in payslip.line_ids:
                if line.salary_rule_id.code == "BASIC":
                    self.starting_salary = line.total
                elif line.salary_rule_id.code == "ALLOWANCE":
                    self.allowance = line.total
                elif line.salary_rule_id.code == "SA":
                    self.special_allowance = line.total
                elif line.salary_rule_id.code == "Grade":
                    self.grade_amount = line.total
                elif line.salary_rule_id.code == "Other":
                    self.other_allowance = line.total

                if line.salary_rule_id.type == "yearly" and yearly:
                    if line.salary_rule_id.code == "DA":
                        self.dearness_allowance = line.total
                    elif line.salary_rule_id.code == "Travel":
                        self.transport_allowance = line.total
                    elif line.salary_rule_id.code == "Meal":
                        self.food_allowance = line.total
                    elif line.salary_rule_id.code == "Medical":
                        self.medical_allowance = line.total
                elif line.salary_rule_id.type == "monthly":
                    if line.salary_rule_id.code == "DA":
                        self.dearness_allowance = line.total
                    elif line.salary_rule_id.code == "Travel":
                        self.transport_allowance = line.total
                    elif line.salary_rule_id.code == "Meal":
                        self.food_allowance = line.total
                    elif line.salary_rule_id.code == "Medical":
                        self.medical_allowance = line.total


            self.salary_grade = self.starting_salary + self.grade_amount
            self.total_allowance = (
                self.allowance
                + self.special_allowance
                + self.dearness_allowance
                + self.transport_allowance
                + self.food_allowance
                + self.local_allowance
                + self.other_allowance
                + self.lunch_allowance
                + self.dress_allowance
                + self.technical_allowance
                + self.qa_allowance
            )
            if self.contract_id.contract_type_id.name == "Permanent":
                self.pf_add = self.salary_grade * 0.1
                self.pf_deduction = self.pf_add * 2
            if (
                self.contract_id.insurance_service
                and self.contract_id.contract_type_id.name == "Permanent"
            ):
                self.insurance_add = self.contract_id.government_added_insurance_amount
                self.insurance_deduction = self.insurance_add * 2
            self.total = (
                self.salary_grade
                + self.total_allowance
                + self.pf_add
                + self.insurance_add
            )
            self.cit_cut = self.salary_grade * 0.13
            self.income_tax = self.compute_tax() / 12
            self.total_deduction = (
                self.pf_deduction
                + self.insurance_deduction
                + self.cit_cut
                + self.income_tax
            )
            self.total_total = self.total - self.total_deduction

        return True

    def compute_tax(self):
        basic_salary = self.starting_salary * 12
        grade = self.grade_amount * 12
        allowance = self.total_allowance * 12
        festive_allowance = self.starting_salary + self.grade_amount
        employer_pf_contribution = (basic_salary + grade) * 0.1
        insurance_contribution = self.insurance_add * 12
        gross_salary = (
            basic_salary
            + grade
            + allowance
            + festive_allowance
            + employer_pf_contribution
            + insurance_contribution
        )
        less_pf_contribution = employer_pf_contribution * 2
        less_cit = (basic_salary + grade) * 0.13
        less_life_insurance_premium = insurance_contribution * 2
        taxable_income = (
            gross_salary - less_pf_contribution - less_cit - less_life_insurance_premium
        )
        orginal_taxable_income = taxable_income
        domain = [
            ("marital_status", "=", self.contract_id.employee_id.marital),
            ("gender", "=", self.contract_id.employee_id.gender),
        ]

        employee_tax_config = self.env["employee.tax.config"].search(domain)
        income_tax = 0
        if employee_tax_config:
            tax_slabs = sorted(
                employee_tax_config.annual_salary_ids,
                key=lambda x: x.annual_salary_from,
            )
            for salary_line in tax_slabs:
                print(f"Taxable Income: {taxable_income}")
                print(
                    f"salary_line.annual_salary_from: {salary_line.annual_salary_from}"
                )
                if taxable_income > salary_line.annual_salary_from:
                    print(f"Taxable Income: {taxable_income}")
                    taxable_amount = min(
                        taxable_income, salary_line.annual_salary_to
                    ) - (salary_line.annual_salary_from - 1)
                    print(f"Taxable Amount: {taxable_amount}")
                    income_tax += taxable_income * (salary_line.tax_idsss.amount / 100)
                    print(
                        f"salary_line.tax_idsss.amount: {salary_line.tax_idsss.amount/100}"
                    )
                    print(f"Income Tax: {income_tax}")
                    taxable_income -= taxable_amount
                    print(f"Taxable Income: {taxable_income}")

        return income_tax

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contracts: Browse record of contracts, date_from, date_to
        @return: returns a list of dict containing the input that should be
        applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(
            lambda contract: contract.resource_calendar_id
        ):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)
            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id
            )
            multi_leaves = []
            for day, hours, leave in day_leave_intervals:
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if len(leave) > 1:
                    for each in leave:
                        if each.holiday_id:
                            multi_leaves.append(each.holiday_id)
                else:
                    holiday = leave.holiday_id
                    current_leave_struct = leaves.setdefault(
                        holiday.holiday_status_id,
                        {
                            "name": holiday.holiday_status_id.name
                            or _("Global Leaves"),
                            "sequence": 5,
                            "code": holiday.holiday_status_id.code or "GLOBAL",
                            "number_of_days": 0.0,
                            "number_of_hours": 0.0,
                            "contract_id": contract.id,
                        },
                    )
                    current_leave_struct["number_of_hours"] += hours
                    if work_hours:
                        current_leave_struct["number_of_days"] += hours / work_hours
            # compute worked days
            work_data = contract.employee_id.get_work_days_data(
                day_from, day_to, calendar=contract.resource_calendar_id
            )
            attendances = {
                "name": _("Normal Working Days paid at 100%"),
                "sequence": 1,
                "code": "WORK100",
                "number_of_days": work_data["days"],
                "number_of_hours": work_data["hours"],
                "contract_id": contract.id,
            }
            res.append(attendances)
            uniq_leaves = [*set(multi_leaves)]
            c_leaves = {}
            for rec in uniq_leaves:
                duration = rec.duration_display.replace("days", "").strip()
                duration_in_hours = float(duration) * 24
                c_leaves.setdefault(rec.holiday_status_id, {"hours": duration_in_hours})
            for item in c_leaves:
                if not leaves or item not in leaves:
                    data = {
                        "name": item.name,
                        "sequence": 20,
                        "code": item.code or "LEAVES",
                        "number_of_hours": c_leaves[item]["hours"],
                        "number_of_days": c_leaves[item]["hours"] / work_hours,
                        "contract_id": contract.id,
                    }
                    res.append(data)
                for time_off in leaves:
                    if item == time_off:
                        leaves[item]["number_of_hours"] += c_leaves[item]["hours"]
                        leaves[item]["number_of_days"] += (
                            c_leaves[item]["hours"] / work_hours
                        )
            res.extend(leaves.values())
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """Function for getting contracts upon date_from and date_to fields"""
        res = []
        structure_ids = contracts.get_all_structures()
        rule_ids = (
            self.env["hr.payroll.structure"].browse(structure_ids).get_all_rules()
        )
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env["hr.salary.rule"].browse(sorted_rule_ids).mapped("input_ids")
        for contract in contracts:
            for input in inputs:
                input_data = {
                    "name": input.name,
                    "code": input.code,
                    "contract_id": contract.id,
                    "date_from": date_from,
                    "date_to": date_to,
                }
                res.append(input_data)
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        """Function for getting Payslip Lines"""

        def _sum_salary_rule_category(localdict, category, amount):
            """Function for getting total sum of Salary Rule Category"""
            if category.parent_id:
                localdict = _sum_salary_rule_category(
                    localdict, category.parent_id, amount
                )
            localdict["categories"].dict[category.code] = (
                category.code in localdict["categories"].dict
                and localdict["categories"].dict[category.code] + amount
                or amount
            )
            return localdict

        class BrowsableObject(object):
            """Class for Browsable Object"""

            def __init__(self, employee_id, dict, env):
                """Function for getting employee_id,dict and env"""
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                """Function for return dict"""
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute(
                    """
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code),
                )
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def _sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip days with respect to
                from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute(
                    """
                    SELECT sum(number_of_days) as number_of_days, 
                    sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code),
                )
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip hours with respect to
                from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute(
                    """SELECT sum(case when hp.credit_note = 
                False then (pl.total) else (-pl.total) end)
                FROM hr_payslip as hp, hr_payslip_line as pl
                WHERE hp.employee_id = %s AND hp.state = 'done'
                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id 
                = pl.slip_id AND pl.code = %s""",
                    (self.employee_id, from_date, to_date, code),
                )
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten
        # by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env["hr.payslip"].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line
        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)
        baselocaldict = {
            "categories": categories,
            "rules": rules,
            "payslip": payslips,
            "worked_days": worked_days,
            "inputs": inputs,
        }
        # get the ids of the structures on the contracts and their
        # parent id as well
        contracts = self.env["hr.contract"].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = (
            self.env["hr.payroll.structure"].browse(structure_ids).get_all_rules()
        )
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env["hr.salary.rule"].browse(sorted_rule_ids)
        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            for rule in sorted_rules:
                key = rule.code + "-" + str(contract.id)
                localdict["result"] = None
                localdict["result_qty"] = 1.0
                localdict["result_rate"] = 100
                # check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = (
                        rule.code in localdict and localdict[rule.code] or 0.0
                    )
                    # set/overwrite the amount computed for this rule in
                    # the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(
                        localdict, rule.category_id, tot_rule - previous_amount
                    )
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        "salary_rule_id": rule.id,
                        "contract_id": contract.id,
                        "name": rule.name,
                        "code": rule.code,
                        "category_id": rule.category_id.id,
                        "sequence": rule.sequence,
                        "appears_on_payslip": rule.appears_on_payslip,
                        "condition_select": rule.condition_select,
                        "condition_python": rule.condition_python,
                        "condition_range": rule.condition_range,
                        "condition_range_min": rule.condition_range_min,
                        "condition_range_max": rule.condition_range_max,
                        "amount_select": rule.amount_select,
                        "amount_fix": rule.amount_fix,
                        "amount_python_compute": rule.amount_python_compute,
                        "amount_percentage": rule.amount_percentage,
                        "amount_percentage_base": rule.amount_percentage_base,
                        "register_id": rule.register_id.id,
                        "amount": amount,
                        "employee_id": contract.employee_id.id,
                        "quantity": qty,
                        "rate": rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]
        return list(result_dict.values())

    # YTI
    # TODO To rename. This method is not really an onchange,
    #  as it is not in any view
    # employee_id and contract_id could be browse records
    def onchange_employee_id(
        self, date_from, date_to, employee_id=False, contract_id=False
    ):
        """Function for return worked days when changing onchange_employee_id"""
        # defaults
        res = {
            "value": {
                "line_ids": [],
                # delete old input lines
                "input_line_ids": [
                    (
                        2,
                        x,
                    )
                    for x in self.input_line_ids.ids
                ],
                # delete old worked days lines
                "worked_days_line_ids": [
                    (
                        2,
                        x,
                    )
                    for x in self.worked_days_line_ids.ids
                ],
                # 'details_by_salary_head':[], TODO put me back
                "name": "",
                "contract_id": False,
                "struct_id": False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env["hr.employee"].browse(employee_id)
        locale = self.env.context.get("lang") or "en_US"
        res["value"].update(
            {
                "name": _("Salary Slip of %s for %s")
                % (
                    employee.name,
                    tools.ustr(
                        babel.dates.format_date(
                            date=ttyme, format="MMMM-y", locale=locale
                        )
                    ),
                ),
                "company_id": employee.company_id.id,
            }
        )
        if not self.env.context.get("contract"):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill
                # should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)
        if not contract_ids:
            return res
        contract = self.env["hr.contract"].browse(contract_ids[0])
        res["value"].update({"contract_id": contract.id})
        struct = contract.struct_id
        if not struct:
            return res
        res["value"].update(
            {
                "struct_id": struct.id,
            }
        )
        # computation of the salary input
        contracts = self.env["hr.contract"].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res["value"].update(
            {
                "worked_days_line_ids": worked_days_line_ids,
                "input_line_ids": input_line_ids,
            }
        )
        return res

    @api.onchange(
        "employee_id",
    )
    def onchange_employee(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get("lang") or "en_US"
        self.name = _("Salary Slip of %s for %s") % (
            employee.name,
            tools.ustr(
                babel.dates.format_date(date=ttyme, format="MMMM-y", locale=locale)
            ),
        )
        self.company_id = employee.company_id
        if not self.env.context.get("contract") or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env["hr.contract"].browse(contract_ids[0])
        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env["hr.contract"].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        return

    @api.onchange("contract_id")
    def onchange_contract_id(self):
        """Function for getting structure when changing contract"""
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        """Function for getting total salary line"""
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0

    @api.onchange("date_from")
    def onchange_date_from(self):
        """Function for getting contract for employee"""
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # # computation of the salary input
        contracts = self.env["hr.contract"].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([("name", "=", "Meal Voucher")]):
            self.line_ids.search([("name", "=", "Meal Voucher")]).salary_rule_id.write(
                {"quantity": self.worked_days_line_ids.number_of_days}
            )
        return

    @api.onchange("date_to")
    def onchange_date_to(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env["hr.contract"].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([("name", "=", "Meal Voucher")]):
            self.line_ids.search([("name", "=", "Meal Voucher")]).salary_rule_id.write(
                {"quantity": self.worked_days_line_ids.number_of_days}
            )
        return

    def action_open_compute_salary_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Compute Salary",
            "res_model": "compute.salary.wizard",
            "view_mode": "form",
            "target": "new",  # Opens the form in a pop-up
        }


class ComputeSalaryWizard(models.TransientModel):
    _name = "compute.salary.wizard"
    _description = "Wizard for Computing Salary"

    batch_id = fields.Many2one(
        "calculate.salary.batches", string="Batch Reference", required=True
    )
    fiscal_year = fields.Many2one("account.fiscal.year", string="Fiscal Year")
    department = fields.Many2one("hr.department", string="Department")
    computation_type = fields.Selection(
        [
            ("monthly", "monthly"),
            ("bimonthly", "bi-monthly"),
            ("trimonthly", "tri-monthly"),
        ],
        string="Computation Type",
        required=True,
    )
    computation_number = fields.Selection(
        [
            ("fquarter", "first quaterly"),
            ("squarter", "second quaterly"),
            ("tquarter", "third quaterly"),
            ("foquarter", "fourth quaterly"),
        ],
        string="Computation Number",
        required=True,
    )
    date_from = fields.Date(string="Date From", store=True)
    date_to = fields.Date(string="Date To", store=True)
    # date_from_bs = fields.Char(string='Date From', store=True)
    # date_to_bs = fields.Char(string='Date To', store=True)
    calculate_salary_of_all_employee = fields.Boolean(
        string="Calculate Salary of All Employee", default=False
    )