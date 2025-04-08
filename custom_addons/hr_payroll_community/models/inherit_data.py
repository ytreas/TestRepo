from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


# inherits
class HREmployeeinherit(models.Model):
    _inherit = "hr.employee"

    pan_number = fields.Char(string="PAN Number", tracking=True, size=9)
    date_of_birth_en = fields.Date(string="Date of Birth")
    date_of_birth_np = fields.Char(string="Date of Birth (Np)", store=True)
    father_name_en = fields.Char(string="Father's Name (En)")
    mother_name_en = fields.Char(string="Mother's Name (En)")
    father_name_np = fields.Char(string="Father's Name (Np)")
    mother_name_np = fields.Char(string="Mother's Name (Np)")
    spouse_name_en = fields.Char(string="Spouse's Name (En)")
    spouse_name_np = fields.Char(string="Spouse's Name (Np)")
    wished_person_name_en = fields.Char(string="Wished Person's Name (En)")
    wished_person_name_np = fields.Char(string="Wished Person's Name (Np)")
    employee_name_np = fields.Char(
        string="Employee Name (NP)",
    )
    issuer_bank_name = fields.Many2one("issuer.bank", string="Bank Name", tracking=True)
    branch_bank_name = fields.Many2one(
        "branch.bank", string="Branch Name", tracking=True
    )
    account_number = fields.Char(string="Account Number")

    # insurance_details
    insurance_company_id = fields.Many2one(
        "insurance.company", string="Insurance Company"
    )
    insurance_policy_number = fields.Char(string="Insurance Policy Number")
    cit_number = fields.Char(string="CIT Number")
    pis_number = fields.Char(string="PIS Number")

    # identity_card_number = fields.Char(string="Identity Card Number")
    personal_identification_number = fields.Char(
        string="Personal Identification Number"
    )
    seat_roll_number = fields.Char(string="Seat Roll Number")
    pf_number = fields.Char(string="PF Number")


class HrJob(models.Model):
    _inherit = "employee.tax.config"

    gender = fields.Selection(
        selection=[("male", "Male"), ("female", "Female"), ("others", "Others")],
        string="Gender",
        required=True,
    )

    disability_type = fields.Many2one("disability.type", string="Disability Type")


class HrJob(models.Model):
    _inherit = "hr.job"

    position_category_name = fields.Many2one(
        "employee.post.designation", string="Position/Category Level"
    )
    allowance_ids = fields.One2many(
        "contract.allowance", "job_ids", string="Allowances"
    )


# Master
class EmployeePostDesignation(models.Model):
    _name = "employee.post.designation"
    _description = "Employee Post Designation"
    _rec_name = "position_category_name_np"

    code = fields.Char(string="Code", required=True)
    position_category_name_en = fields.Char(string="Position/Category Name (EN)")
    position_category_name_np = fields.Char(string="Position/Category Name (NP)")
    position_category_level = fields.Integer(string="Position/Category Level ")
    position_short_name_en = fields.Char(string="Position Short Name (EN)")
    position_short_name_np = fields.Char(string="Position Short Name (NP)")
    salary_scale = fields.Integer(string="Salary Scale")
    position_type = fields.Selection(
        selection=[
            ("technical", "Technical"),
            ("non-technical", "Non-Technical"),
        ],
        string="Position Type",
    )
    grade_rate = fields.Integer("Grade Rate")
    initial_grade_number = fields.Integer("Grade Number")
    max_grade_number = fields.Integer("Max Grade Number")
    adjusted_grade_rate = fields.Integer("Adjusted Grade Rate")
    max_grade_amount = fields.Float("Max Grade Amount")

    # @api.onchange('position_category_level_np')
    # def _onchange_position_category_level_np(self):
    #     """Set default grade values based on position_category_level_np."""
    #     for record in self:
    #         if record.position_category_level_np:
    #             # Set grade values based on position_category_level_np.
    #             if record.position_category_level_np <= 5:
    #                 record.grade_rate = 1
    #                 record.initial_grade_number = 3
    #                 record.max_grade_number = 5
    #             elif record.position_category_level_np <= 10:
    #                 record.grade_rate = 2
    #                 record.initial_grade_number = 6
    #                 record.max_grade_number = 10
    #             else:
    #                 record.grade_rate = 3
    #                 record.initial_grade_number = 11
    #                 record.max_grade_number = 15
    #         else:
    #             # Default values if position_category_level_np is not set.
    #             record.grade_rate = 0
    #             record.initial_grade_number = 0
    #             record.max_grade_number = 0


class DisabilityType(models.Model):
    _name = "disability.type"
    _description = "Disability Type"
    _rec_name = "name_en"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)")
    description = fields.Text(string="Description")


class AppClientSetting(models.Model):
    _name = "app.client.setting"
    _description = "App Client Setting"

    discount_rate = fields.Float(string="Discount Rate (%)", required=True)
    payroll_round = fields.Boolean(string="Payroll Round", default=True)


class HrDepart(models.Model):
    _inherit = "hr.department"

    code = fields.Char(string="Code", required=True)
    name_np = fields.Char(string="Department Name (NP)")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )
