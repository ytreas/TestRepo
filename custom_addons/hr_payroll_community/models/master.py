from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsuranceCompany(models.Model):
    _name = "insurance.company"
    _description = "Insurance Company"
    _rec_name = "insurance_company_name"

    code = fields.Char(string="Code", required=True)
    insurance_company_name = fields.Char(string="Name (En)")
    insurance_company_name_np = fields.Char(string="Name (Np)")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
    )
    description = fields.Text(string="Description")


class LoanType(models.Model):

    _name = "loan.type"
    _description = "Loan Type"
    _rec_name = "loan_type_name"

    code = fields.Char(string="Code", required=True)
    loan_type_name = fields.Char(string="Name (En)")
    loan_type_name_np = fields.Char(string="Name (Np)")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
    )
    description = fields.Text(string="Description")


class AdvanceType(models.Model):

    _name = "advance.type"
    _description = "Advance Type"
    _rec_name = "advance_type_name"

    code = fields.Char(string="Code", required=True)
    advance_type_name = fields.Char(string="Name (En)")
    advance_type_name_np = fields.Char(string="Name (Np)")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
    )
    description = fields.Text(string="Description")


class HelpModule(models.Model):
    _name = "help.module"
    _description = "Sub Module"
    _rec_name = "help_module_name_np"

    code = fields.Char(string="Code", required=True)
    help_module_name = fields.Char(string="Name (En)")
    help_module_name_np = fields.Char(string="Name (Np)")
    help_module = fields.Selection(
        selection=[
            ("income", "Income"),
            ("assets", "Assets"),
            ("expenditure", "Expenditure"),
            ("liablities", "Liablities"),
            ("धरौटी ", "धरौटी "),
        ],
        string="Module",
    )
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
    )
    description = fields.Text(string="Description")


class MainSubjectArea(models.Model):
    _name = "main.subject.area"
    _description = "Main Subject Area"
    _rec_name = "subject_area_name"

    code = fields.Char(string="Code", required=True)
    subject_area_name = fields.Char(string="Name (En)")
    subject_area_name_np = fields.Char(string="Name (Np)")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
    )
    sequence = fields.Integer(string="Sequence")
    description = fields.Text(string="Description")


class SubjectArea(models.Model):
    _name = "subject.area"
    _description = "Subject Area"
    _rec_name = "name_np"

    code = fields.Char(string="Code", required=True)
    name_np = fields.Char(string="Name Np", required=True)
    name_en = fields.Char(string="Name En", required=True)
    location = fields.Char(string="Location")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    contact_person = fields.Char(string="Contact Person")
    bank_name = fields.Char(string="Bank Name")
    bank_branch = fields.Char(string="Bank Branch")
    account_no = fields.Char(string="Account No")
    sanction_type = fields.Char(string="Sanction Type")
    sanction_amount_type = fields.Char(string="Sanction Amount Type")
    total_amount_type = fields.Char(string="Total Amount Type")
    main_subject_area_id = fields.Many2one(
        "main.subject.area", string="Main Subject Area"
    )
    higher_subject_area_id = fields.Many2one(
        "subject.area", string="Higher Subject Area"
    )
    pan_no = fields.Char(string="Pan No")
    masalanda_goods_ids = fields.One2many(
        "subject.area.masalanda", "subject_area_id", string="Masalanda Goods"
    )
    remarks = fields.Text(string="Remarks")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
    )


class AllowanceMaster(models.Model):
    _name = "allowance.master"
    _rec_name = "display_name"

    display_name = fields.Char(string="Display Name", compute="_compute_display_name")
    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    deduction = fields.Boolean(string="Deduction")
    type = fields.Selection(
        selection=[("monthly", "Monthly"), ("yearly", "Yearly")],
        string="Type",
        default="monthly",
    )
    description = fields.Text(string="Description")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.name_en + " " + "/" + rec.type


# BufferModel
class ContractAllowance(models.Model):
    _name = "contract.allowance"
    _description = "Contract Allowance"

    # allowance_id = fields.Many2one('allowance.master', string='Name', required=True)
    allowance_id = fields.Many2one("hr.salary.rule", string="Name", required=True)
    amount = fields.Float(string="Amount", required=True)
    category_id = fields.Many2one(
        "hr.salary.rule.category", related="allowance_id.category_id", string="Pay Head"
    )
    job_ids = fields.Many2one("hr.job", string="Job")
    contract_ids = fields.Many2one("hr.contract", string="Contract")
    employee_post_ids = fields.Many2one("employee.post", string="Employee Post")


class MasalandaGoods(models.Model):
    _name = "masalanda.goods"
    _description = "Masalanda Goods"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    remarks = fields.Text(string="Remarks")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )


