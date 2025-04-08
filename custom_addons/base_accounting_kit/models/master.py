from odoo import api, fields, models, _
from odoo.tools import remove_accents
import random
import logging
from odoo.exceptions import ValidationError

class CompanyCategory(models.Model):
    _name = 'company.category'
    _description = 'Business Type'

    code = fields.Char(string='Code')
    name = fields.Char(string='Name (EN)')
    name_np = fields.Char(string='Name (NP)')

    products_ids = fields.One2many('business.based.products','business_id','Products')
    related_categories = fields.Many2many(
        'company.category',
        'category_rel',
        'business_id',
        'related_business_id',
        string='Related Categories'
    )

    @api.onchange('related_categories')
    def _onchange_related_categories(self):
        print("heree")
        # if self.related_categories:
        #     product_ids = self.env['business.based.products'].search([
        #         ('business_id', 'in', self.related_categories.ids)
        #     ]).ids
        #     self.products_ids = product_ids
        combined_product_ids = set()

    # Iterate through selected related categories to gather their product IDs
        for category in self.related_categories:
            category_product_ids = self.env['business.based.products'].search([
                ('business_id', '=', category.id)
            ]).ids
            combined_product_ids.update(category_product_ids)

        current_product_ids = self.products_ids.ids or []
        combined_product_ids.update(current_product_ids)
        self.products_ids = [(6, 0, list(combined_product_ids))]

        print("Debug: Combined products_ids after selection:", list(combined_product_ids))
        

    def write(self, vals):
        old_products = {category.id: category.products_ids.ids for category in self}
        result = super(CompanyCategory, self).write(vals)
        for category in self:
            if 'products_ids' in vals:
                new_products = category.products_ids.ids
                old_products_ids = old_products[category.id]

                added_products = set(new_products) - set(old_products_ids)
                for product_id in added_products:
                    product = self.env['business.based.products'].browse(product_id)
                    print(product)
                    
                    # Add the category to the product's company_category Many2many field
                    product.product_id.write({
                        'company_category': [(4, category.id)]  # (4, id) adds the record to Many2many
                    })

         
                for company in self.env['res.company'].search([('company_category', '=', category.id)]):
                    if added_products:
                        company.company_category_product = [(4, product_id) for product_id in added_products]

        return result


class BusinessBasedProducts(models.Model):
    _name = "business.based.products"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.template")
    remarks = fields.Char("Remarks")
    list_price = fields.Float("Sales Price", compute = '_compute_list_price')
    standard_price = fields.Float("Cost Price", compute = '_compute_standard_price')
    uom = fields.Char("UOM",compute='_compute_uom')
    business_id = fields.Many2one(
        "company.category", "Company category", default=lambda self: self.id
    )
    company_id = fields.Many2one("res.company")


    @api.model
    def create(self, vals):
        if "company_id" not in vals:
            vals["company_id"] = self.env.user.company_id.id
        return super(BusinessBasedProducts, self).create(vals)
    
    @api.depends('product_id')
    def _compute_list_price(self):
        for rec in self:
            rec.list_price = rec.product_id.list_price

    @api.depends('product_id')
    def _compute_standard_price(self):
        for rec in self:
            rec.standard_price = rec.product_id.standard_price

    @api.depends('product_id')
    def _compute_uom(self):
        for rec in self:
            rec.uom = rec.product_id.uom_id.name

class ChartOfAccounts(models.Model):
    _inherit = 'account.account'
    account_nepali = fields.Char(string='Account Nepali Name')
    business_type = fields.Many2one('company.category',string='Business Type')

    @api.model
    def fill_business_type(self):
        accounts = self.search([('business_type', '=', False)])
        for rec in accounts:
            if not rec.business_type:
                rec.business_type = 24

    def write(self, vals):
        res = super(ChartOfAccounts, self).write(vals)
        self.fill_business_type()
        return res

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

 
    # company_id = fields.Many2one('res.company', string='Company')
    # @api.model
    # def create(self, vals):
    #     if 'company_id' not in vals:
    #         vals['company_id'] = self.env.user.company_id.id
    #     return super(IssuerBank, self).create(vals)

    # def assign_company_id(self, company_id):
    #     self.ensure_one()
    #     self.company_id = company_idS

    @api.depends('bank_name_np','bank_code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.bank_name_np} - {rec.bank_code}"

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

    
    # company_id = fields.Many2one('res.company', string='Company')
    # @api.model
    # def create(self, vals):
    #     if 'company_id' not in vals:
    #         vals['company_id'] = self.env.user.company_id.id
    #     return super(BranchBank, self).create(vals)

    # def assign_company_id(self, company_id):
    #     self.ensure_one()
    #     self.company_id = company_id

    @api.depends('branch_name','code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.branch_name_np} - {rec.branch_code}"

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
    # company_id = fields.Many2one('res.company', string='Company')
    # @api.model
    # def create(self, vals):
    #     if 'company_id' not in vals:
    #         vals['company_id'] = self.env.user.company_id.id
    #     return super(BankType, self).create(vals)

    # def assign_company_id(self, company_id):
    #     self.ensure_one()
    #     self.company_id = company_id

class BusinessTypePricing(models.Model):
    _name = 'business.type.pricing'
    _description = 'Business Type Pricing'

    name = fields.Char(string='Name', required=True)
    business_type = fields.Many2one('company.category', string='Business Type', required=True)
    pricing = fields.Float(string='Pricing', required=True)


# class CustomModel(models.Model):
#     _name = 'custom.model'
#     _description = 'Custom Model for Category and Products'

#     company_id = fields.Many2one(
#         'res.company',
#         string='Company',
#         required=True,
#         default=lambda self: self.env.company  # Default to the current user's company
#     )
    
#     business_based_products_id = fields.Many2one(
#         'business.based.products',
#         string='Products',
#         domain="[('company_id', '=', company_id)]"
#     )

#     @api.onchange('company_id')
#     def _onchange_company_id(self):
#         print("=========================",self.company_id.id)
#         """ Update the domain for business_based_products_id based on the selected company. """
#         if self.company_id:
#             return {
#                 'domain': {
#                     'business_based_products_id': [('business_id', '=', self.company_id.id)]
#                 }
#             }
#         else:
#             return {'domain': {'business_based_products_id': []}}


