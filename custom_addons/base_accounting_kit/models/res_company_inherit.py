from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from datetime import date
import base64
from odoo.http import request
import re
import os
import string
import random
from odoo.tools import lazy_property
from markupsafe import Markup
from .ecommerce import utils

class ResCompany(models.Model):
    _inherit = "res.users"

    name_np = fields.Char(string="Company Name (Np):")


class CompanyCategory(models.Model):
    _inherit = "res.company"

    name_np = fields.Char(string="Company Name (Np):")
    company_category = fields.Many2many("company.category", string="Business Type")
    company_category_product = fields.Many2many(
        "business.based.products",
        string="Product",
        readonly=True,
        store=True,
        compute="_compute_company_category_product",
    )

    organization_type = fields.Selection(
        [
            ("private limited", "private limited"),
            ("public limited", "public limited"),
            ("user committee", "user committee"),
            ("proprietary firm", "proprietary firm"),
            ("others", "others"),
        ],
        string="Organization Type",
    )
    owner_name_np = fields.Char(string="Owner Name(Np)")
    owner_name_en = fields.Char(string="Owner Name(En)")
    pricing = fields.Float(string="Pricing")
    fiscal_year = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        default=lambda self: self._compute_fiscal_year(),
    )
    registration_no = fields.Char(string="Registration Number")
    tax_id = fields.Char(string="Tax ID")
    start_date = fields.Char(string="Start Date")
    # close_date = fields.Char(string='Closed Date')
    recent_tax_paid_year = fields.Char(string="Recent Tax Paid Year")
    mobile = fields.Char(string="Mobile", required=True)
    email = fields.Char(string="Email")
    pan_number = fields.Char(string="PAN", required=True, size=9)
    owner_citizenship_front = fields.Binary(string="Citizenship Front")
    owner_citizenship_back = fields.Binary(string="Citizenship Back")
    company_docs_ids = fields.One2many(
        "company.documents", "res_id", string="Company Documents"
    )
    # Currency field, setting default currency to NPR
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self._get_default_currency(),
        readonly=True,
    )

    @api.model
    def write(self, vals):

        if "account_fiscal_country_id" not in vals:
            vals["account_fiscal_country_id"] = 167

        if "account_enabled_tax_country_ids" not in vals:
            vals["account_enabled_tax_country_ids"] = [(6, 0, [167])]

        return super(CompanyCategory, self).write(vals)

    @api.model
    def _get_default_currency(self):
        """Returns the default currency for NPR (Nepalese Rupees)."""
        return self.env["res.currency"].search([("name", "=", "NPR")], limit=1).id

    def _compute_fiscal_year(self):
        current_date = fields.Date.today()
        fiscal_year = self.env["account.fiscal.year"].search(
            [("date_from", "<=", current_date), ("date_to", ">=", current_date)],
            limit=1,
        )
        if fiscal_year:
            return fiscal_year.id
        else:
            return False

    @api.depends("company_category")
    def _compute_company_category_product(self):
        for record in self:
            if record.company_category:

                business_based_products = (
                    self.env["business.based.products"]
                    .sudo()
                    .search([("business_id", "in", record.company_category.ids)])
                )
                record.company_category_product = [(6, 0, business_based_products.ids)]
            else:
                record.company_category_product = [(5, 0, 0)]
        # for record in self:
        #     prd = []
        #     if record.company_category:
        #         business_based_products = (
        #             self.env["business.based.products"]
        #             .sudo()
        #             .search([("business_id", "in", record.company_category.ids)])
        #         )
        #         prd = [(6, 0, business_based_products.ids)]
        #     record.company_category_product = prd

    @api.onchange("company_category")
    def _calculate_pricing(self):

        for rec in self:
            total_pricing = 0
            if rec.company_category:
                for category_id in rec.company_category.ids:
                    type_pricing_records = self.env["business.type.pricing"].search(
                        [("business_type.id", "=", category_id)]
                    )

                    for type_price in type_pricing_records:
                        total_pricing += type_price.pricing

            rec.pricing = total_pricing

    @api.constrains("pan_number")
    def _check_pan_and_tax_id_length(self):
        for record in self:
            # Validate PAN Number
            if record.pan_number and (
                not record.pan_number.isdigit() or len(record.pan_number) != 9
            ):
                raise ValidationError("PAN Number must be exactly 9 digits long.")

    @api.constrains("email")
    def _check_email_format(self):
        for record in self:
            if record.email:
                # Regular expression for validating an Email
                email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                if not re.match(email_regex, record.email):
                    raise ValidationError(
                        "Invalid email format. Please enter a valid email address."
                    )

    @api.constrains("mobile")
    def _check_mobile_length_and_prefix(self):
        for record in self:
            if record.mobile:
                # Check if mobile number is 10 digits and starts with 97 or 98
                if (
                    not record.mobile.isdigit()
                    or len(record.mobile) != 10
                    or not record.mobile.startswith(("97", "98"))
                ):
                    raise ValidationError(
                        "Mobile number must be 10 digits long and start with 97 or 98."
                    )

    @api.constrains("pan_number")
    def _check_unique_pan_number(self):
        for record in self:
            if record.pan_number:
                duplicate_pan = self.search(
                    [("pan_number", "=", record.pan_number), ("id", "!=", record.id)]
                )
                if duplicate_pan:
                    raise ValidationError(
                        f"The PAN number '{record.pan_number}' already exists. Each PAN number must be unique."
                    )

    @api.constrains("mobile")
    def _check_unique_mobile(self):
        for record in self:
            if record.mobile:
                duplicate_mobile = self.search(
                    [("mobile", "=", record.mobile), ("id", "!=", record.id)]
                )
                if duplicate_mobile:
                    raise ValidationError(
                        f"The mobile number '{record.mobile}' already exists. Each mobile number must be unique."
                    )

    @api.constrains("email")
    def _check_unique_email(self):
        for record in self:
            if record.email:
                duplicate_email = self.search(
                    [("email", "=", record.email), ("id", "!=", record.id)]
                )
                if duplicate_email:
                    raise ValidationError(
                        f"The email address '{record.email}' already exists. Each email address must be unique."
                    )

    @api.constrains("name")
    def _check_duplicate_name(self):
        for record in self:
            if record.name:
                duplicate_en = self.search(
                    [("name", "=", record.name), ("id", "!=", record.id)]
                )
                if duplicate_en:
                    raise ValidationError(
                        f"The organization name '{record.name}' already exists."
                    )

    # def write(self,vals):
    #     if 'company_category' in vals:
    #         # Reset lazy properties `company` & `companies` on all envs
    #         # This is unlikely in a business code to change the company of a user and then do business stuff
    #         # but in case it happens this is handled.
    #         # e.g. `account_test_savepoint.py` `setup_company_data`, triggered by `test_account_invoice_report.py`
    #         for env in list(self.env.transaction.envs):
    #             if env.user in self:
    #                 lazy_property.reset_all(env)


