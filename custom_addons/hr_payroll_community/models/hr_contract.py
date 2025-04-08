from odoo import fields, models, api


class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """

    _inherit = "hr.contract"
    _description = "Employee Contract"

    struct_id = fields.Many2one(
        "hr.payroll.structure",
        string="Salary Structure",
        help="Choose Payroll Structure",
    )
    schedule_pay = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("semi-annually", "Semi-annually"),
            ("annually", "Annually"),
            ("weekly", "Weekly"),
            ("bi-weekly", "Bi-weekly"),
            ("bi-monthly", "Bi-monthly"),
        ],
        string="Scheduled Pay",
        index=True,
        default="monthly",
        help="Defines the frequency of the wage payment.",
    )
    resource_calendar_id = fields.Many2one(
        required=True, string="Working Schedule", help="Employee's working schedule."
    )
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    hra = fields.Monetary(string="HRA", tracking=True, help="House rent allowance.")
    travel_allowance = fields.Monetary(
        string="Travel Allowance", help="Travel allowance"
    )
    da = fields.Monetary(string="DA", help="Dearness allowance")
    meal_allowance = fields.Monetary(string="Meal Allowance", help="Meal allowance")
    medical_allowance = fields.Monetary(
        string="Medical Allowance", help="Medical allowance"
    )

    # Added From here
    current_position_date = fields.Date(string="Current Position Date")
    current_position_date_bs = fields.Char(string="Current Position Date (Nepali)")
    date_start = fields.Date("Contract Start Date")
    date_end = fields.Date("Contract End Date")
    date_start_bs = fields.Char("Contract Start Date (Nepali)", store=True)
    date_end_bs = fields.Char("Contract End Date (Nepali)", store=True)
    position_category_name = fields.Many2one(
       related="employee_id.position_name",
        string="Position/Category Level",
        store=True,
    )
    employee_post = fields.Many2one(
        related="employee_id.employee_post",
        string="Employee Post",
        store=True,)
    

    # Allowance Part
    grade_rate = fields.Integer(
        string="Grade Rate", related="position_category_name.grade_rate", store=True
    )
    initial_grade_number = fields.Integer(string="Grade Number", store=True)
    max_grade_number = fields.Integer(
        string="Maximum Grade Number",
        related="position_category_name.max_grade_number",
        store=True,
    )
    grade_amount = fields.Monetary(
        string="Grade Amount",
        help="Grade Amount",
        compute="compute_grade_amount",
        store=True,
    )

    # DEDUCTION PART
    remuneration_tax = fields.Float(
        "Remuneration Tax (RT)", help="Tax rate as a percentage"
    )
    social_security_tax = fields.Float(
        "Social Security Tax (SST)", help="Tax rate as a percentage"
    )
    employers_contribution = fields.Float(
        "Employer's Contribution to SSF/PF", help="Tax rate as a percentage", default=20
    )
    employees_contribution = fields.Float(
        "Employee's Contribution to SSF/PF", help="Tax rate as a percentage", default=11
    )

    # ALLOWANCE FIELDS
    allowance_ids = fields.One2many(
        "contract.allowance", "contract_ids", string="Allowances"
    )
    other_allowance = fields.Float(
        string="Other Allowance", compute="_compute_other_allowance"
    )
    total_yearly = fields.Float(
        string="Total Yearly", compute="_compute_total_yearly"
    )

    # EMPLOYEE DETAILS FIELDS FOR SALARY
    insurance_service = fields.Boolean(string="Insurance Service")
    government_added_insurance_amount = fields.Float(
        string="Government Added Insurance Amount"
    )
    employee_deducted_insurance_amount = fields.Float(
        string="Employee Deducted Insurance Amount"
    )
    leave_deduction = fields.Boolean(string="Leave Deduction")
    payment_medium = fields.Many2one("payment.medium", string="Payment Medium")
    bank_name = fields.Char(string="Bank Name")
    account_number = fields.Char(string="Account Number")
    grade_upgrade_month = fields.Integer(string="Grade Upgrade Month")
    cit_service = fields.Boolean(string="CIT Service")
    cit_percentage = fields.Float(string="CIT Percentage")
    cit_certificate_no = fields.Char(
        related="employee_id.cit_number",  
        string="CIT Number",
        readonly=False,  
        store=True,      
    )
    cit_amount=fields.Float(string="CIT Amount")
    festivities_month = fields.Integer(string="Festivities Month")
    interest_fund_deduction_amount = fields.Float(
        string="Interest Fund Deduction Amount"
    )
    welfare_fund_cut_amount = fields.Float(string="Welfare Fund Cut Amount")
    dress_allowance = fields.Boolean(string="Dress Allowance")
    get_social_security_tax = fields.Boolean(string="Gets Social Security Tax?")
    

    @api.onchange('employee_post')
    def _onchange_employee_post(self):
        """
        Update the allowances in the contract based on the selected employee post.
        """
        if self.employee_post:
            # Fetch allowances from the selected employee post
            allowances = []
            for allowance in self.employee_post.allowance_ids:
                allowances.append((0, 0, {
                    'allowance_id': allowance.allowance_id.id,  # Many2one field for the allowance name
                    'amount': allowance.amount,  # Float field for the allowance amount
                    'category_id': allowance.category_id.id,  # Related field for the category
                    'employee_post_ids': allowance.employee_post_ids.id,  # Employee post linkage
                }))
            # Update the allowance_ids field in the contract
            self.allowance_ids = allowances
        else:
            # Clear the allowances if no employee post is selected
            self.allowance_ids = [(5, 0, 0)]

    # @api.onchange('job_id')
    # def _onchange_job_id(self):
    #     """
    #     On change of Job Position, replicate allowances from hr.job to hr.contract
    #     """
    #     if self.job_id:
    #         # Clear existing allowances
    #         self.allowance_ids = [(5, 0, 0)]

    #         # Replicate allowances from the job position
    #         allowances = [
    #             (0, 0, {
    #                 'allowance_id': allowance.allowance_id.id,
    #                 'amount': allowance.amount,
    #                 'job_ids': self.job_id.id
    #             })
    #             for allowance in self.job_id.allowance_ids
    #         ]
    #         self.allowance_ids = allowances

    @api.depends("allowance_ids.amount", "allowance_ids.allowance_id.other_allowance")
    def _compute_other_allowance(self):
        for contract in self:
            # Compute the sum of amounts where deduction is False
            contract.other_allowance = sum(
                allowance.amount
                for allowance in contract.allowance_ids
                if allowance.allowance_id and (allowance.allowance_id.other_allowance == True)
            )

    @api.depends("allowance_ids.amount", "allowance_ids.allowance_id.type")
    def _compute_total_yearly(self):
        for contract in self:
            # Compute the sum of amounts where deduction is True
            contract.total_yearly = sum(
                allowance.amount
                for allowance in contract.allowance_ids
                if allowance.allowance_id and (allowance.allowance_id.type == "yearly")
            )

    # @api.depends('position_category_name.grade_rate')
    # def _compute_grade_values(self):
    #     """
    #     Compute grade values for the contract based on the grade rate from the related position.
    #     """
    #     for record in self:
    #         if record.grade_rate:
    #             if record.grade_rate == 1:
    #                 record.initial_grade_number = 3
    #             elif record.grade_rate == 2:
    #                 record.initial_grade_number = 6
    #             elif record.grade_rate == 3:
    #                 record.initial_grade_number = 11
    #             else:
    #                 record.initial_grade_number = 0
    #         else:
    #             record.initial_grade_number = 0

    # @api.depends('initial_grade_number', 'max_grade_number')
    # def _compute_grade_amount(self):
    #     """
    #     Compute the grade amount based on initial and maximum grade numbers.
    #     """
    #     for record in self:
    #         if record.initial_grade_number and record.max_grade_number:
    #             # Example logic for calculating grade amount; modify as needed.
    #             record.grade_amount = (record.max_grade_number - record.initial_grade_number) * 1000
    #         else:
    #             record.grade_amount = 0.0

    @api.depends("grade_rate", "initial_grade_number")
    def compute_grade_amount(self):
        for contract in self:
            contract.grade_amount = contract.grade_rate * contract.initial_grade_number

    @api.model
    def cron_increment_grade_rate(self):
        records = self.search([("current_position_date", "!=", False)])
        # print(f"Total records found: {len(records)}")
        for record in records:
            record._increment_grade_rate()

    def _increment_grade_rate(self):
        if self.current_position_date:
            current_date = fields.Date.today()
            position_date = fields.Date.from_string(self.current_position_date)

            years_diff = (current_date - position_date).days // 365
            print(f"Years difference: {years_diff}")

            if years_diff >= 1:
                print(" Before No grade increment required.", self.initial_grade_number)
                new_grade_rate = self.initial_grade_number + 1

                if new_grade_rate > self.max_grade_number:
                    new_grade_rate = self.max_grade_number

                self.initial_grade_number = new_grade_rate
                print(" After No grade increment required.", self.initial_grade_number)
            else:
                print("No grade increment required.")
        else:
            print("No current_position_date set.")

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by
        hierarchy (parent=False first,then first level children and so on)
        and without duplicate
        """
        structures = self.mapped("struct_id")
        if not structures:
            return []
        # YTI TODO return browse records
        return list(set(structures._get_parent_structure().ids))

    def get_attribute(self, code, attribute):
        """Function for return code for Contract"""
        return self.env["hr.contract.advantage.template"].search(
            [("code", "=", code)], limit=1
        )[attribute]

    def set_attribute_value(self, code, active):
        """Function for set code for Contract"""
        for contract in self:
            if active:
                value = (
                    self.env["hr.contract.advantage.template"]
                    .search([("code", "=", code)], limit=1)
                    .default_value
                )
                contract[code] = value
            else:
                contract[code] = 0.0