class SubjectAreaMasalanda(models.Model):
    _name = "subject.area.masalanda"
    _description = "Subject Area Masalanda"

    masalanda_id = fields.Many2one(
        "masalanda.goods", string="Masalanda Goods", required=True
    )
    quantity = fields.Float(string="Quantity", required=True)
    unit_price = fields.Float(string="Unit Price", required=True)
    total_price = fields.Float(string="Total Price", required=True)
    remarks = fields.Text(string="Remarks")
    subject_area_id = fields.Many2one(
        "subject.area", string="Subject Area", required=True
    )


class PaymentMedium(models.Model):
    _name = "payment.medium"
    _description = "Payment Medium"
    _rec_name = "name_np"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    description = fields.Text(string="Description")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )


class Month(models.Model):
    _name = "month"
    _description = "Month"
    _rec_name = "name_en"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    date_from = fields.Date(string="Date From", required=True)
    date_from_bs = fields.Char(string="Date From", store=True)
    date_to = fields.Date(string="Date To", required=True)
    date_to_bs = fields.Char(string="Date To", store=True)
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )


class EmployeePost(models.Model):
    _name = "employee.post"
    _description = "Employee Post"
    _rec_name = "name_np"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    designation_id = fields.Many2one("employee.post.designation", string="Designation")
    post_type = fields.Selection(
        related="designation_id.position_type", string="Post Type", readonly=False
    )

    categoty_level = fields.Many2one(
        "employee.post.designation", string="Category/Level"
    )
    base_salary = fields.Integer(
        string="Base Salary", related="categoty_level.salary_scale", readonly=True
    )
    job_description = fields.Text(string="Job Description")
    allowance_ids = fields.One2many(
        "contract.allowance", "employee_post_ids", string="Allowances"
    )
    remarks = fields.Text(string="Remarks")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )

    @api.model
    def create(self, vals):
        record = super(EmployeePost, self).create(vals)

        # Check if base_salary exists and is greater than 0
        if record.base_salary:
            # Find the allowance_id where category_id is 'Basic'
            basic_allowance = self.env["hr.salary.rule"].search(
                [("category_id.name", "=", "Basic")], limit=1
            )

            if basic_allowance:
                self.env["contract.allowance"].create({
                    "allowance_id": basic_allowance.id,
                    "amount": record.base_salary,
                    "category_id": basic_allowance.category_id.id,
                    "employee_post_ids": record.id,
                })

        return record
    
class IssuerBank(models.Model):
    _name = "issuer.bank"
    _description = "issuer bank"
    _rec_name = "bank_name_np"
    _check_company_auto = True

    display_name = fields.Char(string='Display Name', compute='_compute_display_name')
    bank_code = fields.Char(string='Code', required=True)
    bank_name_en = fields.Char(string='Issuer Bank Name English', required=True)
    bank_name_np = fields.Char(string='Issuer Bank Name Nepali', required=True)
    bank_type = fields.Many2one('bank.type',string='Bank Type', required=True)
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company')
class BranchBank(models.Model):
    _name = "branch.bank"
    _description = "branch bank"
    _rec_name = "display_name"
    _check_company_auto = True

    display_name = fields.Char(string='Display Name', compute='_compute_display_name')
    branch_sn = fields.Char(string='Branch SN', required=True)
    code = fields.Char(string="Code", required=True)
    bank_name = fields.Many2one("issuer.bank", string="Bank Name")
    branch_name = fields.Char(string="Branch Name", required=True)
    branch_address = fields.Text(string="Branch Address", required=True)
    branch_address_np = fields.Text(string="Branch Address(Nepali)")
    branch_district_np = fields.Char(string="Branch District(Nepali)")
    branch_name_np = fields.Char(string="Branch Name(Nepali)")
    branch_district = fields.Char(string="Branch District", required=True)
    branch_open_date = fields.Char(string="Branch Open Date")
    branch_code = fields.Char(string="Branch Code", required=True)
    branch_phone = fields.Char(string="Branch Phone")
    branch_email = fields.Char(string="Branch Email")
    branch_manager_name = fields.Char(string="Branch Manager Name")
    branch_manager_phone = fields.Char(string="Branch Manager Phone")
    branch_manager_email = fields.Char(string="Branch Manager Email")
    company_id = fields.Many2one('res.company', string='Company')
class BankType(models.Model):
    _name = "bank.type"
    _description = "bank type"
    _rec_name = "bank_type_np"
    _check_company_auto = True


    code = fields.Char(string="Code", required=True)
    bank_type_en = fields.Char(string="Bank Type(English)", required=True)
    bank_type_np = fields.Char(string="Bank Type(Nepali)", required=True)
    remarks = fields.Text(string="Remarks")
    status = fields.Boolean(string="Status", default=True)
    company_id = fields.Many2one('res.company', string='Company')