# class CompanyCategoryProduct(models.Model):
#     _inherit = 'product.template'

#     # company_category = fields.Many2one('company.category',string='Company Category')
#     name_np = fields.Char(string="Product Name (Nepali)")

# def _check_company_category(self):
#     for record in self:
#         if record.company_category:
#             # Ensure the record's category is in the company's selected categories
#             if record.company_category not in record.company_id.company_category:
#                 raise ValidationError("You cannot create this product because its category does not match your company's categories.")


class DocumentsTypes(models.Model):
    _name = "documents.types"
    _description = "Company Documents Types"
    _rec_name = "name"

    name = fields.Char(string="Documents Name")
    code = fields.Char(string="Code")


class CompanyDocuments(models.Model):
    _name = "company.documents"
    _description = "Company Documents"

    type_id = fields.Many2one("documents.types", string="Document Type", create=False)
    documents = fields.Binary(string="Documents")
    res_id = fields.Many2one("res.company", string="Company")
    file_name = fields.Char()

    preview = fields.Html(string="Document preview", store=True)


class OrganizationFieldSelection(models.Model):
    _name = "organization.field.selection"
    _description = "Organization Field Selection"

    name = fields.Char(string="Field Name", required=True)
    field_code = fields.Char(string="Field Code", required=True)

class IndividualFieldSelection(models.Model):
    _name = "individual.field.selection"
    _description = "Individual Field Selection"

    name = fields.Char(string="Field Name", required=True)
    field_code = fields.Char(string="Field Code", required=True)


class emailWizard(models.TransientModel):
    _name = "email.wizard"
    _description = "Email Wizard"

    email_to = fields.Char(string="To", required=True)
    subject = fields.Char(string="Message", required=True)
    body = fields.Text(string="Body")
    registration_docs_ids = fields.Many2many(
        "registration.documents", string="Company Documents"
    )  # Add this field
    organization_type = fields.Char(
        string="Organization Type", compute="_compute_organization_type", store=True
    )
    # update_code = fields.Char(
    #     string="Update Code", compute="_compute_update_code", store=True
    # )
    organization_name_en = fields.Char(string="Company Name (English)")
    owner_name_en = fields.Char(string="Owner Name (English)")

    password = fields.Char(string="password")
    company_register_id = fields.Integer(string="Register ID:")
    # name_np = fields.Char(string="Company Name (Nepali)")
    category_ids = fields.Many2many("company.category", string="Company Category")
    # category_product_ids = fields.Many2many('product.product',string='Product')
    update_code = fields.Char(string="Update Code:",store=True)
    is_reverted = fields.Boolean(string="Is Reverted", default=False)
    is_organization = fields.Boolean(string="Is Organization", default=False)
    # Multi-selection fields
    individual_field_ids = fields.Many2many(
        "individual.field.selection",
        string="Individual Fields",
        help="Select multiple fields related to individual.",
        store=True,
    )

    organization_field_ids = fields.Many2many(
        "organization.field.selection",
        string="Organization Fields",
        help="Select multiple fields related to organization.",
        store=True,
    )
    # @api.model
    # def default_get(self, fields):
    #     res = super(emailWizard, self).default_get(fields)
    #     print("testttt")
    #     # Get the 'organization' value from the context
    #     res['organization_type'] = self.env.context.get('organization', 'default_value')  # Replace 'default_value' as needed
    #     res['update_code'] = self.env.context.get('update_code', 'None')  # Replace 'default_value' as needed
    #     return res

    @api.depends("email_to")  # Replace 'email_to' with relevant fields if needed
    def _compute_organization_type(self):
        for record in self:
            print("testttty")
            # Set the organization type from the context if it's available
            if self.env.context.get("action") == "reverted":
                print("in true")
                record.is_reverted = True
            else:
                print("in false")
                record.is_reverted = False
            record.organization_type = self.env.context.get(
                "organization", "default_value"
            )
            # record.update_code = self.env.context.get("update_code", "None")

    # pan_number = fields.Char(string='PAN Number')
    # phone = fields.Char(string='Phone')
    # mobile = fields.Char(string='Mobile')

    # email = fields.Char(string='Email')
    # street = fields.Char(string='Address')
    # ref_company_id = fields.Integer(string='Ref Company Id')
    # # province = fields.Char(string='Province')
    # # district = fields.Char(string='District')
    # # ward_no = fields.Integer(string='Ward No')
    # login_bg_img = fields.Binary(string='Company Logo')
    # owner_citizenship_front = fields.Binary(string='Owner Citizenship Front')
    # owner_citizenship_back = fields.Binary(string='Owner Citizenship Back')
    # registration_docs_ids = fields.Many2many('registration.documents', string='Company Documents')

    def action_send_email(self):
        self.password = self.generate_password()
        template = self.env.ref("base_accounting_kit.user_registration_templates")

        action_name = self.env.context.get("action")
        print("Action Name", action_name)
        template = self.env.ref("base_accounting_kit.user_registration_templates")
        if not template:
            raise ValidationError("Email template not found.")

        if action_name == "individual" or action_name == "organization":
            password = self.password
            if action_name == "organization":
                self._approve_registration(password)
            elif action_name == "individual":
                self._approve_user_registration(password)

            # Send email
            template.send_mail(self.id, force_send=True)

        elif action_name == "reverted":
            self.password = ""

            template.send_mail(self.id, force_send=True)
            register = (
                self.env["company.register"]
                .sudo()
                .search([("id", "=", self.company_register_id)], limit=1)
            )
            if register:
                register.write({"state": "reverted"})
            # self.sudo().unlink()

    def generate_password(self):
        s1 = list(string.ascii_lowercase)
        s2 = list(string.ascii_uppercase)
        s3 = list(string.digits)
        s4 = list(string.punctuation)
        random.shuffle(s1)
        random.shuffle(s2)
        random.shuffle(s3)
        random.shuffle(s4)

        part1 = round(8 * (30 / 100))
        part2 = round(8 * (20 / 100))
        result = []

        for x in range(part1):
            result.append(s1[x])
            result.append(s2[x])

        for x in range(part2):
            result.append(s3[x])
            result.append(s4[x])
        random.shuffle(result)

        return "".join(result)
    

    def _approve_registration(self, password):
        company_registration = self.env.context.get("default_company_register_id", "")
        action_name = self.env.context.get("organization_name_en", "")
        palika = self.env.context.get("province_id")

        province_id = self.env.context.get("province_id")
        district_id = self.env.context.get("district_id")
        palika_id = self.env.context.get("palika_id")
        ward_no = self.env.context.get("ward_no", "")
        province_name = ""
        district_name = ""
        palika_name = ""

        # Fetch the names from the corresponding models
        if province_id:
            province = self.env["location.province"].browse(province_id)
            province_name = province.name if province else ""
            province_name_np = province.name_np if province else ""

        if district_id:
            district = self.env["location.district"].browse(district_id)
            district_name = district.district_name if district else ""
            district_name_np = district.district_name_np if district else ""

        if palika_id:
            palika = self.env["location.palika"].browse(palika_id)
            palika_name = palika.palika_name if palika else ""
            palika_name_np = palika.palika_name_np if palika else ""

        # Constructing address
        contact_address = (
            f"{province_name},{district_name}, {palika_name}, Ward No: {ward_no}"
        )
        contact_address_np = f"{province_name_np},{district_name_np}, {palika_name_np}, वार्ड नं: {ward_no}"

        origin_url= utils.EcomUtils.get_current_origin()
        
        parent = self.env["res.company"].sudo().search([('website', "=", origin_url['origin_url'])], limit=1)
        if not parent:
            parent = self.env["res.company"].sudo().search([('id', "=",1)], limit=1)
            
        
        
        print("Company parent id:", parent.id)
        company_data = {
            "name": self.env.context.get("organization_name_en", ""),
            "name_np": self.env.context.get("organization_name_np", ""),
            "company_category": [(6, 0, self.category_ids.ids)],
            # 'company_category_product': [(6, 0, self.category_product_ids.ids)],
            "email": self.env.context.get("email", ""),
            "phone": self.env.context.get("phone", ""),
            "mobile": self.env.context.get("mobile", ""),
            "pan_number": self.env.context.get("pan_number", ""),
            "street": contact_address,
            "city": False,
            "state_id": False,
            "zip": False,
            "country_id": 167,
            "account_fiscal_country_id": 167,
            "street_np": contact_address_np,
            "tax_id": self.env.context.get("tax_id", ""),
            "start_date": self.env.context.get("start_date", ""),
            # 'close_date': self.env.context.get('close_date', ''),
            "recent_tax_paid_year": self.env.context.get("recent_tax_paid_year", ""),
            "owner_name_np": self.env.context.get("owner_name_np", ""),
            "owner_name_en": self.env.context.get("owner_name_en", ""),
            "registration_no": self.env.context.get("registration_no", ""),
            "organization_type": self.env.context.get("organization_type", ""),
            "login_bg_img": self.env.context.get("login_bg_img"),
            "owner_citizenship_front": self.env.context.get(
                "owner_citizenship_front", ""
            ),
            "owner_citizenship_back": self.env.context.get(
                "owner_citizenship_back", ""
            ),
            "province": self.env.context.get("province_id", ""),
            "district": self.env.context.get("district_id", ""),
            "palika": self.env.context.get("palika_id", ""),
            "ward_no": self.env.context.get("ward_no", ""),
            "parent_id": parent.id,
            "pickup_location":self.env.context.get("pickup_location"),
            "latitude":self.env.context.get("latitude"),
            "longitude":self.env.context.get("longitude"),
        }

        print("Company Data:", company_data)
        company = self.env["res.company"].sudo().create(company_data)
        if company:
            for doc in self.registration_docs_ids:
                self.env["company.documents"].sudo().create(
                    {
                        "type_id": doc.type_id.id,
                        "file_name": doc.file_name,
                        "res_id": company.id,
                        "documents": doc.documents,
                    }
                )
        user_data = {
            "name": self.env.context.get("owner_name_en"),
            "login": self.env.context.get("email", ""),
            "mobile": self.env.context.get("mobile", ""),
            "company_ids": [(4, company.id)],
            "company_id": company.id,
            "password": password,
        }
        user = (
            self.env["res.users"]
            .sudo()
            .with_context(no_reset_password=True)
            .create(user_data)
        )

        # Assign the 'Limited User' group to the newly created user
        limited_user_group = self.env["res.groups"].search(
            [("name", "=", "Limited User")], limit=1
        )
        if limited_user_group:
            # Add the user to the 'Limited User' group
            user.write({"groups_id": [(4, limited_user_group.id)]})
        else:
            raise UserError("Group 'Limited User' not found.")

        # users = self.env['res.users'].sudo().search([('company_id', '=', company.id)])
        # for user in users:
        #     user.write({
        #         'password': password,
        #         'company_ids': [(4, company.id)],
        #     })
        register = (
            self.env["company.register"]
            .sudo()
            .search([("id", "=", self.company_register_id)], limit=1)
        )
        if register:
            register.write({"state": "approved"})
        res_partner = (
            self.env["res.partner"]
            .sudo()
            .search(
                [
                    ("email", "=", self.env.context.get("email", "")),
                    ("is_company", "=", True),
                ],
                limit=1,
            )
        )
        res_partner_user = (
            self.env["res.partner"]
            .sudo()
            .search(
                [
                    ("email", "=", self.env.context.get("email", "")),
                    (("is_company", "=", False)),
                ],
                limit=1,
            )
        )
        try:
            res_partner.write(
                {
                    "name_np": self.env.context.get("organization_name_np"),
                    "pan_no": self.env.context.get("pan_number"),
                }
            )
            res_partner_user.write({"name_np": self.env.context.get("owner_name_np")})
        except Exception as e:
            raise ValidationError(
                _("Unexpected error occurred while creating res.partner")
            )

    # USERS
    def _approve_user_registration(self, password):
        origin_url= utils.EcomUtils.get_current_origin()
        
        parent = self.env["res.company"].sudo().search([('website', "=", origin_url['origin_url'])], limit=1)
        if not parent:
            parent = self.env["res.company"].sudo().search([('id', "=",1)], limit=1)

        first_name_en = self.env.context.get("first_name_en", "")
        middle_name_en = self.env.context.get("middle_name_en", "")
        last_name_en = self.env.context.get("last_name_en", "")

        # Concatenate English names
        concat_en = " ".join(
            filter(None, [first_name_en, middle_name_en, last_name_en])
        )
        first_name_np = self.env.context.get("first_name_np", "")
        middle_name_np = self.env.context.get("middle_name_np", "")
        last_name_np = self.env.context.get("last_name_np", "")

        concat_np = " ".join(
            filter(None, [first_name_np, middle_name_np, last_name_np])
        )

        province_id = self.env.context.get("province_id")
        district_id = self.env.context.get("district_id")
        palika_id = self.env.context.get("palika_id")
        ward_no = self.env.context.get("ward_no", "")
        province_name = ""
        district_name = ""
        palika_name = ""

        # Fetch the names from the corresponding models
        if province_id:
            province = self.env["location.province"].browse(province_id)
            province_name = province.name if province else ""

        if district_id:
            district = self.env["location.district"].browse(district_id)
            district_name = district.district_name if district else ""

        if palika_id:
            palika = self.env["location.palika"].browse(palika_id)
            palika_name = palika.palika_name if palika else ""

        contact_address = (
            f"{province_name},{district_name}, {palika_name}, Ward No: {ward_no}"
        )

        company_data = {
            "name": concat_en,
            # 'name_np': concat_np,
            "company_category": [(6, 0, self.category_ids.ids)],
            # 'company_category_product': [(6, 0, self.category_product_ids.ids)],
            "email": self.env.context.get("email", ""),
            "phone": self.env.context.get("phone", ""),
            "mobile": self.env.context.get("mobile", ""),
            "pan_number": self.env.context.get("pan_number", ""),
            "street": contact_address,
            "city": False,
            "state_id": False,
            "zip": False,
            "country_id": 167,
            "account_fiscal_country_id": 167,
            "street_np": self.env.context.get("address", ""),
            "tax_id": self.env.context.get("tax_id", ""),
            "start_date": self.env.context.get("start_date", ""),
            # 'close_date': self.env.context.get('close_date', ''),
            "recent_tax_paid_year": self.env.context.get("recent_tax_paid_year", ""),
            "owner_name_np": self.env.context.get("owner_name_np", ""),
            "owner_name_en": self.env.context.get("owner_name_en", ""),
            "pan_number": self.env.context.get("pan_number", ""),
            "registration_no": self.env.context.get("registration_no", ""),
            "organization_type": self.env.context.get("organization_type", ""),
            "login_bg_img": self.env.context.get("login_bg_img", ""),
            "owner_citizenship_front": self.env.context.get(
                "owner_citizenship_front", ""
            ),
            "owner_citizenship_back": self.env.context.get(
                "owner_citizenship_back", ""
            ),
            "province": self.env.context.get("province_id", ""),
            "district": self.env.context.get("district_id", ""),
            "palika": self.env.context.get("palika_id", ""),
            "ward_no": self.env.context.get("ward_no", ""),
            # 'province': self.province,
            # 'district': self.district,
            # 'ward_no': self.ward_no,
            "parent_id": parent.id,
            "pickup_location":self.env.context.get("pickup_location"),
            "latitude":self.env.context.get("latitude"),
            "longitude":self.env.context.get("longitude"),
        }
        print("Company Data:", company_data)
        company = self.env["res.company"].sudo().create(company_data)
        if company:
            user_data = {
                "name": concat_en,
                "name_np": concat_np,
                "login": self.env.context.get("email"),
                "mobile": self.env.context.get("mobile", ""),
                "company_ids": [(4, company.id)],
                "company_id": company.id,
                "image_1920": self.env.context.get("login_bg_img_individual", ""),
                "password": password,
            }
            user = (
                self.env["res.users"]
                .sudo()
                .with_context(no_reset_password=True)
                .create(user_data)
            )

            # Assign the 'Limited User' group to the newly created user
            limited_user_group = self.env["res.groups"].search(
                [("name", "=", "Limited User")], limit=1
            )
            if limited_user_group:
                # Add the user to the 'Limited User' group
                user.write({"groups_id": [(4, limited_user_group.id)]})
            else:
                raise UserError("Group 'Limited User' not found.")

        users = self.env["res.users"].sudo().search([("company_id", "=", company.id)])
        # for user in users:
        #     user.write({
        #         'password': password,
        #         'company_ids': [(4, company.id)],
        #     })
        register = (
            self.env["company.register"]
            .sudo()
            .search([("id", "=", self.company_register_id)], limit=1)
        )
        if register:
            register.write({"state": "approved"})

        res_partner = (
            self.env["res.partner"]
            .sudo()
            .search(
                [
                    ("email", "=", self.env.context.get("email", "")),
                    ("is_company", "=", True),
                ],
                limit=1,
            )
        )
        partner_full_name_np = f"{self.env.context.get('first_name_np','') or ''} {self.env.context.get('middle_name_np','') or ''} {self.env.context.get('last_name_np','') or ''}"
        try:
            res_partner.write(
                {
                    "name_np": partner_full_name_np,
                    "pan_no": self.env.context.get("pan_number"),
                }
            )
        except Exception as e:
            raise ValidationError(
                _("Unexpected error occurred while creating res.partner")
            )
            
    


class CompanyRegistrations(models.Model):
    _name = "company.register"
    _order = "state_priority, id desc"
    # _order = "state='draft' desc, id desc"

    company_type = fields.Selection(
        [("individual", "individual"), ("organization", "organization")],
        string="Company Type",
    )
    organization_name_en = fields.Char(string="Organization Name (EN)")
    organization_name_np = fields.Char(string="Organization Name (NEP)")
    organization_type = fields.Selection(
        [
            ("private limited", "private limited"),
            ("public limited", "public limited"),
            ("user committee", "user committee"),
            ("proprietary firm", "proprietary firm"),
            ("others", "others"),
        ],
        string="Organization Type",
    )
    currency_id = fields.Many2one("res.currency", string="Currency", default=117)
    fiscal_year = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        default=lambda self: self._compute_fiscal_year(),
    )

    first_name_en = fields.Char(string="First Name (EN)")
    middle_name_en = fields.Char(string="Middle Name (EN)")
    last_name_en = fields.Char(string="Last Name(EN)")
    first_name_np = fields.Char(string="First Name (NP)")
    middle_name_np = fields.Char(string="Middle Name (NP)")
    last_name_np = fields.Char(string="Last Name(NP)")
    gender = fields.Selection(
        [("male", "male"), ("female", "female"), ("others", "others")], string="Gender"
    )

    owner_citizenship_front = fields.Binary(string="Owner Citizenship Front")
    owner_citizenship_back = fields.Binary(string="Owner Citizenship Back")
    registration_docs_ids = fields.One2many(
        "registration.documents", "registration_id", string="Company       Documents"
    )

    company_category_ids = fields.Many2many("company.category", string="Business Type")
    # company_category_product_ids = fields.Many2many('product.product',string='Product')
    street = fields.Text(string="Address")
    street_np = fields.Text(string="Address NP")
    pan_number = fields.Char(string="PAN Number", required=True, size=9)
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile", required=True)
    email = fields.Char(string="Email", required=True)
    province = fields.Many2one("location.province", string="Province")
    district = fields.Many2one("location.district", string="District")
    palika = fields.Many2one("location.palika", string="Palika")
    ward_no = fields.Integer(string="Ward No")
    login_bg_img_company = fields.Binary(string="Company Logo")
    login_bg_img_individual = fields.Binary(string="Profile Picture")
    ref_id = fields.Integer(string="Ref ID")
    requested_by = fields.Char(string="Requested By")
    registration_no = fields.Char(string="Registration Number")
    tax_id = fields.Char(string="Tax ID")
    start_date = fields.Char(string="Start Date")
    start_date_bs = fields.Char(string="Start Date BS")
    # close_date = fields.Date(string='Closed Date')
    # close_date_bs = fields.Char(string='Closed Date BS')
    latitude = fields.Float("Address latitude")
    longitude = fields.Float("Address longitude")
    pickup_location=fields.Char('Pick up location')

    recent_tax_paid_year = fields.Char(string="Recent Tax Paid Year")
    owner_name_np = fields.Char(string="Owner Name(Np)")

    owner_name_en = fields.Char(string="Owner Name(En)")
    state = fields.Selection(
        [
            ("draft", "Pending"),
            ("approved", "Approved"),
            ("reverted", "Reverted"),
            ("resubmit", "Resubmit"),
        ],
        String="State",
        default="draft",
    )
    pricing = fields.Float(string="Pricing")

    state_priority = fields.Integer(
        string="State Priority", compute="_compute_state_priority", store=True
    )

    @api.depends("state")
    def _compute_state_priority(self):
        for record in self:
            if record.state == "draft":
                record.state_priority = 1
            elif record.state == "resubmit":
                record.state_priority = 2
            elif record.state == "reverted":
                record.state_priority = 3
            elif record.state == "approved":
                record.state_priority = 4

    # total_pending = fields.Integer(string='Pending Requests', compute='_compute_state_count')
    # total_approved = fields.Integer(string='Approved Requests', compute='_compute_state_count')
    # total_reverted = fields.Integer(string='Reverted Requests', compute='_compute_state_count')

    update_code = fields.Char(string="Update Code")

    @api.constrains("pan_number")
    def _check_unique_pan_number(self):
        for record in self:
            if record.pan_number:
                duplicate_pan = self.search(
                    [("pan_number", "=", record.pan_number), ("id", "!=", record.id)]
                )
                if duplicate_pan:
                    raise ValidationError(
                        f"The PAN number '{record.pan_number}' already exists. Each PAN number must be unique."
                    )

    @api.constrains("mobile")
    def _check_unique_mobile(self):
        for record in self:
            if record.mobile:
                duplicate_mobile = self.search(
                    [("mobile", "=", record.mobile), ("id", "!=", record.id)]
                )
                if duplicate_mobile:
                    raise ValidationError(
                        f"The mobile number '{record.mobile}' already exists. Each mobile number must be unique."
                    )

    @api.constrains("email")
    def _check_unique_email(self):
        for record in self:
            if record.email:
                duplicate_email = self.search(
                    [("email", "=", record.email), ("id", "!=", record.id)]
                )
                if duplicate_email:
                    raise ValidationError(
                        f"The email address '{record.email}' already exists. Each email address must be unique."
                    )

    @api.constrains("organization_name_en", "organization_name_np")
    def _check_duplicate_organization_name(self):
        for record in self:
            if record.organization_name_en:
                duplicate_en = self.search(
                    [
                        ("organization_name_en", "=", record.organization_name_en),
                        ("id", "!=", record.id),
                    ]
                )
                if duplicate_en:
                    raise ValidationError(
                        f"The organization name '{record.organization_name_en}' already exists in English."
                    )

            if record.organization_name_np:
                duplicate_np = self.search(
                    [
                        ("organization_name_np", "=", record.organization_name_np),
                        ("id", "!=", record.id),
                    ]
                )
                if duplicate_np:
                    raise ValidationError(
                        f"The organization name '{record.organization_name_np}' already exists in Nepali."
                    )

    @api.model
    def create(self, vals):
        record = super(CompanyRegistrations, self).create(vals)
        code = random.randint(100000, 999999)
        while self.search_count([("update_code", "=", code)]) > 0:
            code = random.randint(100000, 999999)

        record.update_code = code

        if record.company_type == "individual":
            entity_name = f"{record.first_name_en} {record.middle_name_en or ''} {record.last_name_en}".strip()
        else:
            entity_name = record.organization_name_en

        business_types = (
            ", ".join(record.company_category_ids.mapped("name"))
            if record.company_category_ids
            else "N/A"
        )

        message = (
            f"{_('A new registration request has been created by:')} "
            f" {entity_name} "
            f" for company type: {dict(record._fields['company_type'].selection).get(record.company_type)}"
            f" and the selected business types are: {business_types}"
            f"[Click this link to view the registration]                     (http://lekhaplus.com/web#id={record.id}&model=company.register&view_type=form)"
        )
        admin_user = self.env.ref("base.user_admin")
        print("Searching for 'Company Registration Notification' channel...")
        admin_channel = self.env["discuss.channel"].search(
            [("name", "=", "Company Registration Notification")], limit=1
        )
        if admin_channel:
            print("Channel found. Posting the message to the existing channel...")
        else:
            print("Channel not found. Creating a new channel for admin only...")
            admin_channel = self.env["discuss.channel"].create(
                {
                    "name": "Company Registration Notification",
                    "channel_type": "channel",
                    "group_ids": [(4, self.env.ref("base.group_system").id)],
                    "channel_partner_ids": [(4, admin_user.partner_id.id)],
                }
            )
            print("New admin-only channel created successfully.")

        print("Posting message to the admin channel...")
        admin_channel.message_post(
            body=Markup(message),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=3,
        )
        print("Message posted successfully.")

        return record

    @api.onchange("company_category_ids")
    def _calculate_pricing(self):

        for rec in self:
            total_pricing = 0
            if rec.company_category_ids:
                for category_id in rec.company_category_ids.ids:
                    type_pricing_records = self.env["business.type.pricing"].search(
                        [("business_type.id", "=", category_id)]
                    )

                    for type_price in type_pricing_records:
                        total_pricing += type_price.pricing

            rec.pricing = total_pricing

    # @api.onchange("company_category_ids")
    # def _calculate_pricing(self):
    #     for rec in self:
    #         pricing = 0
    #         for record in rec.company_category_ids.ids:
    #             type_price = self.env['business.type.pricing'].search([('business_type.id','=',record)])
    #             pricing = pricing + type_price.price
    #             rec.pricing = pricing

    def _compute_fiscal_year(self):
        current_date = fields.Date.today()
        fiscal_year = self.env["account.fiscal.year"].search(
            [("date_from", "<=", current_date), ("date_to", ">=", current_date)],
            limit=1,
        )
        if fiscal_year:
            return fiscal_year.id
        else:
            return False

    @api.constrains("email")
    def _check_email_format(self):
        for record in self:
            if record.email:
                # Regular expression for validating an Email
                email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                if not re.match(email_regex, record.email):
                    raise ValidationError(
                        "Invalid email format. Please enter a valid email address."
                    )

    @api.constrains("mobile")
    def _check_mobile_length_and_prefix(self):
        for record in self:
            if record.mobile:
                # Check if mobile number is 10 digits and starts with 97 or 98
                if (
                    not record.mobile.isdigit()
                    or len(record.mobile) != 10
                    or not record.mobile.startswith(("97", "98"))
                ):
                    raise ValidationError(
                        "Mobile number must be 10 digits long and start with 97 or 98."
                    )

    @api.constrains("pan_number")
    def _check_pan_and_tax_id_length(self):
        for record in self:
            # Validate PAN Number
            if record.pan_number and (
                not record.pan_number.isdigit() or len(record.pan_number) != 9
            ):
                raise ValidationError("PAN Number must be exactly 9 digits long.")
            # hhhhhhhh

    def action_approved_button(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "email.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_company_register_id": self.id,
                "action": self.company_type,
                "default_email_to": self.email,
                "default_username": self.organization_name_en,
                "default_password": self.organization_name_en,
                "default_subject": "Thank you for registering with us. We are excited to have you on board.",
                "default_organization_name_en": self.organization_name_en,
                "default_owner_name_en": (
                    f"{self.first_name_en} {self.middle_name_en} {self.last_name_en}"
                    if self.company_type == "individual"
                    else False
                ),
                "organization_name_np": self.organization_name_np,
                "organization_name_en": self.organization_name_en,
                "default_category_ids": self.company_category_ids.ids,
                # 'default_category_product_ids': self.company_category_product_ids.ids,
                "pan_number": self.pan_number,
                "currency_id": self.currency_id,
                "fiscal_year": self.fiscal_year,
                "phone": self.phone,
                "mobile": self.mobile,
                "email": self.email,
                "tax_id": self.tax_id,
                "registration_no": self.registration_no,
                "organization_type": self.organization_type,
                "start_date": self.start_date,
                # 'end_date':self.close_date,
                "recent_tax_paid_year": self.recent_tax_paid_year,
                "owner_name_np": self.owner_name_np,
                "owner_name_en": self.owner_name_en,
                "palika_id": self.palika.id,
                "ref_company_id": self.ref_id,
                "province_id": self.province.id,
                "district_id": self.district.id,
                "ward_no": self.ward_no,
                "login_bg_img": self.login_bg_img_company,
                "owner_citizenship_front": self.owner_citizenship_front,
                "owner_citizenship_back": self.owner_citizenship_back,
                "default_registration_docs_ids": [
                    (6, 0, self.registration_docs_ids.ids)
                ],
                "first_name_en": self.first_name_en,
                "middle_name_en": self.middle_name_en,
                "last_name_en": self.last_name_en,
                "first_name_np": self.first_name_np,
                "middle_name_np": self.middle_name_np,
                "last_name_np": self.last_name_np,
                "gender": self.gender,
                "login_bg_img_individual": self.login_bg_img_individual,
                "pickup_location":self.pickup_location,
                "latitude":self.latitude,
                "longitude":self.longitude,
            },
        }

    def action_reverted_button(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "email.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "action": "reverted",
                "organization": self.company_type,
                "update_code": self.update_code,
                "default_company_register_id": self.id,
                "default_email_to": self.email,
                "default_organization_name_en": self.organization_name_en,
                "default_owner_name_en": (
                    f"{self.first_name_en} {self.middle_name_en} {self.last_name_en}"
                    if self.company_type == "individual"
                    else False
                ),
                "default_company_register_id": self.id,
                "default_update_code": self.update_code,
                "default_username": self.organization_name_en,
                "default_subject": "Reverted Notification",
                "default_body": "Sorry your registeration failed.",
            },
        }


class RegistrationDocuments(models.Model):
    _name = "registration.documents"
    _description = "Registration Documents"

    type_id = fields.Many2one("documents.types", string="Documents Types")
    documents = fields.Binary(string="Documents")
    preview = fields.Html(
        string="Document preview", compute="_compute_preview", store=True
    )
    registration_id = fields.Many2one("company.register", string="Registration")

    file_name = fields.Char()
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif","webp"}

    @api.model
    def create(self, vals):
        if 'file_name' in vals:
            self._validate_file_extension(vals.get("file_name"))
        res = super().create(vals)
        if 'documents' in vals or 'file_name' in vals:
            res._compute_preview()
        return res

    def write(self, vals):
        if 'file_name' in vals:
            self._validate_file_extension(vals.get("file_name"))
        res = super().write(vals)
        if 'documents' in vals or 'file_name' in vals:
            self._compute_preview()
        return res

    def _validate_file_extension(self, file_name):
        """Validate the file extension before saving."""
        file_extension = os.path.splitext(file_name)[1][1:].lower()
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(
                "Invalid file type! Only PDF, PNG, JPG, JPEG, WEBP and GIF files are allowed."
            )


    @api.depends("documents", "file_name")
    def _compute_preview(self):
        for record in self:
            if not record.documents or not record.file_name:
                record.preview = '<div>No file</div>'
                continue

            file_extension = os.path.splitext(record.file_name)[1][1:].lower()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            if file_extension == "pdf": 
                file_url = f"{base_url}/web/content?model={self._name}&id={record.id}&field=documents&filename={record.file_name}"
                record.preview = f"""
                    <div style="text-align: center;">
                        <a href="{file_url}" target="_blank" class="btn btn-primary">
                            <i class="fa fa-file-pdf-o"/> View PDF
                        </a>
                    </div>
                """
            elif file_extension in ["png", "jpg", "jpeg", "gif","webp"]:
                image_url = f"{base_url}/web/image?model={self._name}&id={record.id}&field=documents&filename={record.file_name}"
                record.preview = f"""
                    <div style="text-align: center;">
                        <a href="{image_url}" target="_blank">
                            <img src="{image_url}" style="max-height: 50px; max-width: 100px; object-fit: contain;"/>
                        </a>
                    </div>
                """
            else:
                record.preview = '<div>Unsupported file type</div>'