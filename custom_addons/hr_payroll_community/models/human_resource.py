from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class EmployeeAddSub(models.Model):
    _name = "employee.add.sub"
    _description = "Employee Add/Sub"

    code = fields.Char(string="Code", required=True)
    fiscal_years = fields.Many2one("account.fiscal.year", string="Fiscal Year")
    month = fields.Selection(
        selection=[
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Month",
        required=True,
    )
    local_position = fields.Char(string="Local Position")
    account_id = fields.Many2one("account.account", string="Account", required=True)
    amount = fields.Float(string="Amount", required=True)
    addsub = fields.Selection(
        selection=[("add", "Add"), ("sub", "Sub")], string="Add/Sub", required=True
    )
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )
    remarks = fields.Text(string="Remarks")


class PositionType(models.Model):
    _name = "position.type"
    _description = "Position Type"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    description = fields.Text(string="Description")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )


class EmployeeServiceGroup(models.Model):
    _name = "employee.service.group"
    _description = "Employee Service Group"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    description = fields.Text(string="Description")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )


class EmployeeArea(models.Model):
    _name = "employee.area"
    _description = "Employee Area"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    description = fields.Text(string="Description")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )


class RepresentativeDetails(models.Model):
    _name = "representative.details"
    _description = "Representative Details"

    code = fields.Char(string="Code")
    representative_position = fields.Char(string="Representative Position")
    designation = fields.Char(string="Designation")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )
    current = fields.Selection(
        selection=[("current", "Current"), ("past", "Past")],
        string="Current",
    )
    taxpayer = fields.Char(string="Taxpayer")
    first_name_en = fields.Char(string="Name (EN)")
    first_name_np = fields.Char(string="Name (NP)")
    middle_name_en = fields.Char(string="Middle Name (EN)")
    middle_name_np = fields.Char(string="Middle Name (NP)")
    surname_en = fields.Char(string="Surname (EN)")
    surname_np = fields.Char(string="Surname (NP)")
    fathers_name_en = fields.Char(string="Father's Name (EN)")
    fathers_name_np = fields.Char(string="Father's Name (NP)")
    grandfather_name_en = fields.Char(string="Grandfather's Name (EN)")
    grandfather_name_np = fields.Char(string="Grandfather's Name (NP)")
    date_of_birth = fields.Date(string="Date of Birth")
    date_of_birth_np = fields.Char(string="Date of Birth (NP)")
    gender = fields.Selection(
        selection=[("male", "Male"), ("female", "Female"), ("other", "Others")],
        string="Gender",
    )
    religion = fields.Selection(
        selection=[
            ("hindu", "Hindu"),
            ("buddhist", "Buddhist"),
            ("christian", "Christian"),
            ("muslim", "Muslim"),
            ("kirat", "Kirat"),
            ("bone", "Bone"),
            ("sikh", "Sikh"),
            ("others", "Others"),
        ],
        string="Religion",
    )
    mother_tongue = fields.Selection(
        selection=[
            ("nepali", "Nepali"),
            ("newari", "Newari"),
            ("gurung", "Gurung"),
            ("bajika", "Bajika"),
            ("urdu", "Urdu"),
            ("rajbanshi", "Rajbanshi"),
            ("sherpa", "Sherpa"),
            ("hindi", "Hindi"),
            ("doteli", "Doteli"),
            ("other", "Other"),
            ("maithili", "Maithili"),
            ("bhojpuri", "Bhojpuri"),
            ("tharu", "Tharu"),
            ("tamang", "Tamang"),
            ("magar", "Magar"),
            ("awadi", "Awadi"),
            ("not_unknown_not_applicable", "Not Unknown/Not Applicable"),
        ],
        string="Mother Tongue",
    )
    country = fields.Many2one("res.country", string="Country")
    nationality = fields.Selection(
        selection=[
            ("nepali", "Nepali"),
            ("indian", "Indian"),
            ("chinese", "Chinese"),
            ("pakistani", "Pakistani"),
            ("bangali", "Bangali"),
            ("bangladeshi", "Bangladeshi"),
            ("birtani", "Birtani"),
            ("not_applicable_not_known", "Not Applicable/Not Known"),
        ],
        string="Nationality",
    )
    citizenship_number = fields.Char(string="Citizenship Number")
    citizenship_issue_date = fields.Date(string="Citizenship Issue Date")
    citizenship_issue_date_np = fields.Char(
        string="Citizenship Issue Date (NP)", store=True
    )
    citizenship_issue_district = fields.Char(string="Citizenship Issue District")
    passport_number = fields.Char(string="Passport Number")
    passport_issue_date = fields.Date(string="Passport Issue Date")
    passport_issue_date_np = fields.Char(string="Passport Issue Date (NP)", store=True)
    passport_issue_district = fields.Char(string="Passport Issue District")
    identity_card_number = fields.Char(string="Identity Card Number")
    identity_issue_date = fields.Date(string="Identity Issue Date")
    identity_issue_date_np = fields.Char(string="Identity Issue Date (NP)", store=True)
    identity_issue_district = fields.Char(string="Identity Issue District")
    pan_number = fields.Char(string="PAN Number")
    other_description = fields.Text(string="Other Description")
    permanent_address = fields.Text(string="Address")
    permanent_house_number = fields.Char(string=" House Number")
    permanent_tole_name = fields.Char(string=" Tole Name")
    permanent_street_name = fields.Char(string=" Street Name")
    temporary_address = fields.Text(string=" Address")
    temporary_house_number = fields.Char(string=" House Number")
    temporary_tole_name = fields.Char(string=" Tole Name")
    temporary_street_name = fields.Char(string=" Street Name")
    phone_number = fields.Char(string="Phone Number")
    mobile_number = fields.Char(string="Mobile Number")
    email_address = fields.Char(string="Email Address")
    mailing_address = fields.Text(string="Mailing Address")
    current_position_start_date = fields.Date(string="Current Position Start Date")
    current_position_start_date_np = fields.Char(
        string="Current Position Start Date (NP)", store=True
    )
    current_position_end_date = fields.Date(string="Current Position End Date")
    current_position_end_date_np = fields.Char(
        string="Current Position End Date (NP)", store=True
    )
    sequentially = fields.Integer(string="Sequentially")
    payment_medium = fields.Many2one("payment.medium", string="Payment Medium")

    bank_name = fields.Char(string="Bank Name")
    bank_slip_number = fields.Char(string="Bank Slip Number")
    account_number = fields.Char(string="Account Number")
    remarks = fields.Text(string="Remarks")


