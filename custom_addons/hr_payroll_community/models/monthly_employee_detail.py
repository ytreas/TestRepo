from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date


class MonthlyEmployeeDetail(models.Model):
    _name = "montly.employee.detail"
    _description = "Montly Employee Detail"
    # _rec_name = 'insurance_company_name'

    payslip_id = fields.Many2one('hr.payslip',string='Payslip')
    employee_sn_number = fields.Char(string='Employee SN Number')
    employee_name= fields.Many2one('hr.employee',string='Employee Name')
    employee_position= fields.Char(string='Employee Position')
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
    incentive_allowance = fields.Float(string="Incentive Allowance")
    communication_expense = fields.Float(string="Communication Expense")
    insurance_deduction = fields.Float(string="Insurance Deduction")
    total_total = fields.Float(string="Net Amount Received By Employee")
    welfare_fund_cut = fields.Float(string="Welfare Fund Deduction")
    total_deduction = fields.Float(string="Total Deduction")
    woman_tax_discount = fields.Float(string="Womans 10% Tax Discount")
    medical_allowance = fields.Float(string="Medical Allowance")
    # citizen_investment_fund = fields.Float(string="Citizen Investment Fund")
    remarks = fields.Char(string="Remarks")
    batch_id = fields.Many2one("calculate.salary.batches", string="Batch")
    total_allowance = fields.Float(string="Total Allowance")    
    salary_grade = fields.Float(string="Salary Grade")
    total_allowance = fields.Float(string="Total Allowance")

class CalculateSalaryBatches(models.Model):
    _name = "calculate.salary.batches"
    _description = "Calculate Salary Batches"
    _rec_name = "id"

    batch_date = fields.Date(string="Batch Date")
    batch_date_bs = fields.Char(string="Batch Date BS", store=True)
    batch_description = fields.Char(string="Batch Description")
    # confirm_salary_payment = fields.Boolean(string='Confirm Salary Payment')
    fiscal_year = fields.Many2one("account.fiscal.year", string="Fiscal Year")
    department = fields.Many2one("hr.department", string="Department")
    computation_type = fields.Selection(
        [
            ("monthly", "monthly"),
            ("bimonthly", "bi-monthly"),
            ("trimonthly", "tri-monthly"),
            ("quarterly", "quarterly"),
        ],
        string="Computation Type", store=True
    )
    computation_number = fields.Selection(
        [
            ("fquarter", "first quaterly"),
            ("squarter", "second quaterly"),
            ("tquarter", "third quaterly"),
            ("foquarter", "fourth quaterly"),
        ],
        string="Computation Number",
    )
    letter_number = fields.Char(string="Letter Number")
    confirmed_salary_payment = fields.Boolean(
        string="Confirmed Salary Payment", default=False
    )
    prepared_salary_payment = fields.Boolean(
        string="Prepared Salary Payment", default=False
    )
    approved_salary_payment = fields.Boolean(
        string="Approved Salary Payment", default=False
    )
    salary_confirming_person = fields.Many2one("res.users", string="Confirming Person")
    salary_preparing_person = fields.Many2one("res.users", string="Preparing Person")
    salary_approving_person = fields.Many2one("res.users", string="Approving Person")
    salary_confirmed_date = fields.Date(string="Confirmed Date")
    salary_confirmed_date_bs = fields.Char(string="Confirmed Date BS")
    bank_name = fields.Many2one('issuer.bank', string="Bank Name")
    bank_branch = fields.Many2one('branch.bank', string="Bank Branch")
    monthly_employee_detail_ids = fields.One2many(
        "montly.employee.detail", "batch_id", string="Employee Name"
    )
    months = fields.Many2many('month',string='Month',required=True)
    date_from = fields.Date(string='Date From',store = True)
    date_to = fields.Date(string='Date To', store = True)
    calculate_salary_of_all_employee = fields.Boolean(string='Calculate Salary of All Employee', default=False)
    # leave_penalty_include = fields.Boolean(string='Include Leave Penalty', default=False)
    # calculate_festival_allowance = fields.Boolean(string='Calculate Festival Allowance', default=False)
    # include_lunch_allowance = fields.Boolean(string='Include Lunch Allowance', default=False)
    # include_clothing_allowance = fields.Boolean(string='Include Clothing Allowance', default=False)
    # motivation_allowance = fields.Boolean(string='Include Motivation Allowance', default=False)
    use_yearly_service = fields.Boolean(string='Use Yearly Service', default=False)
    payslip_count = fields.Integer(string='Payslip Count', compute='_compute_payslip_count')

    @api.onchange('months')
    def _onchange_months(self):
        if self.months:
            # Get number of selected months
            selected_month_count = len(self.months)
            
            # Validation for maximum 3 months
            if selected_month_count > 3:
                raise ValidationError("You cannot select more than 3 months!")
                
            # Get sorted month codes
            month_codes = sorted([int(month.code) for month in self.months])
            
            # Check if months are sequential
            if selected_month_count > 1:
                for i in range(len(month_codes) - 1):
                    if month_codes[i + 1] - month_codes[i] != 1:
                        raise ValidationError("Please select sequential months only!")

            # Set computation_type based on number of months
            if selected_month_count == 1:
                self.computation_type = 'monthly'
            elif selected_month_count == 2:
                self.computation_type = 'bimonthly'
            elif selected_month_count == 3:
                self.computation_type = 'trimonthly'
            else:
                self.computation_type = False

            # Set computation_number based on selected months
            if selected_month_count == 3:
                # First quarter: 01, 02, 03
                if month_codes == [1, 2, 3]:
                    self.computation_number = 'fquarter'
                # Second quarter: 04, 05, 06
                elif month_codes == [4, 5, 6]:
                    self.computation_number = 'squarter'
                # Third quarter: 07, 08, 09
                elif month_codes == [7, 8, 9]:
                    self.computation_number = 'tquarter'
                # Fourth quarter: 10, 11, 12
                elif month_codes == [10, 11, 12]:
                    self.computation_number = 'foquarter'
                else:
                    self.computation_number = False
            else:
                self.computation_number = False
                
    def computecompute(self, vals):
        # Check if '_skip_generate_details' is in the context
        if not self.env.context.get("_skip_generate_details"):
            # Update the batch record and generate employee details
            result = super(CalculateSalaryBatches, self).write(vals)
            self._generate_employee_details(self)
            return result
        else:
            # Perform write without generating details
            return super(CalculateSalaryBatches, self).write(vals)

    def _generate_employee_details(self):
        """Populate Monthly Employee Details from hr.payslip."""
        # Get payslip records for the current batch
        domain = [('batches_id', '=', self.id)]
        # Get payslip records (modify domain as needed)
        if self.department:
            domain.append(('employee_id.department_id', '=', self.department.id))
        
        payslip_records = self.env['hr.payslip'].search(domain)

        # Prepare details
        details = []
        for payslip in payslip_records:
            detail = {
                'payslip_id': payslip.id,
                'employee_sn_number': payslip.employee_id.identification_id or '',
                'employee_name': payslip.employee_id.id,
                'employee_position': payslip.contract_id.job_id.name or '',
                'starting_salary': payslip.starting_salary if payslip.starting_salary else 0.0,
                'total': payslip.total if payslip.total else 0.0,
                'grade_amount': payslip.grade_amount if payslip.grade_amount else 0.0,
                'grade_quantity': payslip.grade_quantity if payslip.grade_quantity else 0.0,
                # 'citizen_investment_fund': payslip.citizen_investment_fund if payslip.citizen_investment_fund else 0.0,
                'dearness_allowance': payslip.dearness_allowance if payslip.dearness_allowance else 0.0,
                'qa_allowance': payslip.qa_allowance if payslip.qa_allowance else 0.0,
                'social_security_tax': payslip.social_security_tax if payslip.social_security_tax else 0.0,
                'allowance': payslip.allowance if payslip.allowance else 0.0,
                'special_allowance': payslip.special_allowance if payslip.special_allowance else 0.0,
                'medical_allowance': payslip.medical_allowance if payslip.medical_allowance else 0.0,
                'loan': payslip.loan if payslip.loan else 0.0,
                'salary_grade': payslip.salary_grade if payslip.salary_grade else 0.0,
                'total_allowance': payslip.total_allowance if payslip.total_allowance else 0.0,
                'lunch_allowance': payslip.lunch_allowance if payslip.lunch_allowance else 0.0,
                'dress_allowance': payslip.dress_allowance if payslip.dress_allowance else 0.0,
                'submission': payslip.submission if payslip.submission else 0.0,
                'local_allowance': payslip.local_allowance if payslip.local_allowance else 0.0,
                'other_allowance': payslip.other_allowance if payslip.other_allowance else 0.0,
                'income_tax': payslip.income_tax if payslip.income_tax else 0.0,
                'absent_days': payslip.absent_days if payslip.absent_days else 0.0,
                'absent_deduction': payslip.absent_deduction if payslip.absent_deduction else 0.0,
                'pf_add': payslip.pf_add if payslip.pf_add else 0.0,
                'extraordinary_holiday': payslip.extraordinary_holiday if payslip.extraordinary_holiday else 0.0,
                # 'citizen_investment_fund': payslip.citizen_investment_fund if payslip.citizen_investment_fund else 0.0,
                'extraordinary_holiday_deduction': payslip.extraordinary_holiday_deduction if payslip.extraordinary_holiday_deduction else 0.0,
                'interest_fund_deduction': payslip.interest_fund_deduction if payslip.interest_fund_deduction else 0.0,
                'insurance_add': payslip.insurance_add if payslip.insurance_add else 0.0,
                'technical_allowance': payslip.technical_allowance if payslip.technical_allowance else 0.0,
                'transport_allowance': payslip.transport_allowance if payslip.transport_allowance else 0.0,
                'food_allowance': payslip.food_allowance if payslip.food_allowance else 0.0,
                'other_deduction': payslip.other_deduction if payslip.other_deduction else 0.0,
                'cit_cut': payslip.cit_cut if payslip.cit_cut else 0.0,
                'pf_deduction': payslip.pf_deduction if payslip.pf_deduction else 0.0,
                'incentive_allowance': payslip.incentive_allowance if payslip.incentive_allowance else 0.0,
                'communication_expense': payslip.communication_expense if payslip.communication_expense else 0.0,
                'insurance_deduction': payslip.insurance_deduction if payslip.insurance_deduction else 0.0,
                'welfare_fund_cut': payslip.welfare_fund_cut if payslip.welfare_fund_cut else 0.0,
                'total_total': payslip.total_total if payslip.total_total else 0.0,
                'total_deduction': payslip.total_deduction if payslip.total_deduction else 0.0,
                'total_allowance': payslip.total_allowance if payslip.total_allowance else 0.0,
            }
            details.append((0, 0, detail))

        # Add the details to the batch without triggering recursion
        self.with_context(_skip_generate_details=True).computecompute(
            {"monthly_employee_detail_ids": details}
        )

    def action_open_compute_salary_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Compute Salary",
            "res_model": "compute.salary.wizard",
            "view_mode": "form",
            "target": "new",  # Opens the form in a pop-up
            "context": {
                "default_batch_id": self.id,  # Pass the current record ID to the wizard
            },
        }
    
    @api.onchange('months')
    def compute_date_from(self):
        for record in self:
            if self.months:
                self.date_from = min(self.months.mapped('date_from'))
                print("Date From: ", self.date_from)
            else:
                record.date_from = False 

    @api.onchange('months')
    def compute_date_to(self):
        for record in self:
            if self.months:
                self.date_to = max(self.months.mapped('date_to'))
                print("Date To: ", self.date_to)
            else:
                record.date_to = False 

    def action_compute(self):
        # Ensure date_from and date_to are provided in the wizard
        if not self.date_from or not self.date_to:
            raise UserError("Please provide both 'Date From' and 'Date To' in the wizard.")
        
        self.env['hr.payslip'].generate_payslips_from_contracts(self.id,self.department)

        selected_payslips = self.env['hr.payslip'].search([('batches_id', '=', self.id)])
        if self.department :
            pp = 0
        else:
            pp= len(selected_payslips)
            
        # Update date_from and date_to for each selected payslip
        for payslip in selected_payslips:
            if self.department :
                if payslip.employee_id.department_id.id == self.department.id:
                    pp = pp +1
                    payslip.write({
                        'date_from': self.date_from or payslip.date_from,  
                        'date_to': self.date_to or payslip.date_to,  
                        'use_yearly_service': self.use_yearly_service   
                    })
                    contracts = payslip.contract_id
                    if contracts:
                        worked_day_lines = payslip.get_worked_day_lines(contracts, self.date_from,self.date_to)
                        payslip.write({'worked_days_line_ids': [(5, 0, 0)]+[(0,0,line) for line in worked_day_lines]})
                    payslip.action_compute_sheet()

            else:
                payslip.write({
                    'date_from': self.date_from or payslip.date_from,  
                    'date_to': self.date_to or payslip.date_to,  
                    'use_yearly_service': self.use_yearly_service  
                })
                contracts = payslip.contract_id
                if contracts:
                    worked_day_lines = payslip.get_worked_day_lines(contracts, self.date_from,self.date_to)
                    payslip.write({'worked_days_line_ids': [(5, 0, 0)]+[(0,0,line) for line in worked_day_lines]})
                payslip.action_compute_sheet()

        self._generate_employee_details()

        # Notify the user about the completion of the computation
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Salary Computation Complete',
                'message': f'Computed salary for {pp} payslip(s).',
                'sticky': False,
            }
        }

    def action_confirm_salary(self):
        #Confirming hr.payslip employee salary slip from salary Batches
        payslips = self.env["hr.payslip"].search([("batches_id", "=", self.id)])

        for payslip in payslips:
            if payslip.state != "done":
                payslip.action_payslip_done()

        self.confirmed_salary_payment = True
        self.salary_confirming_person = self.env.user.id
        self.salary_confirmed_date = date.today()

        payslips = self.env["hr.payslip"].search([("batches_id", "=", self.id)])

        for payslip in payslips:
            if payslip.state != "done":
                payslip.action_payslip_done()

    def _compute_payslip_count(self):
        for record in self:
            record.payslip_count = len(record.monthly_employee_detail_ids)

    def action_prepare_salary(self):
        self.prepared_salary_payment = False
        self.approved_salary_payment = False
        self.salary_preparing_person = self.env.user.id
    
    def action_approve_salary(self):
        self.approved_salary_payment = True
        self.confirmed_salary_payment = False
        self.salary_approving_person = self.env.user.id
    