class RepresentativePosition(models.Model):
    _name = "representative.position"
    _description = "Representative Position"
    _rec_name = "name_np"

    code = fields.Char(string="Code", required=True)
    name_en = fields.Char(string="Name (EN)", required=True)
    name_np = fields.Char(string="Name (NP)", required=True)
    description = fields.Text(string="Description")
    meeting_allowance = fields.Float(string="Meeting Allowance", required=True)
    month_range = fields.Integer(string="Month Range", required=True)
    sequentially = fields.Integer(string="Sequentially")
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )


class RepresentativeFacilities(models.Model):
    _name = "representative.facilities"
    _description = "Representative Facilities"

    code = fields.Char(string="Code")
    fiscal_years = fields.Many2one("account.fiscal.year", string="Fiscal Year")
    month = fields.Selection(
        selection=[
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Month",
    )
    position = fields.Many2one(
        "representative.position", string="Position", required=True
    )
    account_id = fields.Many2one("account.account", string="Account")
    addsub = fields.Selection(
        selection=[("add", "Add"), ("sub", "Sub")], string="Add/Sub", required=True
    )
    amount = fields.Float(string="Amount", required=True)
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )
    remarks = fields.Text(string="Remarks")


class RepresentativeAttendance(models.Model):
    _name = "representative.attendance"
    _description = "Representative Attendance"

    code = fields.Char(string="Code", required=True)
    fiscal_years = fields.Many2one("account.fiscal.year", string="Fiscal Year")
    representative = fields.Many2one(
        "representative.details", string="Representative", required=True
    )
    meeting_date = fields.Date(string="Meeting Date", required=True)
    month = fields.Selection(
        selection=[
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Month",
        required=True,
    )
    remarks = fields.Text(string="Remarks")


class EmployeeLoan(models.Model):
    _name = "employee.loan"
    _description = "Employee Loan"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    account_id = fields.Many2one("account.account", string="Account")
    loan_type = fields.Many2one("loan.type", string="Loan Type", required=True)
    loan_amount = fields.Float(string="Loan Amount", required=True)
    installment_count = fields.Integer(string="Installment Count", required=True)
    monthly_installment = fields.Float(string="Monthly Installment", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )
    remarks = fields.Text(string="Remarks")


class EmployeeAdvance(models.Model):
    _name = "employee.advance"
    _description = "Employee Advance"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    account_id = fields.Many2one("account.account", string="Account", required=True)
    advance_type = fields.Many2one("advance.type", string="Advance Type", required=True)
    advance_amount = fields.Float(string="Advance Amount", required=True)
    installment_count = fields.Integer(string="Installment Count", required=True)
    monthly_installment = fields.Float(string="Monthly Installment", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    status = fields.Selection(
        selection=[("active", "Active"), ("inactive", "Inactive")],
        string="Status",
        default="active",
    )
    remarks = fields.Text(string="Remarks")
